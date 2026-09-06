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

router = APIRouter()


@router.post("/send")
async def send_otp(
    payload: SendOTPRequest,
):
    """
    Send OTP to customer's email or mobile number.
    """

    login_type="email" if payload.email else "mobile"

    result = await send_login_otp(
        email=payload.email,
        mobile=payload.mobile,
        login_type=login_type,
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
        "loginType": result.get(
            "loginType",
            login_type,
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


@router.post("/resend")
async def resend_otp(
    payload: ResendOTPRequest,
):
    """
    Resend OTP to customer's email or mobile number.
    """

    login_type="email" if payload.email else "mobile"

    result = await resend_login_otp(
        email=payload.email,
        mobile=payload.mobile,
        login_type=login_type,
    )

    if not result.get("success"):
        message = result.get(
            "message",
            "Unable to resend OTP.",
        )

        if "wait" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
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
        "loginType": result.get(
            "loginType",
            login_type,
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


@router.post("/verify")
async def verify_otp(
    payload: VerifyOTPRequest,
):
    """
    Verify OTP and authenticate customer.

    Supports:
    - Email OTP
    - Mobile OTP
    """

    login_type="email" if payload.email else "mobile"

    result = await verify_login_otp(
        email=payload.email,
        mobile=payload.mobile,
        otp=payload.otp,
        login_type=login_type,
    )

    if not result.get("success"):
        message = result.get(
            "message",
            "Unable to verify OTP.",
        )

        if "inactive" in message.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=message,
            )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=message,
        )

    customer = result.get("customer")

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Customer information was not found.",
        )

    return {
        "success": True,
        "message": result.get("message", "Login successful."),
        "loginType": result.get("loginType", login_type),
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
