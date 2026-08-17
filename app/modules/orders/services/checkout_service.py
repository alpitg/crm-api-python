from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.db.mongo import db
from app.modules.orders.services.invoice_service import (
    InvoiceServiceError,
    invoice_service,
)
from app.modules.orders.services.payment_service import (
    PaymentServiceError,
    payment_service,
)
from app.utils.generate_unique_id_util import generate_order_code
from app.utils.mongo_serializer import serialize_mongo
from app.utils.pricing import get_product_pricing
from config import settings


orders_collection = db["orders"]
products_collection = db["products"]
invoices_collection = db["invoices"]


class CheckoutServiceError(Exception):
    """Raised when checkout initialization fails."""


class CheckoutService:
    async def create_checkout(
        self,
        payload: Any,
    ) -> dict[str, Any]:
        """
        Create an order and initialize checkout payment.

        Online:
        1. Validate products and stock.
        2. Calculate pricing server-side.
        3. Create order.
        4. Create invoice.
        5. Create Razorpay order.
        6. Link Razorpay order to invoice.
        7. Return checkout information.

        COD:
        1. Validate products and stock.
        2. Calculate pricing server-side.
        3. Create order.
        4. Create invoice.
        5. Mark order as placed.
        6. Keep payment pending.
        """
        order = payload
        now = datetime.now(timezone.utc)

        customer_id = self._validate_customer_id(
            order.customerId
        )

        (
            processed_items,
            subtotal,
            product_discount,
            total_tax,
            excluded_tax_total,
        ) = await self._process_items(
            order.items
        )

        # IMPORTANT:
        # Do not trust promotional discount values from
        # a public frontend. Coupon/offer validation should
        # happen in a backend service.
        requested_discount = self._calculate_discount(
            discount_amount=order.discountAmount,
            subtotal=subtotal,
        )

        total_discount = round(
            product_discount + requested_discount,
            2,
        )

        shipping = self._calculate_shipping(
            order=order,
            subtotal=subtotal,
        )

        # Misc charges from a public client should ideally
        # also come from backend-controlled services.
        misc_charges, misc_total = (
            self._calculate_misc_charges(
                order.miscCharges
            )
        )

        total_amount = self._calculate_total(
            subtotal=subtotal,
            excluded_tax_total=excluded_tax_total,
            shipping=shipping,
            misc_total=misc_total,
            requested_discount=requested_discount,
        )

        order_code = generate_order_code()

        order_doc = self._build_order_document(
            order=order,
            customer_id=customer_id,
            processed_items=processed_items,
            order_code=order_code,
            subtotal=subtotal,
            total_discount=total_discount,
            total_tax=total_tax,
            excluded_tax_total=excluded_tax_total,
            requested_discount=requested_discount,
            shipping=shipping,
            misc_charges=misc_charges,
            total_amount=total_amount,
            now=now,
        )

        order_id = await self._create_order(
            order_doc
        )

        invoice_id: ObjectId | None = None

        try:
            invoice = await invoice_service.create_invoice(
                order_id=order_id,
                customer_name=order.customerName,
                total_amount=total_amount,
                payment_method=order.paymentMethod,
                payment_provider=(
                    "razorpay"
                    if order.paymentMethod == "online"
                    else "cod"
                ),
                now=now,
            )

            invoice_id = invoice.get("_id")

            if not invoice_id:
                raise InvoiceServiceError(
                    "Invoice ID was not returned."
                )

            await invoice_service.update_bill_to(
                invoice_id=invoice_id,
                bill_to=self._build_bill_to(order),
            )

            await orders_collection.update_one(
                {"_id": order_id},
                {
                    "$set": {
                        "invoiceId": str(invoice_id),
                        "updatedAt": now,
                    }
                },
            )

            if order.paymentMethod == "online":
                payment = (
                    await self._initialize_online_payment(
                        order_id=order_id,
                        order_code=order_code,
                        invoice_id=invoice_id,
                        total_amount=total_amount,
                    )
                )

                return await self._build_response(
                    order_id=order_id,
                    invoice_id=invoice_id,
                    payment=payment,
                )

            await self._place_cod_order(
                order_id=order_id,
                invoice_id=invoice_id,
                now=now,
            )

            return await self._build_response(
                order_id=order_id,
                invoice_id=invoice_id,
                payment=None,
            )

        except (
            CheckoutServiceError,
            InvoiceServiceError,
            PaymentServiceError,
        ):
            await self._rollback_checkout(
                order_id=order_id,
                invoice_id=invoice_id,
            )
            raise

        except Exception as exc:
            await self._rollback_checkout(
                order_id=order_id,
                invoice_id=invoice_id,
            )

            raise CheckoutServiceError(
                "Failed to initialize checkout."
            ) from exc

    async def _process_items(
        self,
        items: list[Any],
    ) -> tuple[
        list[dict[str, Any]],
        float,
        float,
        float,
        float,
    ]:
        """
        Validate products and calculate pricing
        completely from backend product data.
        """
        processed_items: list[dict[str, Any]] = []

        subtotal = 0.0
        total_discount = 0.0
        total_tax = 0.0
        excluded_tax_total = 0.0

        for item in items:
            product_id = item.productId

            if not product_id:
                raise CheckoutServiceError(
                    "Product ID is required."
                )

            if not ObjectId.is_valid(product_id):
                raise CheckoutServiceError(
                    f"Invalid product ID: {product_id}"
                )

            quantity = int(item.quantity)

            if quantity <= 0:
                raise CheckoutServiceError(
                    "Quantity must be greater than zero."
                )

            product_object_id = ObjectId(
                product_id
            )

            product = (
                await products_collection.find_one(
                    {"_id": product_object_id}
                )
            )

            if not product:
                raise CheckoutServiceError(
                    f"Product not found: {product_id}"
                )

            self._validate_stock(
                product=product,
                quantity=quantity,
            )

            pricing = (
                self._calculate_product_pricing(
                    product=product,
                    quantity=quantity,
                )
            )

            line_subtotal = round(
                float(pricing["subtotal"]),
                2,
            )

            line_discount = round(
                float(pricing["discount"]),
                2,
            )

            line_tax = round(
                float(pricing["taxAmount"]),
                2,
            )

            line_excluded_tax = round(
                float(
                    pricing["excludedTaxAmount"]
                ),
                2,
            )

            subtotal += line_subtotal
            total_discount += line_discount
            total_tax += line_tax
            excluded_tax_total += line_excluded_tax

            processed_items.append(
                self._build_processed_item(
                    item=item,
                    product=product,
                    pricing=pricing,
                )
            )

        if not processed_items:
            raise CheckoutServiceError(
                "At least one product is required."
            )

        return (
            processed_items,
            round(subtotal, 2),
            round(total_discount, 2),
            round(total_tax, 2),
            round(excluded_tax_total, 2),
        )

    @staticmethod
    def _validate_customer_id(
        customer_id: str | None,
    ) -> ObjectId | None:
        """Validate an optional customer ID."""
        if not customer_id:
            return None

        if not ObjectId.is_valid(customer_id):
            raise CheckoutServiceError(
                "Invalid customer ID."
            )

        return ObjectId(customer_id)

    @staticmethod
    def _validate_stock(
        *,
        product: dict[str, Any],
        quantity: int,
    ) -> None:
        """Validate available product inventory."""
        inventory = product.get("inventory") or {}

        try:
            shelf_quantity = int(
                inventory.get(
                    "quantityInShelf"
                )
                or 0
            )

            warehouse_quantity = int(
                inventory.get(
                    "quantityInWarehouse"
                )
                or 0
            )
        except (TypeError, ValueError) as exc:
            raise CheckoutServiceError(
                "Invalid inventory data."
            ) from exc

        available_stock = (
            shelf_quantity + warehouse_quantity
        )

        if available_stock < quantity:
            product_name = product.get(
                "name",
                "product",
            )

            raise CheckoutServiceError(
                f"Insufficient stock for "
                f"{product_name}."
            )

    @staticmethod
    def _calculate_product_pricing(
        *,
        product: dict[str, Any],
        quantity: int,
    ) -> dict[str, Any]:
        """Calculate product pricing using backend rules."""
        try:
            return get_product_pricing(
                product,
                quantity,
            )
        except (ValueError, TypeError) as exc:
            product_name = product.get(
                "name",
                "product",
            )

            raise CheckoutServiceError(
                f"Invalid pricing for "
                f"{product_name}: {exc}"
            ) from exc

    @staticmethod
    def _build_tax_snapshot(
        pricing: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Create an immutable tax snapshot."""
        tax_data = pricing.get("tax") or {}

        class_name = tax_data.get(
            "className"
        )

        rate = round(
            float(
                tax_data.get("rate") or 0
            ),
            2,
        )

        amount = round(
            float(
                tax_data.get("amount") or 0
            ),
            2,
        )

        included = bool(
            tax_data.get(
                "included",
                False,
            )
        )

        if not class_name and rate <= 0:
            return []

        return [
            {
                "className": class_name,
                "rate": rate,
                "included": included,
                "amount": amount,
            }
        ]

    def _build_processed_item(
        self,
        *,
        item: Any,
        product: dict[str, Any],
        pricing: dict[str, Any],
    ) -> dict[str, Any]:
        """Create an immutable order-item snapshot."""
        line_discount = round(
            float(pricing["discount"]),
            2,
        )

        product_type = (
            item.productType
            or product.get(
                "productType",
                "physical",
            )
        )

        return {
            "productId": item.productId,
            "productType": product_type,
            "name": product.get("name"),
            "description": product.get(
                "description"
            ),
            "quantity": int(item.quantity),
            "unitPrice": round(
                float(
                    pricing["unitSellingPrice"]
                ),
                2,
            ),
            "mrp": round(
                float(pricing["unitMrp"]),
                2,
            ),
            "discountedQuantity": (
                int(item.quantity)
                if line_discount > 0
                else 0
            ),
            "discountAmount": line_discount,
            "cancelledQty": 0,
            "taxSnapshot": (
                self._build_tax_snapshot(
                    pricing
                )
            ),
        }

    @staticmethod
    def _calculate_discount(
        discount_amount: float | None,
        subtotal: float,
    ) -> float:
        """
        Calculate checkout discount.

        IMPORTANT:
        This currently accepts the requested discount because
        that field exists in the public schema.

        For production coupons/offers, replace this with a
        backend coupon/offer service. Never trust a frontend
        calculated discount as the final promotional discount.
        """
        requested_discount = float(
            discount_amount or 0
        )

        if requested_discount <= 0:
            return 0.0

        return round(
            min(
                requested_discount,
                subtotal,
            ),
            2,
        )

    @staticmethod
    def _calculate_shipping(
        *,
        order: Any,
        subtotal: float,
    ) -> float:
        """
        Calculate shipping server-side.

        Replace this with a real shipping service when
        shipping rules are introduced.
        """
        del order
        del subtotal

        return 0.0

    @staticmethod
    def _calculate_misc_charges(
        misc_charges: list[Any] | None,
    ) -> tuple[
        list[dict[str, Any]],
        float,
    ]:
        """
        Calculate miscellaneous charges.

        These should eventually be calculated by the backend
        rather than trusted from the public frontend.
        """
        if not misc_charges:
            return [], 0.0

        processed_charges: list[
            dict[str, Any]
        ] = []

        total = 0.0

        for charge in misc_charges:
            label = str(
                charge.label
            ).strip()

            amount = round(
                float(charge.amount),
                2,
            )

            if not label:
                continue

            if amount <= 0:
                continue

            processed_charges.append(
                {
                    "label": label,
                    "amount": amount,
                }
            )

            total += amount

        return (
            processed_charges,
            round(total, 2),
        )

    @staticmethod
    def _calculate_total(
        *,
        subtotal: float,
        excluded_tax_total: float,
        shipping: float,
        misc_total: float,
        requested_discount: float,
    ) -> float:
        """Calculate final payable amount."""
        total_amount = (
            subtotal
            + excluded_tax_total
            + shipping
            + misc_total
            - requested_discount
        )

        total_amount = round(
            total_amount,
            2,
        )

        if total_amount <= 0:
            raise CheckoutServiceError(
                "Invalid order amount."
            )

        return total_amount

    @staticmethod
    def _build_order_document(
        *,
        order: Any,
        customer_id: ObjectId | None,
        processed_items: list[
            dict[str, Any]
        ],
        order_code: str,
        subtotal: float,
        total_discount: float,
        total_tax: float,
        excluded_tax_total: float,
        requested_discount: float,
        shipping: float,
        misc_charges: list[
            dict[str, Any]
        ],
        total_amount: float,
        now: datetime,
    ) -> dict[str, Any]:
        """Build the order MongoDB document."""
        is_online = (
            order.paymentMethod == "online"
        )

        included_tax_total = round(
            max(
                total_tax
                - excluded_tax_total,
                0.0,
            ),
            2,
        )

        return {
            "orderCode": order_code,
            "customerName": order.customerName,
            "customerId": customer_id,
            "items": processed_items,
            "deliveryAddress": (
                order.deliveryAddress.model_dump()
            ),
            "paymentMethod": order.paymentMethod,
            "paymentStatus": "pending",
            "discountAmount": round(
                requested_discount,
                2,
            ),
            "miscCharges": misc_charges,
            "shippingAmount": round(
                shipping,
                2,
            ),
            "orderStatus": (
                "payment_pending"
                if is_online
                else "placed"
            ),
            "invoiceId": None,
            "handledBy": None,
            "createdAt": now,
            "updatedAt": now,
            "likelyDateOfDelivery": (
                order.likelyDateOfDelivery
            ),
            "note": (
                order.note
                or "Website order"
            ),
            "subtotal": round(
                subtotal,
                2,
            ),
            "totalDiscountAmount": round(
                total_discount,
                2,
            ),
            "totalTaxAmount": round(
                total_tax,
                2,
            ),
            "includedTaxAmount": (
                included_tax_total
            ),
            "excludedTaxAmount": round(
                excluded_tax_total,
                2,
            ),
            "totalAmount": round(
                total_amount,
                2,
            ),
            "cancelledAmount": 0.0,
        }

    @staticmethod
    async def _create_order(
        order_doc: dict[str, Any],
    ) -> ObjectId:
        """Create an order document."""
        try:
            result = (
                await orders_collection.insert_one(
                    order_doc
                )
            )
        except Exception as exc:
            raise CheckoutServiceError(
                "Failed to create order."
            ) from exc

        if not result.inserted_id:
            raise CheckoutServiceError(
                "Failed to create order."
            )

        return result.inserted_id

    @staticmethod
    def _build_bill_to(
        order: Any,
    ) -> dict[str, Any]:
        """Build invoice billing information."""
        address = order.deliveryAddress

        return {
            "name": address.name,
            "address": {
                "addressLine1": (
                    address.addressLine1
                ),
                "addressLine2": (
                    address.addressLine2
                ),
                "landmark": address.landmark,
                "city": address.city,
                "state": address.state,
                "pincode": address.pincode,
                "addressType": (
                    address.addressType
                ),
            },
            "detail": None,
            "phone": address.mobile,
            "email": None,
            "gstin": None,
        }

    async def _initialize_online_payment(
        self,
        *,
        order_id: ObjectId,
        order_code: str,
        invoice_id: ObjectId,
        total_amount: float,
    ) -> dict[str, Any]:
        """Create Razorpay order and link it to invoice."""
        try:
            razorpay_order = (
                payment_service.create_razorpay_order(
                    amount=total_amount,
                    order_id=order_id,
                    order_code=order_code,
                    invoice_id=invoice_id,
                )
            )
        except PaymentServiceError:
            raise
        except Exception as exc:
            raise PaymentServiceError(
                "Failed to create Razorpay order."
            ) from exc

        if not isinstance(
            razorpay_order,
            dict,
        ):
            raise PaymentServiceError(
                "Invalid Razorpay response."
            )

        razorpay_order_id = (
            razorpay_order.get("id")
        )

        if not razorpay_order_id:
            raise PaymentServiceError(
                "Razorpay order ID was not returned."
            )

        await invoice_service.set_razorpay_order_id(
            invoice_id=invoice_id,
            razorpay_order_id=(
                razorpay_order_id
            ),
        )

        return razorpay_order

    async def _place_cod_order(
        self,
        *,
        order_id: ObjectId,
        invoice_id: ObjectId,
        now: datetime,
    ) -> None:
        """Finalize a COD order."""
        order_result = (
            await orders_collection.update_one(
                {"_id": order_id},
                {
                    "$set": {
                        "orderStatus": "placed",
                        "paymentStatus": "pending",
                        "updatedAt": now,
                    }
                },
            )
        )

        if order_result.matched_count == 0:
            raise CheckoutServiceError(
                "Order could not be finalized."
            )

        invoice_result = (
            await invoices_collection.update_one(
                {"_id": invoice_id},
                {
                    "$set": {
                        "paymentStatus": "pending",
                        "paymentMode": "cod",
                        "paymentProvider": "cod",
                        "paymentMethod": "cod",
                        "updatedAt": now,
                    }
                },
            )
        )

        if invoice_result.matched_count == 0:
            raise CheckoutServiceError(
                "Invoice could not be finalized."
            )


    async def _build_response(
        self,
        *,
        order_id: ObjectId,
        invoice_id: ObjectId,
        payment: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Build JSON-safe checkout response."""

        order = await orders_collection.find_one(
            {"_id": order_id}
        )

        if not order:
            raise CheckoutServiceError(
                "Order could not be retrieved."
            )

        invoice = await invoice_service.get_invoice(
            invoice_id
        )

        if not invoice:
            raise CheckoutServiceError(
                "Invoice could not be retrieved."
            )

        # --------------------------------------------------------
        # Convert MongoDB documents to JSON-safe dictionaries
        # --------------------------------------------------------

        order_response = serialize_mongo(order)
        invoice_response = serialize_mongo(invoice)

        response: dict[str, Any] = {
            "order": order_response,
            "invoice": invoice_response,
        }

        # --------------------------------------------------------
        # PAYMENT
        # --------------------------------------------------------

        if payment:
            payment_id = payment.get("id")

            if not payment_id:
                raise CheckoutServiceError(
                    "Invalid payment response."
                )

            response["payment"] = {
                "provider": "razorpay",
                "keyId": settings.RAZORPAY_KEY_ID,
                "razorpayOrderId": str(payment_id),
                "amount": payment.get(
                    "amount",
                    0,
                ),
                "currency": payment.get(
                    "currency",
                    "INR",
                ),
            }

        else:
            response["payment"] = {
                "provider": "cod",
                "method": "cod",
                "amount": order.get(
                    "totalAmount",
                    0,
                ),
                "currency": "INR",
            }

        return response

    async def _rollback_checkout(
        self,
        *,
        order_id: ObjectId,
        invoice_id: ObjectId | None,
    ) -> None:
        """
        Roll back locally-created checkout records.

        Razorpay orders cannot be deleted through this local
        rollback. The local order/invoice are removed so that
        an incomplete checkout does not remain as a valid order.
        """
        if invoice_id:
            try:
                await invoice_service.delete_invoice(
                    invoice_id
                )
            except Exception:
                pass

        try:
            await orders_collection.delete_one(
                {"_id": order_id}
            )
        except Exception:
            pass


checkout_service = CheckoutService()


async def create_checkout_order(
    payload: Any,
) -> dict[str, Any]:
    """Create a public checkout order."""
    return await checkout_service.create_checkout(
        payload
    )