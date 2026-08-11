from fastapi import APIRouter, HTTPException

from app.modules.website.auth.schemas.login_schema import WebsiteLoginRequest
from app.services.auth.login_service import login_customer

router = APIRouter()


@router.post("/login")
async def website_login(
    payload: WebsiteLoginRequest,
):
    customer = await login_customer(
        mobile=payload.mobile,
    )

    if not customer:
        raise HTTPException(
            status_code=401,
            detail="Invalid mobile number.",
        )

    return {
        "success": True,
        "message": "Login successful.",
        "user": {
            "id": str(customer["_id"]),
            "mobile": customer.get("mobile"),
            "name": customer.get("name"),
            "email": customer.get("email"),
        },
    }