from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import razorpay
from bson import ObjectId

from app.db.mongo import db
from app.modules.orders.services.invoice_service import (
    InvoiceServiceError,
    invoice_service,
)
from config import settings


orders_collection = db["orders"]
carts_collection = db["carts"]

class PaymentServiceError(Exception):
    """Raised when payment processing fails."""


class PaymentService:
    def __init__(self) -> None:
        self.client = razorpay.Client(
            auth=(
                settings.RAZORPAY_KEY_ID,
                settings.RAZORPAY_KEY_SECRET,
            )
        )

    # ============================================================
    # ID VALIDATION
    # ============================================================

    @staticmethod
    def _to_object_id(
        value: ObjectId | str | None,
        field_name: str,
    ) -> ObjectId:
        """Convert a value to MongoDB ObjectId."""

        if value is None:
            raise PaymentServiceError(
                f"{field_name} is required."
            )

        if isinstance(value, ObjectId):
            return value

        value_string = str(value).strip()

        if not value_string:
            raise PaymentServiceError(
                f"{field_name} is required."
            )

        if not ObjectId.is_valid(value_string):
            raise PaymentServiceError(
                f"Invalid {field_name}."
            )

        return ObjectId(value_string)

    # ============================================================
    # STRING VALIDATION
    # ============================================================

    @staticmethod
    def _validate_string(
        value: Any,
        field_name: str,
    ) -> str:
        """Validate and normalize a required string."""

        if value is None:
            raise PaymentServiceError(
                f"{field_name} is required."
            )

        if not isinstance(value, str):
            raise PaymentServiceError(
                f"Invalid {field_name}."
            )

        value = value.strip()

        if not value:
            raise PaymentServiceError(
                f"{field_name} is required."
            )

        return value

    # ============================================================
    # CREATE RAZORPAY ORDER
    # ============================================================

    def create_razorpay_order(
        self,
        *,
        amount: float,
        order_id: ObjectId | str,
        order_code: str,
        invoice_id: ObjectId | str,
    ) -> dict[str, Any]:
        """Create a Razorpay order."""

        if amount is None:
            raise PaymentServiceError(
                "Payment amount is required."
            )

        try:
            amount_value = float(amount)
        except (TypeError, ValueError) as exc:
            raise PaymentServiceError(
                "Invalid payment amount."
            ) from exc

        if amount_value <= 0:
            raise PaymentServiceError(
                "Razorpay order amount must be greater than zero."
            )

        order_object_id = self._to_object_id(
            order_id,
            "order ID",
        )

        invoice_object_id = self._to_object_id(
            invoice_id,
            "invoice ID",
        )

        order_code = self._validate_string(
            order_code,
            "order code",
        )

        razorpay_amount = int(
            round(amount_value * 100)
        )

        if razorpay_amount <= 0:
            raise PaymentServiceError(
                "Razorpay order amount must be greater than zero."
            )

        try:
            razorpay_order = self.client.order.create(
                {
                    "amount": razorpay_amount,
                    "currency": "INR",
                    "receipt": order_code,
                    "payment_capture": 1,
                    "notes": {
                        "order_id": str(
                            order_object_id
                        ),
                        "order_code": order_code,
                        "invoice_id": str(
                            invoice_object_id
                        ),
                    },
                }
            )
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

        razorpay_order_id = razorpay_order.get(
            "id"
        )

        if not isinstance(
            razorpay_order_id,
            str,
        ):
            raise PaymentServiceError(
                "Razorpay did not return a valid order ID."
            )

        razorpay_order_id = (
            razorpay_order_id.strip()
        )

        if not razorpay_order_id:
            raise PaymentServiceError(
                "Razorpay did not return an order ID."
            )

        return razorpay_order

    # ============================================================
    # VERIFY PAYMENT
    # ============================================================

    async def verify_payment(
        self,
        *,
        order_id: ObjectId | str,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        razorpay_signature: str,
    ) -> dict[str, Any]:
        """Verify and finalize a Razorpay payment."""

        order_object_id = self._to_object_id(
            order_id,
            "order ID",
        )

        razorpay_payment_id = (
            self._validate_string(
                razorpay_payment_id,
                "Razorpay payment ID",
            )
        )

        razorpay_order_id = (
            self._validate_string(
                razorpay_order_id,
                "Razorpay order ID",
            )
        )

        razorpay_signature = (
            self._validate_string(
                razorpay_signature,
                "Razorpay signature",
            )
        )

        order = await self._get_order(
            order_object_id
        )

        invoice = await self._get_invoice(
            order
        )

        # --------------------------------------------------------
        # ALREADY PAID
        # --------------------------------------------------------

        if (
            order.get("paymentStatus") == "paid"
            and order.get("orderStatus") == "placed"
        ):
            return {
                "already_verified": True,
                "order": self._make_json_safe(
                    order
                ),
                "invoice": self._make_json_safe(
                    invoice
                ),
                "payment": None,
                "paid_at": None,
            }

        # --------------------------------------------------------
        # PAYMENT METHOD
        # --------------------------------------------------------

        payment_method = order.get(
            "paymentMethod"
        )

        if payment_method != "online":
            raise PaymentServiceError(
                "This order is not an online payment order."
            )

        # --------------------------------------------------------
        # INVOICE RAZORPAY DATA
        # --------------------------------------------------------

        razorpay_data = invoice.get(
            "razorpay"
        )

        if razorpay_data is None:
            razorpay_data = {}

        if not isinstance(
            razorpay_data,
            dict,
        ):
            raise PaymentServiceError(
                "Invalid Razorpay invoice data."
            )

        stored_razorpay_order_id = (
            razorpay_data.get("orderId")
        )

        stored_razorpay_order_id = (
            self._validate_string(
                stored_razorpay_order_id,
                "Stored Razorpay order ID",
            )
        )

        # --------------------------------------------------------
        # RAZORPAY ORDER ID MATCH
        # --------------------------------------------------------

        if (
            stored_razorpay_order_id
            != razorpay_order_id
        ):
            raise PaymentServiceError(
                "Razorpay order ID mismatch."
            )

        # --------------------------------------------------------
        # DUPLICATE PAYMENT
        # --------------------------------------------------------

        self._check_existing_payment(
            invoice=invoice,
            razorpay_payment_id=(
                razorpay_payment_id
            ),
        )

        # --------------------------------------------------------
        # VERIFY SIGNATURE
        # --------------------------------------------------------

        self._verify_signature(
            razorpay_order_id=(
                stored_razorpay_order_id
            ),
            razorpay_payment_id=(
                razorpay_payment_id
            ),
            razorpay_signature=(
                razorpay_signature
            ),
        )

        # --------------------------------------------------------
        # FETCH PAYMENT
        # --------------------------------------------------------

        payment = self._fetch_payment(
            razorpay_payment_id
        )

        # --------------------------------------------------------
        # EXPECTED AMOUNT
        # --------------------------------------------------------

        expected_amount = (
            self._get_order_amount(order)
        )

        # --------------------------------------------------------
        # VALIDATE PAYMENT
        # --------------------------------------------------------

        self._validate_payment(
            payment=payment,
            razorpay_order_id=(
                stored_razorpay_order_id
            ),
            expected_amount=expected_amount,
        )

        now = datetime.now(timezone.utc)

        # --------------------------------------------------------
        # INVOICE ID
        # --------------------------------------------------------

        invoice_id = self._to_object_id(
            invoice.get("_id"),
            "invoice ID",
        )

        # --------------------------------------------------------
        # MARK INVOICE PAID
        # --------------------------------------------------------

        try:
            await invoice_service.mark_as_paid(
                invoice_id=invoice_id,
                payment_id=(
                    razorpay_payment_id
                ),
                razorpay_order_id=(
                    stored_razorpay_order_id
                ),
                signature=razorpay_signature,
                payment_method=payment.get(
                    "method"
                ),
                amount=expected_amount,
                paid_at=now,
            )
        except InvoiceServiceError as exc:
            raise PaymentServiceError(
                str(exc)
            ) from exc

        # --------------------------------------------------------
        # MARK ORDER PAID
        # --------------------------------------------------------

        await self._mark_order_paid(
            order_id=order_object_id,
            updated_at=now,
        )

        await self._clear_cart(
            order=order,
        )

        # --------------------------------------------------------
        # GET UPDATED ORDER
        # --------------------------------------------------------

        updated_order = await self._get_order(
            order_object_id
        )

        # --------------------------------------------------------
        # GET UPDATED INVOICE
        # --------------------------------------------------------

        try:
            updated_invoice = (
                await invoice_service.get_invoice(
                    invoice_id
                )
            )
        except InvoiceServiceError as exc:
            raise PaymentServiceError(
                str(exc)
            ) from exc

        if not updated_invoice:
            raise PaymentServiceError(
                "Updated invoice could not be retrieved."
            )



        # --------------------------------------------------------
        # RESPONSE
        # --------------------------------------------------------

        return {
            "already_verified": False,
            "order": self._make_json_safe(
                updated_order
            ),
            "invoice": self._make_json_safe(
                updated_invoice
            ),
            "payment": self._make_json_safe(
                payment
            ),
            "paid_at": now.isoformat(),
        }

    # ============================================================
    # GET ORDER
    # ============================================================

    @classmethod
    async def _get_order(
        cls,
        order_id: ObjectId | str,
    ) -> dict[str, Any]:
        """Get an order by MongoDB ID."""

        order_object_id = cls._to_object_id(
            order_id,
            "order ID",
        )

        order = await orders_collection.find_one(
            {
                "_id": order_object_id
            }
        )

        if not order:
            raise PaymentServiceError(
                "Order not found."
            )

        if not isinstance(
            order,
            dict,
        ):
            raise PaymentServiceError(
                "Invalid order data."
            )

        return order

    # ============================================================
    # GET INVOICE
    # ============================================================

    @classmethod
    async def _get_invoice(
        cls,
        order: dict[str, Any],
    ) -> dict[str, Any]:
        """Get the invoice belonging to an order."""

        if not isinstance(
            order,
            dict,
        ):
            raise PaymentServiceError(
                "Invalid order data."
            )

        invoice_id = order.get(
            "invoiceId"
        )

        invoice_object_id = cls._to_object_id(
            invoice_id,
            "invoice ID",
        )

        try:
            invoice = (
                await invoice_service.get_invoice(
                    invoice_object_id
                )
            )
        except InvoiceServiceError as exc:
            raise PaymentServiceError(
                str(exc)
            ) from exc

        if not invoice:
            raise PaymentServiceError(
                "Invoice not found."
            )

        if not isinstance(
            invoice,
            dict,
        ):
            raise PaymentServiceError(
                "Invalid invoice data."
            )

        return invoice

    # ============================================================
    # GET ORDER AMOUNT
    # ============================================================

    @staticmethod
    def _get_order_amount(
        order: dict[str, Any],
    ) -> float:
        """Get and validate the order payable amount."""

        amount = order.get(
            "totalAmount"
        )

        if amount is None:
            raise PaymentServiceError(
                "Order amount is missing."
            )

        try:
            amount = float(amount)
        except (TypeError, ValueError) as exc:
            raise PaymentServiceError(
                "Invalid order amount."
            ) from exc

        if amount <= 0:
            raise PaymentServiceError(
                "Invalid order amount."
            )

        return round(
            amount,
            2,
        )

    # ============================================================
    # DUPLICATE PAYMENT CHECK
    # ============================================================

    @staticmethod
    def _check_existing_payment(
        *,
        invoice: dict[str, Any],
        razorpay_payment_id: str,
    ) -> None:
        """Prevent reuse of an already processed payment."""

        razorpay_data = invoice.get(
            "razorpay"
        ) or {}

        if not isinstance(
            razorpay_data,
            dict,
        ):
            raise PaymentServiceError(
                "Invalid Razorpay invoice data."
            )

        existing_payment_id = (
            razorpay_data.get("paymentId")
        )

        if not existing_payment_id:
            return

        existing_payment_id = str(
            existing_payment_id
        ).strip()

        if (
            existing_payment_id
            == razorpay_payment_id
        ):
            raise PaymentServiceError(
                "Payment already verified."
            )

        raise PaymentServiceError(
            "Invoice already has a different payment."
        )

    # ============================================================
    # VERIFY SIGNATURE
    # ============================================================

    def _verify_signature(
        self,
        *,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> None:
        """Verify the Razorpay payment signature."""

        try:
            self.client.utility.verify_payment_signature(
                {
                    "razorpay_order_id": (
                        razorpay_order_id
                    ),
                    "razorpay_payment_id": (
                        razorpay_payment_id
                    ),
                    "razorpay_signature": (
                        razorpay_signature
                    ),
                }
            )
        except Exception as exc:
            raise PaymentServiceError(
                "Invalid payment signature."
            ) from exc

    # ============================================================
    # FETCH PAYMENT
    # ============================================================

    def _fetch_payment(
        self,
        razorpay_payment_id: str,
    ) -> dict[str, Any]:
        """Fetch payment details from Razorpay."""

        razorpay_payment_id = (
            self._validate_string(
                razorpay_payment_id,
                "Razorpay payment ID",
            )
        )

        try:
            payment = self.client.payment.fetch(
                razorpay_payment_id
            )
        except Exception as exc:
            raise PaymentServiceError(
                "Unable to fetch payment details."
            ) from exc

        if not payment:
            raise PaymentServiceError(
                "Payment details not found."
            )

        if not isinstance(
            payment,
            dict,
        ):
            raise PaymentServiceError(
                "Invalid payment response."
            )

        return payment

    # ============================================================
    # VALIDATE PAYMENT
    # ============================================================

    @classmethod
    def _validate_payment(
        cls,
        *,
        payment: dict[str, Any],
        razorpay_order_id: str,
        expected_amount: float,
    ) -> None:
        """Validate Razorpay payment against the order."""

        if not isinstance(
            payment,
            dict,
        ):
            raise PaymentServiceError(
                "Invalid payment data."
            )

        # --------------------------------------------------------
        # PAYMENT ORDER ID
        # --------------------------------------------------------

        payment_order_id = payment.get(
            "order_id"
        )

        payment_order_id = cls._validate_string(
            payment_order_id,
            "Payment Razorpay order ID",
        )

        if payment_order_id != razorpay_order_id:
            raise PaymentServiceError(
                "Payment does not belong to this order."
            )

        # --------------------------------------------------------
        # PAYMENT ID
        # --------------------------------------------------------

        payment_id = payment.get(
            "id"
        )

        payment_id = cls._validate_string(
            payment_id,
            "Payment ID",
        )

        # --------------------------------------------------------
        # AMOUNT
        # --------------------------------------------------------

        try:
            expected_amount_paise = int(
                round(
                    float(expected_amount) * 100
                )
            )
        except (TypeError, ValueError) as exc:
            raise PaymentServiceError(
                "Invalid expected payment amount."
            ) from exc

        try:
            actual_amount = int(
                payment.get("amount") or 0
            )
        except (TypeError, ValueError) as exc:
            raise PaymentServiceError(
                "Invalid payment amount."
            ) from exc

        if actual_amount <= 0:
            raise PaymentServiceError(
                "Payment amount must be greater than zero."
            )

        if (
            actual_amount
            != expected_amount_paise
        ):
            raise PaymentServiceError(
                "Payment amount mismatch."
            )

        # --------------------------------------------------------
        # CURRENCY
        # --------------------------------------------------------

        currency = payment.get(
            "currency"
        )

        if currency != "INR":
            raise PaymentServiceError(
                "Invalid payment currency."
            )

        # --------------------------------------------------------
        # STATUS
        # --------------------------------------------------------

        status = payment.get(
            "status"
        )

        if status != "captured":
            raise PaymentServiceError(
                "Payment is not captured."
            )

        # --------------------------------------------------------
        # METHOD
        # --------------------------------------------------------

        payment_method = payment.get(
            "method"
        )

        if not payment_method:
            raise PaymentServiceError(
                "Payment method was not returned by Razorpay."
            )

        # Keep variable explicitly used for
        # validation/readability.
        _ = payment_id

    # ============================================================
    # MARK ORDER PAID
    # ============================================================

    @classmethod
    async def _mark_order_paid(
        cls,
        *,
        order_id: ObjectId | str,
        updated_at: datetime,
    ) -> None:
        """Mark order as successfully paid and placed."""

        order_object_id = cls._to_object_id(
            order_id,
            "order ID",
        )

        if not isinstance(
            updated_at,
            datetime,
        ):
            raise PaymentServiceError(
                "Invalid payment update timestamp."
            )

        result = await orders_collection.update_one(
            {
                "_id": order_object_id,
                "paymentStatus": {
                    "$ne": "paid"
                },
            },
            {
                "$set": {
                    "paymentStatus": "paid",
                    "orderStatus": "placed",
                    "updatedAt": updated_at,
                }
            },
        )

        if result.modified_count > 0:
            return

        # --------------------------------------------------------
        # CHECK CURRENT STATE
        # --------------------------------------------------------

        order = await orders_collection.find_one(
            {
                "_id": order_object_id
            },
            {
                "paymentStatus": 1,
                "orderStatus": 1,
            },
        )

        if not order:
            raise PaymentServiceError(
                "Order not found while updating payment status."
            )

        if (
            order.get("paymentStatus")
            == "paid"
            and order.get("orderStatus")
            == "placed"
        ):
            return

        raise PaymentServiceError(
            "Failed to update order payment status."
        )


    # ============================================================
    # CLEAR CART ITEM
    # ============================================================

    @staticmethod
    async def _clear_cart(
        *,
        order: dict[str, Any],
    ) -> None:
        """Clear customer's cart after successful payment."""

        customer_id = order.get("customerId")

        if not customer_id:
            return

        if isinstance(customer_id, ObjectId):
            customer_object_id = customer_id
        else:
            customer_id_string = str(
                customer_id
            ).strip()

            if not ObjectId.is_valid(
                customer_id_string
            ):
                raise PaymentServiceError(
                    "Invalid customer ID."
                )

            customer_object_id = ObjectId(
                customer_id_string
            )

        try:
            await carts_collection.update_one(
                {
                    "customerId": customer_object_id
                },
                {
                    "$set": {
                        "items": [],
                        "updatedAt": datetime.now(
                            timezone.utc
                        ),
                    }
                },
            )
        except Exception as exc:
            raise PaymentServiceError(
                "Payment succeeded, but cart could not be cleared."
            ) from exc


    # ============================================================
    # JSON SAFE
    # ============================================================

    @classmethod
    def _make_json_safe(
        cls,
        value: Any,
    ) -> Any:
        """Convert MongoDB/Python values to JSON-safe values."""

        if isinstance(
            value,
            ObjectId,
        ):
            return str(value)

        if isinstance(
            value,
            datetime,
        ):
            return value.isoformat()

        if isinstance(
            value,
            Decimal,
        ):
            return float(value)

        if isinstance(
            value,
            dict,
        ):
            return {
                str(key): cls._make_json_safe(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(
            value,
            (list, tuple, set),
        ):
            return [
                cls._make_json_safe(item)
                for item in value
            ]

        return value


payment_service = PaymentService()