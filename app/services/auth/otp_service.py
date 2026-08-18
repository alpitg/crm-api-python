from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db.mongo import db
from app.services.auth.token_service import create_auth_tokens
from app.services.auth.otp.factory import get_otp_provider

OTP_EXPIRY_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 30
DEFAULT_OTP_PROVIDER = "twilio"

website_otps_collection = db["website_otps"]
customers_collection = db["customers"]

def _now() -> datetime:
    return datetime.now(timezone.utc)

def _normalize_mobile(mobile: str) -> str:
    if not mobile:
        raise ValueError("Mobile number is required.")

    mobile = mobile.strip()
    mobile = "".join(character for character in mobile if character.isdigit())

    if len(mobile) != 10:
        raise ValueError("Please enter a valid 10-digit mobile number.")

    if not mobile.startswith(("6", "7", "8", "9")):
        raise ValueError("Please enter a valid mobile number.")

    return mobile

def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value

async def generate_and_store_otp(
    mobile: str,
    provider: str = DEFAULT_OTP_PROVIDER,
) -> dict:
    mobile = _normalize_mobile(mobile)
    now = _now()

    otp_provider = get_otp_provider(provider)

    existing_otp = await website_otps_collection.find_one(
        {"mobile": mobile}
    )

    if existing_otp:
        last_sent_at = existing_otp.get("created_at")

        if last_sent_at:
            last_sent_at = _normalize_datetime(last_sent_at)
            elapsed = (now - last_sent_at).total_seconds()

            if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
                remaining = max(
                    1,
                    int(
                        OTP_RESEND_COOLDOWN_SECONDS - elapsed
                    ),
                )

                raise ValueError(
                    f"Please wait {remaining} seconds "
                    "before requesting another OTP."
                )

    provider_result = await otp_provider.send_otp(
        mobile=mobile
    )

    if not provider_result.get("success"):
        raise RuntimeError("Unable to send OTP.")

    expires_at = now + timedelta(
        minutes=OTP_EXPIRY_MINUTES
    )

    await website_otps_collection.update_one(
        {"mobile": mobile},
        {
            "$set": {
                "mobile": mobile,
                "created_at": now,
                "expiresAt": expires_at,
                "verified": False,
                "verified_at": None,
                "provider": provider,
                "provider_reference": provider_result.get(
                    "provider_reference"
                ),
            }
        },
        upsert=True,
    )

    return {
        "mobile": mobile,
        "expiresAt": expires_at,
        "expiresIn": OTP_EXPIRY_MINUTES * 60,
        "retryAfter": OTP_RESEND_COOLDOWN_SECONDS,
        "provider": provider,
    }

async def send_login_otp(mobile: str) -> dict:
    try:
        result = await generate_and_store_otp(
            mobile=mobile,
            provider=DEFAULT_OTP_PROVIDER,
        )
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    except Exception as exc:
        print("Unable to send login OTP:", str(exc))
        return {
            "success": False,
            "message": "Unable to send OTP.",
        }

    return {
        "success": True,
        "message": "OTP sent successfully.",
        "mobile": result["mobile"],
        "expiresIn": result["expiresIn"],
        "retryAfter": result["retryAfter"],
    }

async def resend_login_otp(mobile: str) -> dict:
    try:
        result = await generate_and_store_otp(
            mobile=mobile,
            provider=DEFAULT_OTP_PROVIDER,
        )
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
        }
    except Exception as exc:
        print("Unable to resend login OTP:", str(exc))
        return {
            "success": False,
            "message": "Unable to resend OTP.",
        }

    return {
        "success": True,
        "message": "OTP resent successfully.",
        "mobile": result["mobile"],
        "expiresIn": result["expiresIn"],
        "retryAfter": result["retryAfter"],
    }

async def verify_otp(
    mobile: str,
    otp: str,
) -> bool:
    try:
        mobile = _normalize_mobile(mobile)
    except ValueError:
        return False

    if not otp:
        return False

    otp = otp.strip()

    if len(otp) != 6 or not otp.isdigit():
        return False

    otp_record = await website_otps_collection.find_one(
        {"mobile": mobile}
    )

    if not otp_record:
        return False

    if otp_record.get("verified", False):
        return False

    expires_at = otp_record.get("expiresAt")

    if not expires_at:
        await website_otps_collection.delete_one(
            {"_id": otp_record["_id"]}
        )
        return False

    expires_at = _normalize_datetime(expires_at)

    if _now() >= expires_at:
        await website_otps_collection.delete_one(
            {"_id": otp_record["_id"]}
        )
        return False

    provider_name = otp_record.get(
        "provider",
        DEFAULT_OTP_PROVIDER,
    )

    otp_provider = get_otp_provider(provider_name)

    verified = await otp_provider.verify_otp(
        mobile=mobile,
        otp=otp,
    )

    if not verified:
        return False

    await website_otps_collection.update_one(
        {"_id": otp_record["_id"]},
        {
            "$set": {
                "verified": True,
                "verified_at": _now(),
            }
        },
    )

    return True

async def verify_login_otp(
    mobile: str,
    otp: str,
) -> dict:
    try:
        mobile = _normalize_mobile(mobile)
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
        }

    verified = await verify_otp(
        mobile=mobile,
        otp=otp,
    )

    if not verified:
        return {
            "success": False,
            "message": "Invalid or expired OTP.",
        }

    customer = await customers_collection.find_one(
        {"mobile": mobile}
    )

    if not customer:
        now = _now()

        customer_document = {
            "mobile": mobile,
            "name": None,
            "email": None,
            "created_at": now,
            "updated_at": now,
            "is_active": True,
        }

        insert_result = await customers_collection.insert_one(
            customer_document
        )

        customer_document["_id"] = insert_result.inserted_id
        customer = customer_document

    if customer.get("is_active", True) is False:
        return {
            "success": False,
            "message": "Customer account is inactive.",
        }

    customer_id = str(customer["_id"])

    tokens = create_auth_tokens(
        customer_id=customer_id,
        mobile=mobile,
    )

    await consume_verified_otp(
        mobile=mobile
    )

    return {
        "success": True,
        "message": "Login successful.",
        "mobile": mobile,
        "customer": {
            "id": customer_id,
            "mobile": customer.get("mobile"),
            "name": customer.get("name"),
            "email": customer.get("email"),
        },
        "access_token": tokens["access_token"],
        "refresh_token": tokens["refresh_token"],
        "token_type": tokens["token_type"],
        "expiresIn": tokens["expiresIn"],
    }

async def consume_verified_otp(
    mobile: str,
) -> bool:
    try:
        mobile = _normalize_mobile(mobile)
    except ValueError:
        return False

    result = await website_otps_collection.delete_one(
        {
            "mobile": mobile,
            "verified": True,
        }
    )

    return result.deleted_count > 0

async def clear_otp(
    mobile: str,
) -> None:
    try:
        mobile = _normalize_mobile(mobile)
    except ValueError:
        return

    await website_otps_collection.delete_one(
        {"mobile": mobile}
    )

async def get_otp_status(
    mobile: str,
) -> Optional[dict]:
    try:
        mobile = _normalize_mobile(mobile)
    except ValueError:
        return None

    record = await website_otps_collection.find_one(
        {"mobile": mobile}
    )

    if not record:
        return None

    return {
        "mobile": record.get("mobile"),
        "created_at": record.get("created_at"),
        "expiresAt": record.get("expiresAt"),
        "verified": record.get("verified", False),
        "verified_at": record.get("verified_at"),
        "provider": record.get("provider"),
        "provider_reference": record.get(
            "provider_reference"
        ),
    }

async def delete_expired_otps() -> int:
    now = _now()

    result = await website_otps_collection.delete_many(
        {
            "expiresAt": {
                "$lt": now,
            }
        }
    )

    return result.deleted_count