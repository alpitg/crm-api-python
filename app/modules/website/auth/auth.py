from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.auth.token_service import (
    get_current_customer,
    logout_customer,
    refresh_access_token,
)


router = APIRouter()


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(
        ...,
        min_length=1,
    )


@router.post("/refresh")
async def refresh_token(
    payload: RefreshTokenRequest,
):
    """
    Generate a new access token using refresh token.
    """

    try:
        result = refresh_access_token(
            refresh_token=payload.refresh_token,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        ) from exc

    if not result.get("success"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=result.get(
                "message",
                "Invalid or expired refresh token.",
            ),
        )

    return {
        "success": True,
        "message": "Token refreshed successfully.",
        "access_token": result["access_token"],
        "refresh_token": result.get(
            "refresh_token",
            payload.refresh_token,
        ),
        "token_type": "bearer",
    }


@router.get("/me")
async def get_current_user(
    customer=Depends(get_current_customer),
):
    """
    Get currently authenticated customer.
    """

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    return {
        "success": True,
        "user": {
            "id": str(customer["_id"]),
            "mobile": customer.get("mobile"),
            "name": customer.get("name"),
            "email": customer.get("email"),
        },
    }


@router.post("/logout")
async def logout(
    customer=Depends(get_current_customer),
):
    """
    Logout currently authenticated customer.

    The service should revoke/delete the customer's
    active refresh session.
    """

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
        )

    await logout_customer(
        customer_id=str(customer["_id"]),
    )

    return {
        "success": True,
        "message": "Logged out successfully.",
    }