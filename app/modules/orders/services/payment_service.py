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
        """
        Create a Razorpay order.

        Amount is received in INR and converted to paise.
        """

        razorpay_amount = int(
            round(amount * 100)
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
        order_id: ObjectId,
        razorpay_payment_id: str,
        razorpay_order_id: str,
        razorpay_signature: str,
    ) -> dict[str, Any]:
        """
        Verify a Razorpay payment.

        Validation flow:

        1. Load order.
        2. Load invoice.
        3. Validate Razorpay order ID.
        4. Prevent duplicate payment verification.
        5. Verify Razorpay signature.
        6. Fetch payment from Razorpay.
        7. Validate amount/currency/order/status.
        8. Mark invoice as paid.
        9. Mark order as placed.
        """

        order = await self._get_order(
            order_id
        )

        invoice = await self._get_invoice(
            order
        )

        # --------------------------------------------------------
        # Already paid
        # --------------------------------------------------------

        if (
            order.get("paymentStatus") == "paid"
            and order.get("orderStatus") == "placed"
        ):
            return {
                "already_verified": True,
                "order": order,
                "invoice": invoice,
                "payment": None,
            }

        # --------------------------------------------------------
        # Validate Razorpay order
        # --------------------------------------------------------

        stored_razorpay_order_id = (
            invoice
            .get("razorpay", {})
            .get("orderId")
        )

        if not stored_razorpay_order_id:
            raise PaymentServiceError(
                "Razorpay order ID not found for invoice."
            )

        if (
            stored_razorpay_order_id
            != razorpay_order_id
        ):
            raise PaymentServiceError(
                "Razorpay order ID mismatch."
            )

        # --------------------------------------------------------
        # Prevent duplicate payment
        # --------------------------------------------------------

        self._check_existing_payment(
            invoice=invoice,
            razorpay_payment_id=razorpay_payment_id,
        )

        # --------------------------------------------------------
        # Verify Razorpay signature
        # --------------------------------------------------------

        self._verify_signature(
            razorpay_order_id=stored_razorpay_order_id,
            razorpay_payment_id=razorpay_payment_id,
            razorpay_signature=razorpay_signature,
        )

        # --------------------------------------------------------
        # Fetch payment from Razorpay
        # --------------------------------------------------------

        payment = self._fetch_payment(
            razorpay_payment_id
        )

        # --------------------------------------------------------
        # Validate payment
        # --------------------------------------------------------

        expected_amount = float(
            order.get("totalAmount", 0)
        )

        self._validate_payment(
            payment=payment,
            razorpay_order_id=stored_razorpay_order_id,
            expected_amount=expected_amount,
        )

        # --------------------------------------------------------
        # Mark invoice and order as paid
        # --------------------------------------------------------

        now = datetime.now(timezone.utc)

        try:
            await invoice_service.mark_as_paid(
                invoice_id=invoice["_id"],
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

        # --------------------------------------------------------
        # Get updated documents
        # --------------------------------------------------------

        updated_order = await self._get_order(
            order_id
        )

        updated_invoice = await invoice_service.get_invoice(
            invoice["_id"]
        )

        return {
            "already_verified": False,
            "order": updated_order,
            "invoice": updated_invoice,
            "payment": payment,
            "paid_at": now,
        }

    # ============================================================
    # GET ORDER
    # ============================================================

    @staticmethod
    async def _get_order(
        order_id: ObjectId,
    ) -> dict[str, Any]:
        """Get order by MongoDB ID."""

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
        """Get invoice belonging to an order."""

        invoice_id = order.get("invoiceId")

        if not invoice_id:
            raise PaymentServiceError(
                "Invoice not found for this order."
            )

        if isinstance(invoice_id, ObjectId):
            invoice_object_id = invoice_id

        elif ObjectId.is_valid(str(invoice_id)):
            invoice_object_id = ObjectId(
                str(invoice_id)
            )

        else:
            raise PaymentServiceError(
                "Invalid invoice ID."
            )

        try:
            return await invoice_service.get_invoice(
                invoice_object_id
            )
        except InvoiceServiceError as exc:
            raise PaymentServiceError(
                str(exc)
            ) from exc

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

        existing_payment_id = (
            invoice
            .get("razorpay", {})
            .get("paymentId")
        )

        if not existing_payment_id:
            return

        if existing_payment_id == razorpay_payment_id:
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
        """Verify Razorpay payment signature."""

        if not razorpay_order_id:
            raise PaymentServiceError(
                "Razorpay order ID is required."
            )

        if not razorpay_payment_id:
            raise PaymentServiceError(
                "Razorpay payment ID is required."
            )

        if not razorpay_signature:
            raise PaymentServiceError(
                "Razorpay signature is required."
            )

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
        """Fetch payment details directly from Razorpay."""

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
        """
        Validate Razorpay payment against our order.

        Checks:

        - Razorpay order ID
        - Amount
        - Currency
        - Captured status
        """

        # --------------------------------------------------------
        # Order ID
        # --------------------------------------------------------

        payment_order_id = payment.get(
            "order_id"
        )

        if payment_order_id != razorpay_order_id:
            raise PaymentServiceError(
                "Payment does not belong to this order."
            )

        # --------------------------------------------------------
        # Amount
        # --------------------------------------------------------

        expected_amount_paise = int(
            round(expected_amount * 100)
        )

        actual_amount = int(
            payment.get("amount") or 0
        )

        if actual_amount != expected_amount_paise:
            raise PaymentServiceError(
                "Payment amount mismatch."
            )

        # --------------------------------------------------------
        # Currency
        # --------------------------------------------------------

        if payment.get("currency") != "INR":
            raise PaymentServiceError(
                "Invalid payment currency."
            )

        # --------------------------------------------------------
        # Payment status
        # --------------------------------------------------------

        if payment.get("status") != "captured":
            raise PaymentServiceError(
                "Payment is not captured."
            )

    # ============================================================
    # MARK ORDER AS PAID
    # ============================================================

    @staticmethod
    async def _mark_order_paid(
        *,
        order_id: ObjectId,
        updated_at: datetime,
    ) -> None:
        """Mark order as successfully paid and placed."""

        result = await orders_collection.update_one(
            {"_id": order_id},
            {
                "$set": {
                    "paymentStatus": "paid",
                    "orderStatus": "placed",
                    "updatedAt": updated_at,
                }
            },
        )

        if result.matched_count == 0:
            raise PaymentServiceError(
                "Failed to update order payment status."
            )


payment_service = PaymentService()