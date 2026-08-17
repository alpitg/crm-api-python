from datetime import datetime, timezone
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
    # CREATE RAZORPAY ORDER
    # ============================================================

    def create_razorpay_order(
        self,
        *,
        amount: float,
        order_id: ObjectId,
        order_code: str,
        invoice_id: ObjectId,
    ) -> dict[str, Any]:
        """Create a Razorpay order."""

        razorpay_amount = int(round(amount * 100))

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
                        "order_id": str(order_id),
                        "order_code": order_code,
                        "invoice_id": str(invoice_id),
                    },
                }
            )
        except Exception as exc:
            raise PaymentServiceError(
                "Failed to create Razorpay order."
            ) from exc

        if not isinstance(razorpay_order, dict):
            raise PaymentServiceError(
                "Invalid Razorpay response."
            )

        razorpay_order_id = razorpay_order.get("id")

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
        """
        Verify a Razorpay payment.

        Flow:
        1. Get order.
        2. Get invoice.
        3. Validate stored Razorpay order ID.
        4. Prevent duplicate payment.
        5. Verify Razorpay signature.
        6. Fetch payment from Razorpay.
        7. Validate payment amount/currency/status.
        8. Mark invoice as paid.
        9. Mark order as paid/placed.
        10. Return JSON-safe response.
        """

        if not razorpay_payment_id:
            raise PaymentServiceError(
                "Razorpay payment ID is required."
            )

        if not razorpay_order_id:
            raise PaymentServiceError(
                "Razorpay order ID is required."
            )

        if not razorpay_signature:
            raise PaymentServiceError(
                "Razorpay signature is required."
            )

        # ========================================================
        # CONVERT ORDER ID
        # ========================================================

        if isinstance(order_id, ObjectId):
            order_object_id = order_id
        elif ObjectId.is_valid(str(order_id)):
            order_object_id = ObjectId(str(order_id))
        else:
            raise PaymentServiceError(
                "Invalid order ID."
            )

        order = await self._get_order(order_object_id)

        invoice = await self._get_invoice(order)

        # ========================================================
        # ALREADY PAID
        # ========================================================

        if (
            order.get("paymentStatus") == "paid"
            and order.get("orderStatus") == "placed"
        ):
            return {
                "already_verified": True,
                "order": self._make_json_safe(order),
                "invoice": self._make_json_safe(invoice),
                "payment": None,
            }

        # ========================================================
        # STORED RAZORPAY ORDER ID
        # ========================================================

        razorpay_data = invoice.get("razorpay") or {}

        stored_razorpay_order_id = razorpay_data.get(
            "orderId"
        )

        if not stored_razorpay_order_id:
            raise PaymentServiceError(
                "Razorpay order ID not found for invoice."
            )

        if str(stored_razorpay_order_id) != str(
            razorpay_order_id
        ):
            raise PaymentServiceError(
                "Razorpay order ID mismatch."
            )

        # ========================================================
        # DUPLICATE PAYMENT
        # ========================================================

        self._check_existing_payment(
            invoice=invoice,
            razorpay_payment_id=razorpay_payment_id,
        )

        # ========================================================
        # VERIFY SIGNATURE
        # ========================================================

        self._verify_signature(
            razorpay_order_id=stored_razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )

        # ========================================================
        # FETCH PAYMENT
        # ========================================================

        payment = self._fetch_payment(
            razorpay_payment_id
        )

        # ========================================================
        # VALIDATE PAYMENT
        # ========================================================

        expected_amount = float(
            order.get("totalAmount") or 0
        )

        if expected_amount <= 0:
            raise PaymentServiceError(
                "Invalid order amount."
            )

        self._validate_payment(
            payment=payment,
            razorpay_order_id=stored_razorpay_order_id,
            expected_amount=expected_amount,
        )

        # ========================================================
        # UPDATE PAYMENT
        # ========================================================

        now = datetime.now(timezone.utc)

        invoice_id = invoice.get("_id")

        if not invoice_id:
            raise PaymentServiceError(
                "Invoice ID is missing."
            )

        try:
            await invoice_service.mark_as_paid(
                invoice_id=invoice_id,
                payment_id=razorpay_payment_id,
                razorpay_order_id=stored_razorpay_order_id,
                signature=razorpay_signature,
                payment_method=payment.get("method"),
                amount=expected_amount,
                paid_at=now,
            )
        except InvoiceServiceError as exc:
            raise PaymentServiceError(
                str(exc)
            ) from exc

        await self._mark_order_paid(
            order_id=order_id,
            updated_at=now,
        )

        # ========================================================
        # GET UPDATED DOCUMENTS
        # ========================================================

        updated_order = await self._get_order(
            order_id
        )

        updated_invoice = await invoice_service.get_invoice(
            invoice_id
        )

        if not updated_invoice:
            raise PaymentServiceError(
                "Updated invoice could not be retrieved."
            )

        # ========================================================
        # RESPONSE
        # ========================================================

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

    @staticmethod
    async def _get_order(
        order_id: ObjectId,
    ) -> dict[str, Any]:
        """Get an order by MongoDB ID."""

        if not isinstance(order_id, ObjectId):
            raise PaymentServiceError(
                "Invalid order ID."
            )

        order = await orders_collection.find_one(
            {"_id": order_id}
        )

        if not order:
            raise PaymentServiceError(
                "Order not found."
            )

        return order

    # ============================================================
    # GET INVOICE
    # ============================================================

    @staticmethod
    async def _get_invoice(
        order: dict[str, Any],
    ) -> dict[str, Any]:
        """Get the invoice belonging to an order."""

        invoice_id = order.get("invoiceId")

        if not invoice_id:
            raise PaymentServiceError(
                "Invoice not found for this order."
            )

        if isinstance(invoice_id, ObjectId):
            invoice_object_id = invoice_id
        else:
            invoice_id_string = str(invoice_id).strip()

            if not ObjectId.is_valid(
                invoice_id_string
            ):
                raise PaymentServiceError(
                    "Invalid invoice ID."
                )

            invoice_object_id = ObjectId(
                invoice_id_string
            )

        try:
            invoice = await invoice_service.get_invoice(
                invoice_object_id
            )
        except InvoiceServiceError as exc:
            raise PaymentServiceError(
                str(exc)
            ) from exc

        if not invoice:
            raise PaymentServiceError(
                "Invoice not found."
            )

        return invoice

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

        razorpay_data = invoice.get("razorpay") or {}

        existing_payment_id = razorpay_data.get(
            "paymentId"
        )

        if not existing_payment_id:
            return

        if str(existing_payment_id) == str(
            razorpay_payment_id
        ):
            raise PaymentServiceError(
                "Payment already verified."
            )

        raise PaymentServiceError(
            "Invoice already has a different payment."
        )

    # ============================================================
    # VERIFY RAZORPAY SIGNATURE
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
                    "razorpay_order_id": razorpay_order_id,
                    "razorpay_payment_id": razorpay_payment_id,
                    "razorpay_signature": razorpay_signature,
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

        if not isinstance(payment, dict):
            raise PaymentServiceError(
                "Invalid payment response."
            )

        return payment

    # ============================================================
    # VALIDATE PAYMENT
    # ============================================================

    @staticmethod
    def _validate_payment(
        *,
        payment: dict[str, Any],
        razorpay_order_id: str,
        expected_amount: float,
    ) -> None:
        """Validate Razorpay payment against the order."""

        # --------------------------------------------------------
        # RAZORPAY ORDER ID
        # --------------------------------------------------------

        payment_order_id = payment.get(
            "order_id"
        )

        if payment_order_id != razorpay_order_id:
            raise PaymentServiceError(
                "Payment does not belong to this order."
            )

        # --------------------------------------------------------
        # AMOUNT
        # --------------------------------------------------------

        expected_amount_paise = int(
            round(expected_amount * 100)
        )

        try:
            actual_amount = int(
                payment.get("amount") or 0
            )
        except (TypeError, ValueError) as exc:
            raise PaymentServiceError(
                "Invalid payment amount."
            ) from exc

        if actual_amount != expected_amount_paise:
            raise PaymentServiceError(
                "Payment amount mismatch."
            )

        # --------------------------------------------------------
        # CURRENCY
        # --------------------------------------------------------

        if payment.get("currency") != "INR":
            raise PaymentServiceError(
                "Invalid payment currency."
            )

        # --------------------------------------------------------
        # STATUS
        # --------------------------------------------------------

        if payment.get("status") != "captured":
            raise PaymentServiceError(
                "Payment is not captured."
            )

    # ============================================================
    # MARK ORDER PAID
    # ============================================================

    @staticmethod
    async def _mark_order_paid(
        *,
        order_id: ObjectId,
        updated_at: datetime,
    ) -> None:
        """Mark order as successfully paid and placed."""

        result = await orders_collection.update_one(
            {
                "_id": order_id,
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

        if result.matched_count == 0:
            # Check whether the order was already paid.
            order = await orders_collection.find_one(
                {"_id": order_id},
                {
                    "paymentStatus": 1,
                    "orderStatus": 1,
                },
            )

            if (
                order
                and order.get("paymentStatus")
                == "paid"
            ):
                return

            raise PaymentServiceError(
                "Failed to update order payment status."
            )

    # ============================================================
    # JSON SAFE CONVERSION
    # ============================================================

    @classmethod
    def _make_json_safe(
        cls,
        value: Any,
    ) -> Any:
        """
        Convert MongoDB/Python values into values that
        FastAPI can serialize as JSON.
        """

        if isinstance(value, ObjectId):
            return str(value)

        if isinstance(value, datetime):
            return value.isoformat()

        if isinstance(value, dict):
            return {
                str(key): cls._make_json_safe(
                    item
                )
                for key, item in value.items()
            }

        if isinstance(value, list):
            return [
                cls._make_json_safe(item)
                for item in value
            ]

        if isinstance(value, tuple):
            return [
                cls._make_json_safe(item)
                for item in value
            ]

        return value


payment_service = PaymentService()