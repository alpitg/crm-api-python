from fastapi import APIRouter, HTTPException, status

from app.modules.orders.schemas.orders import (
    PublicOrderIn,
    VerifyWebsitePaymentIn,
)
from app.modules.orders.services.checkout_service import (
    CheckoutServiceError,
    checkout_service,
)
from app.modules.orders.services.payment_service import (
    PaymentServiceError,
    payment_service,
)
from core.sanitize import stringify_object_ids

router = APIRouter()


@router.post(
    "/checkout",
    status_code=status.HTTP_201_CREATED,
)
async def create_public_checkout(payload: PublicOrderIn):
    """
    Create a public website checkout.

    For online payment, this creates the order, invoice,
    and Razorpay order.

    For COD, the order is placed immediately with pending
    payment status.
    """
    try:
        return await checkout_service.create_checkout(payload)
    except CheckoutServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post("/verify-payment")
async def verify_public_payment(
    payload: VerifyWebsitePaymentIn,
):
    """
    Verify a Razorpay payment for a public checkout.
    """
    try:
        result = await payment_service.verify_payment(
            order_id=payload.orderId,
            razorpay_payment_id=payload.razorpayPaymentId,
            razorpay_order_id=payload.razorpayOrderId,
            razorpay_signature=payload.razorpaySignature,
        )

        return {
            "success": True,
            "message": "Payment verified successfully",
            "order": stringify_object_ids(
                result["order"]
            ),
            "invoice": stringify_object_ids(
                result["invoice"]
            ),
            "payment": result["payment"],
        }

    except PaymentServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc