from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.mongo import db
from app.modules.orders.schemas.orders import (
    PublicOrderIn,
    VerifyWebsitePaymentIn,
)
from app.modules.website.order.schemas.orders_schema import (
    WebsiteOrdersResponse,
)
from app.modules.website.order.services.checkout_service import (
    CheckoutService,
    CheckoutServiceError,
)
from app.modules.website.order.services.order_service import (
    WebsiteOrderService,
)
from app.modules.website.order.services.payment_service import (
    PaymentServiceError,
    payment_service,
)
from app.services.auth.token_service import get_current_customer
from core.sanitize import stringify_object_ids


router = APIRouter()

orders_collection = db["orders"]

order_service = WebsiteOrderService(
    orders_collection=orders_collection,
)

checkout_service = CheckoutService()


@router.get(
    "/search",
    response_model=WebsiteOrdersResponse,
)
async def get_my_orders(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_customer),
):
    customer_id = current_user["_id"]

    result = await order_service.get_customer_orders(
        customer_id=customer_id,
        page=page,
        limit=limit,
    )

    return stringify_object_ids(
        {
            "success": True,
            "orders": result["orders"],
            "pagination": {
                "page": result["page"],
                "limit": result["limit"],
                "total": result["total"],
                "pages": result["pages"],
            },
        }
    )


@router.post(
    "/checkout",
    status_code=status.HTTP_201_CREATED,
)
async def create_public_checkout(
    payload: PublicOrderIn,
):
    """
    Create a public website checkout.

    For online payment, this creates the order,
    invoice, and Razorpay order.

    For COD, the order is placed immediately
    with pending payment status.
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
    """Verify a Razorpay payment for a public checkout."""
    try:
        result = await payment_service.verify_payment(
            order_id=payload.orderId,
            razorpay_payment_id=payload.razorpayPaymentId,
            razorpay_order_id=payload.razorpayOrderId,
            razorpay_signature=payload.razorpaySignature,
        )

        return {
            "success": True,
            "message": (
                "Payment already verified."
                if result.get("already_verified")
                else "Payment verified successfully."
            ),
            "order": stringify_object_ids(
                result["order"]
            ),
            "invoice": stringify_object_ids(
                result["invoice"]
            ),
            "payment": result.get("payment"),
            "paid_at": result.get("paid_at"),
        }

    except PaymentServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
