from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.db.mongo import db


invoices_collection = db["invoices"]


class InvoiceServiceError(Exception):
    """Raised when invoice processing fails."""


class InvoiceService:
    @staticmethod
    def _utc_now() -> datetime:
        """Return the current UTC datetime."""
        return datetime.now(timezone.utc)

    @staticmethod
    def _validate_object_id(
        value: ObjectId,
        field_name: str,
    ) -> None:
        """Validate a MongoDB ObjectId."""
        if not isinstance(value, ObjectId):
            raise InvoiceServiceError(
                f"Invalid {field_name}."
            )

    async def create_invoice(
        self,
        *,
        order_id: ObjectId,
        customer_name: str,
        total_amount: float,
        payment_method: str = "online",
        payment_provider: str = "razorpay",
        now: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Create a pending invoice for an order.

        Payment verification is handled separately by PaymentService.
        """
        self._validate_object_id(
            order_id,
            "order ID",
        )

        if not customer_name:
            raise InvoiceServiceError(
                "Customer name is required."
            )

        total_amount = round(
            float(total_amount),
            2,
        )

        if total_amount <= 0:
            raise InvoiceServiceError(
                "Invoice amount must be greater than zero."
            )

        created_at = now or self._utc_now()

        invoice_doc = {
            "orderIds": [order_id],
            "billDate": None,
            "billFrom": None,
            "billTo": {
                "name": customer_name,
                "address": None,
                "detail": None,
                "phone": None,
                "email": None,
                "gstin": None,
            },
            "paymentMode": payment_method,
            "paymentProvider": payment_provider,
            "paymentMethod": None,
            "advancePaid": 0.0,
            "generateInvoice": True,
            "paymentStatus": "pending",
            "totalAmount": total_amount,
            "balanceAmount": total_amount,
            "razorpay": {
                "orderId": None,
                "paymentId": None,
                "signature": None,
            },
            "createdAt": created_at,
            "updatedAt": created_at,
        }

        try:
            result = await invoices_collection.insert_one(
                invoice_doc
            )
        except Exception as exc:
            raise InvoiceServiceError(
                "Failed to create invoice."
            ) from exc

        if not result.inserted_id:
            raise InvoiceServiceError(
                "Failed to create invoice."
            )

        invoice = await invoices_collection.find_one(
            {"_id": result.inserted_id}
        )

        if not invoice:
            raise InvoiceServiceError(
                "Invoice was created but could not be retrieved."
            )

        return invoice

    async def set_razorpay_order_id(
        self,
        *,
        invoice_id: ObjectId,
        razorpay_order_id: str,
    ) -> dict[str, Any]:
        """
        Store the Razorpay order ID against the invoice.
        """
        self._validate_object_id(
            invoice_id,
            "invoice ID",
        )

        if not razorpay_order_id:
            raise InvoiceServiceError(
                "Razorpay order ID is required."
            )

        now = self._utc_now()

        result = await invoices_collection.update_one(
            {"_id": invoice_id},
            {
                "$set": {
                    "razorpay.orderId": razorpay_order_id,
                    "updatedAt": now,
                }
            },
        )

        if result.matched_count == 0:
            raise InvoiceServiceError(
                "Invoice not found."
            )

        invoice = await invoices_collection.find_one(
            {"_id": invoice_id}
        )

        if not invoice:
            raise InvoiceServiceError(
                "Invoice not found after update."
            )

        return invoice

    async def mark_as_paid(
        self,
        *,
        invoice_id: ObjectId,
        payment_id: str,
        razorpay_order_id: str,
        signature: str,
        payment_method: str | None,
        amount: float,
        paid_at: datetime | None = None,
    ) -> dict[str, Any]:
        """
        Mark an invoice as paid.

        Razorpay signature verification must already have been
        performed by PaymentService before calling this method.
        """
        self._validate_object_id(
            invoice_id,
            "invoice ID",
        )

        if not payment_id:
            raise InvoiceServiceError(
                "Payment ID is required."
            )

        if not razorpay_order_id:
            raise InvoiceServiceError(
                "Razorpay order ID is required."
            )

        if not signature:
            raise InvoiceServiceError(
                "Payment signature is required."
            )

        amount = round(
            float(amount),
            2,
        )

        if amount <= 0:
            raise InvoiceServiceError(
                "Payment amount must be greater than zero."
            )

        invoice = await invoices_collection.find_one(
            {"_id": invoice_id}
        )

        if not invoice:
            raise InvoiceServiceError(
                "Invoice not found."
            )

        # ---------------------------------------------
        # Idempotency
        # ---------------------------------------------

        existing_payment_id = (
            invoice.get("razorpay", {}).get("paymentId")
        )

        if existing_payment_id:
            if existing_payment_id == payment_id:
                return invoice

            raise InvoiceServiceError(
                "Invoice already has a different payment."
            )

        # ---------------------------------------------
        # Verify Razorpay order ID
        # ---------------------------------------------

        stored_order_id = (
            invoice.get("razorpay", {}).get("orderId")
        )

        if not stored_order_id:
            raise InvoiceServiceError(
                "Razorpay order ID is not stored on the invoice."
            )

        if stored_order_id != razorpay_order_id:
            raise InvoiceServiceError(
                "Razorpay order ID does not match the invoice."
            )

        # ---------------------------------------------
        # Verify payment amount
        # ---------------------------------------------

        invoice_amount = round(
            float(
                invoice.get(
                    "totalAmount",
                    0,
                )
            ),
            2,
        )

        if abs(amount - invoice_amount) > 0.01:
            raise InvoiceServiceError(
                "Payment amount does not match the invoice amount."
            )

        # ---------------------------------------------
        # Already paid protection
        # ---------------------------------------------

        if invoice.get("paymentStatus") == "paid":
            raise InvoiceServiceError(
                "Invoice is already marked as paid."
            )

        payment_time = paid_at or self._utc_now()

        update = {
            "paymentStatus": "paid",
            "paymentMode": "online",
            "paymentProvider": "razorpay",
            "paymentMethod": payment_method or "online",
            "advancePaid": amount,
            "balanceAmount": 0.0,
            "razorpay.paymentId": payment_id,
            "razorpay.orderId": razorpay_order_id,
            "razorpay.signature": signature,
            "paidAt": payment_time,
            "updatedAt": payment_time,
        }

        try:
            result = await invoices_collection.update_one(
                {
                    "_id": invoice_id,
                    "paymentStatus": {
                        "$ne": "paid"
                    },
                },
                {
                    "$set": update,
                },
            )
        except Exception as exc:
            raise InvoiceServiceError(
                "Failed to update invoice payment."
            ) from exc

        if result.matched_count == 0:
            # Another request may have completed the payment
            # between the initial read and this update.
            latest_invoice = (
                await invoices_collection.find_one(
                    {"_id": invoice_id}
                )
            )

            if (
                latest_invoice
                and latest_invoice.get("razorpay", {}).get(
                    "paymentId"
                )
                == payment_id
            ):
                return latest_invoice

            raise InvoiceServiceError(
                "Invoice could not be marked as paid."
            )

        updated_invoice = (
            await invoices_collection.find_one(
                {"_id": invoice_id}
            )
        )

        if not updated_invoice:
            raise InvoiceServiceError(
                "Invoice could not be retrieved after payment."
            )

        return updated_invoice

    async def get_invoice(
        self,
        invoice_id: ObjectId,
    ) -> dict[str, Any]:
        """Get an invoice by MongoDB ID."""
        self._validate_object_id(
            invoice_id,
            "invoice ID",
        )

        invoice = await invoices_collection.find_one(
            {"_id": invoice_id}
        )

        if not invoice:
            raise InvoiceServiceError(
                "Invoice not found."
            )

        return invoice

    async def get_invoice_by_order_id(
        self,
        order_id: ObjectId,
    ) -> dict[str, Any]:
        """Get the invoice belonging to an order."""
        self._validate_object_id(
            order_id,
            "order ID",
        )

        invoice = await invoices_collection.find_one(
            {"orderIds": order_id}
        )

        if not invoice:
            raise InvoiceServiceError(
                "Invoice not found for this order."
            )

        return invoice

    async def update_bill_to(
        self,
        *,
        invoice_id: ObjectId,
        bill_to: dict[str, Any],
    ) -> dict[str, Any]:
        """Update invoice customer/billing information."""
        self._validate_object_id(
            invoice_id,
            "invoice ID",
        )

        if not bill_to:
            raise InvoiceServiceError(
                "Billing information is required."
            )

        now = self._utc_now()

        result = await invoices_collection.update_one(
            {"_id": invoice_id},
            {
                "$set": {
                    "billTo": bill_to,
                    "updatedAt": now,
                }
            },
        )

        if result.matched_count == 0:
            raise InvoiceServiceError(
                "Invoice not found."
            )

        invoice = await invoices_collection.find_one(
            {"_id": invoice_id}
        )

        if not invoice:
            raise InvoiceServiceError(
                "Invoice not found after update."
            )

        return invoice

    async def cancel_invoice(
        self,
        *,
        invoice_id: ObjectId,
        reason: str | None = None,
    ) -> dict[str, Any]:
        """
        Cancel an unpaid invoice.

        Paid invoices must go through the refund flow.
        """
        self._validate_object_id(
            invoice_id,
            "invoice ID",
        )

        invoice = await invoices_collection.find_one(
            {"_id": invoice_id}
        )

        if not invoice:
            raise InvoiceServiceError(
                "Invoice not found."
            )

        payment_status = invoice.get(
            "paymentStatus"
        )

        if payment_status == "paid":
            raise InvoiceServiceError(
                "Paid invoice cannot be cancelled. "
                "Use the refund flow."
            )

        if payment_status == "cancelled":
            return invoice

        now = self._utc_now()

        update: dict[str, Any] = {
            "paymentStatus": "cancelled",
            "updatedAt": now,
        }

        if reason:
            update["cancellationReason"] = reason

        result = await invoices_collection.update_one(
            {
                "_id": invoice_id,
                "paymentStatus": {
                    "$ne": "paid"
                },
            },
            {
                "$set": update
            },
        )

        if result.matched_count == 0:
            raise InvoiceServiceError(
                "Invoice could not be cancelled."
            )

        cancelled_invoice = (
            await invoices_collection.find_one(
                {"_id": invoice_id}
            )
        )

        if not cancelled_invoice:
            raise InvoiceServiceError(
                "Invoice not found after cancellation."
            )

        return cancelled_invoice

    async def delete_invoice(
        self,
        invoice_id: ObjectId,
    ) -> None:
        """
        Delete an invoice.

        Used primarily for checkout rollback when invoice/payment
        initialization fails.
        """
        self._validate_object_id(
            invoice_id,
            "invoice ID",
        )

        try:
            await invoices_collection.delete_one(
                {"_id": invoice_id}
            )
        except Exception as exc:
            raise InvoiceServiceError(
                "Failed to delete invoice."
            ) from exc


invoice_service = InvoiceService()