from fastapi import APIRouter, HTTPException, status

from app.modules.website.auth.schemas.otp_schema import (
    ResendOTPRequest,
    SendOTPRequest,
    VerifyOTPRequest,
)

from app.services.auth.otp_service import (
    resend_login_otp,
    send_login_otp,
    verify_login_otp,
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter()


# ============================================================
# SEND OTP
# ============================================================


@router.post("/send")
async def send_otp(
    payload: SendOTPRequest,
):
    """
    Send OTP to customer's mobile number.

    Flow:

        User enters mobile
                ↓
            POST /send
                ↓
            OTP generated
                ↓
            OTP sent by SMS
    """

    result = await send_login_otp(
        mobile=payload.mobile,
    )

    if not result.get("success"):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.get(
                "message",
                "Unable to send OTP.",
            ),
        )

    return {
        "success": True,
        "message": result.get(
            "message",
            "OTP sent successfully.",
        ),
        "expiresIn": result.get(
            "expiresIn",
            300,
        ),
        "retryAfter": result.get(
            "retryAfter",
            30,
        ),
    }


# ============================================================
# RESEND OTP
# ============================================================


@router.post("/resend")
async def resend_otp(
    payload: ResendOTPRequest,
):
    """
    Resend OTP to customer's mobile number.
    """

    result = await resend_login_otp(
        mobile=payload.mobile,
    )

    if not result.get("success"):

        message = result.get(
            "message",
            "Unable to resend OTP.",
        )

        # Cooldown errors should be 429.
        if "wait" in message.lower():

            raise HTTPException(
                status_code=(
                    status.HTTP_429_TOO_MANY_REQUESTS
                ),
                detail=message,
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )

    return {
        "success": True,
        "message": result.get(
            "message",
            "OTP resent successfully.",
        ),
        "expiresIn": result.get(
            "expiresIn",
            300,
        ),
        "retryAfter": result.get(
            "retryAfter",
            30,
        ),
    }


# ============================================================
# VERIFY OTP
# ============================================================


@router.post("/verify")
async def verify_otp(
    payload: VerifyOTPRequest,
):
    """
    Verify OTP and authenticate customer.

    Successful response contains:

        customer.id
        customer.mobile
        customer.name
        customer.email

        access_token
        refresh_token
        token_type
        expiresIn
    """

    result = await verify_login_otp(
        mobile=payload.mobile,
        otp=payload.otp,
    )

    # --------------------------------------------------------
    # OTP / LOGIN FAILURE
    # --------------------------------------------------------

    if not result.get("success"):

        message = result.get(
            "message",
            "Unable to verify OTP.",
        )

        if (
            "inactive"
            in message.lower()
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=message,
            )

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=message,
        )

    # --------------------------------------------------------
    # CUSTOMER
    # --------------------------------------------------------

    customer = result.get(
        "customer"
    )

    if not customer:

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail="Customer information was not found.",
        )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

    return {
        "success": True,
        "message": result.get("message", "Login successful."),
        "customer": {
            "id": customer.get("id"),
            "mobile": customer.get("mobile"),
            "name": customer.get("name"),
            "email": customer.get("email"),
        },
        "access_token": result.get("access_token"),
        "refresh_token": result.get("refresh_token"),
        "token_type": result.get("token_type", "bearer"),
        "expiresIn": result.get("expiresIn", 1800),
    }