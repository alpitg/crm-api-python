import random
from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db.mongo import db
from app.services import mail_service
from app.services.auth.token_service import create_auth_tokens

OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 30
MAX_VERIFY_ATTEMPTS = 5

website_otps_collection = db["website_otps"]
customers_collection = db["customers"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def _normalize_login_type(login_type: Optional[str]) -> str:
    login_type = (login_type or "email").strip().lower()

    if login_type not in {"email", "mobile"}:
        raise ValueError("Invalid login type.")

    return login_type


def _normalize_mobile(mobile: str) -> str:
    if not mobile:
        raise ValueError("Mobile number is required.")

    mobile = mobile.strip()
    mobile = "".join(
        character for character in mobile if character.isdigit()
    )

    if len(mobile) != 10:
        raise ValueError(
            "Please enter a valid 10-digit mobile number."
        )

    return mobile


def _normalize_email(email: str) -> str:
    if not email:
        raise ValueError("Email address is required.")

    email = email.strip().lower()

    if "@" not in email or "." not in email.split("@")[-1]:
        raise ValueError("Please enter a valid email address.")

    return email


def _normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value


def _normalize_identifier(
    identifier: str,
    login_type: str = "email",
) -> str:
    login_type = _normalize_login_type(login_type)

    if login_type == "mobile":
        return _normalize_mobile(identifier)

    return _normalize_email(identifier)


def _otp_query(
    identifier: str,
    login_type: str = "email",
) -> dict:
    login_type = _normalize_login_type(login_type)
    identifier = _normalize_identifier(
        identifier,
        login_type,
    )

    return {
        "identifier": identifier,
        "login_type": login_type,
    }


async def generate_and_store_otp(
    identifier: str,
    login_type: str = "email",
) -> dict:
    login_type = _normalize_login_type(login_type)
    identifier = _normalize_identifier(
        identifier,
        login_type,
    )

    now = _now()

    query = _otp_query(
        identifier=identifier,
        login_type=login_type,
    )

    existing_otp = await website_otps_collection.find_one(query)

    if existing_otp:
        last_sent_at = existing_otp.get("created_at")

        if last_sent_at:
            last_sent_at = _normalize_datetime(last_sent_at)

            elapsed = (
                now - last_sent_at
            ).total_seconds()

            if elapsed < OTP_RESEND_COOLDOWN_SECONDS:
                remaining = max(
                    1,
                    int(
                        OTP_RESEND_COOLDOWN_SECONDS
                        - elapsed
                    ),
                )

                raise ValueError(
                    f"Please wait {remaining} seconds "
                    "before requesting another OTP."
                )

    otp = _generate_otp()

    expires_at = now + timedelta(
        minutes=OTP_EXPIRY_MINUTES
    )

    await website_otps_collection.update_one(
        query,
        {
            "$set": {
                "identifier": identifier,
                "login_type": login_type,
                "otp": otp,
                "created_at": now,
                "expiresAt": expires_at,
                "attempts": 0,
                "verified": False,
                "verified_at": None,
            }
        },
        upsert=True,
    )

    return {
        "identifier": identifier,
        "login_type": login_type,
        "otp": otp,
        "expiresAt": expires_at,
        "expiresIn": OTP_EXPIRY_MINUTES * 60,
        "retryAfter": OTP_RESEND_COOLDOWN_SECONDS,
    }


async def send_login_otp(
    login_type: str = "email",
    email: Optional[str] = None,
    mobile: Optional[str] = None,
) -> dict:
    login_type = _normalize_login_type(login_type)

    identifier = ""

    if login_type == "email":
        identifier = email or identifier
    else:
        identifier = mobile or identifier

    try:
        result = await generate_and_store_otp(
            identifier=identifier,
            login_type=login_type,
        )
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
        }

    if login_type == "email":
        try:
            await mail_service.send_otp(
                email=result["identifier"],
                otp=result["otp"],
            )
        except Exception as exc:
            await clear_otp(
                identifier=result["identifier"],
                login_type=login_type,
            )

            return {
                "success": False,
                "message": "Unable to send OTP email.",
                "error": str(exc),
            }

    else:
        # Add SMS provider here.
        #
        # await sms_service.send_otp(
        #     mobile=result["identifier"],
        #     otp=result["otp"],
        # )
        pass

    return {
        "success": True,
        "message": "OTP sent successfully.",
        "identifier": result["identifier"],
        "loginType": result["login_type"],
        "expiresIn": result["expiresIn"],
        "retryAfter": result["retryAfter"],
    }


async def resend_login_otp(
    login_type: str = "email",
    email: Optional[str] = None,
    mobile: Optional[str] = None,
) -> dict:
    login_type = _normalize_login_type(login_type)

    identifier = ""

    if login_type == "email":
        identifier = email or identifier
    else:
        identifier = mobile or identifier

    try:
        result = await generate_and_store_otp(
            identifier=identifier,
            login_type=login_type,
        )
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
        }

    if login_type == "email":
        try:
            await mail_service.send_otp(
                email=result["identifier"],
                otp=result["otp"],
            )
        except Exception as exc:
            await clear_otp(
                identifier=result["identifier"],
                login_type=login_type,
            )

            return {
                "success": False,
                "message": "Unable to send OTP email.",
                "error": str(exc),
            }

    else:
        # Add SMS provider here.
        #
        # await sms_service.send_otp(
        #     mobile=result["identifier"],
        #     otp=result["otp"],
        # )
        pass

    return {
        "success": True,
        "message": "OTP resent successfully.",
        "identifier": result["identifier"],
        "loginType": result["login_type"],
        "expiresIn": result["expiresIn"],
        "retryAfter": result["retryAfter"],
    }


async def verify_otp(
    identifier: str,
    otp: str,
    login_type: str = "email",
) -> bool:
    try:
        login_type = _normalize_login_type(login_type)
        identifier = _normalize_identifier(
            identifier,
            login_type,
        )
    except ValueError:
        return False

    if not otp:
        return False

    otp = otp.strip()

    if len(otp) != OTP_LENGTH:
        return False

    if not otp.isdigit():
        return False

    query = _otp_query(
        identifier=identifier,
        login_type=login_type,
    )

    otp_record = await website_otps_collection.find_one(query)

    if not otp_record:
        return False

    if otp_record.get("verified"):
        return False

    now = _now()

    expires_at = otp_record.get("expiresAt")

    if not expires_at:
        await website_otps_collection.delete_one(
            {"_id": otp_record["_id"]}
        )
        return False

    expires_at = _normalize_datetime(expires_at)

    if now >= expires_at:
        await website_otps_collection.delete_one(
            {"_id": otp_record["_id"]}
        )
        return False

    attempts = otp_record.get("attempts", 0)

    if attempts >= MAX_VERIFY_ATTEMPTS:
        await website_otps_collection.delete_one(
            {"_id": otp_record["_id"]}
        )
        return False

    stored_otp = str(
        otp_record.get("otp", "")
    )

    if stored_otp != otp:
        await website_otps_collection.update_one(
            {"_id": otp_record["_id"]},
            {
                "$inc": {
                    "attempts": 1,
                }
            },
        )
        return False

    await website_otps_collection.update_one(
        {"_id": otp_record["_id"]},
        {
            "$set": {
                "verified": True,
                "verified_at": now,
            }
        },
    )

    return True


async def verify_login_otp(
    otp: str,
    login_type: str = "email",
    email: Optional[str] = None,
    mobile: Optional[str] = None,
) -> dict:
    login_type = _normalize_login_type(login_type)

    identifier = ""

    if login_type == "email":
        identifier = email or identifier
    else:
        identifier = mobile or identifier

    try:
        identifier = _normalize_identifier(
            identifier,
            login_type,
        )
    except ValueError as exc:
        return {
            "success": False,
            "message": str(exc),
        }

    verified = await verify_otp(
        identifier=identifier,
        otp=otp,
        login_type=login_type,
    )

    if not verified:
        return {
            "success": False,
            "message": "Invalid or expired OTP.",
        }

    if login_type == "email":
        customer = await customers_collection.find_one(
            {
                "email": identifier,
            }
        )
    else:
        customer = await customers_collection.find_one(
            {
                "mobile": identifier,
            }
        )

    if not customer:
        now = _now()

        customer_document = {
            "mobile": (
                identifier
                if login_type == "mobile"
                else None
            ),
            "name": "user",
            "email": (
                identifier
                if login_type == "email"
                else None
            ),
            "description": None,
            "createdAt": now,
            "updatedAt": now,
            "isActive": True,
        }

        insert_result = await customers_collection.insert_one(
            customer_document
        )

        customer_document["_id"] = (
            insert_result.inserted_id
        )

        customer = customer_document

    if customer.get("isActive", True) is False:
        return {
            "success": False,
            "message": "Customer account is inactive.",
        }

    customer_id = str(customer["_id"])

    tokens = create_auth_tokens(
        customer_id=customer_id,
        mobile=customer.get("mobile"),
    )

    await consume_verified_otp(
        identifier=identifier,
        login_type=login_type,
    )

    return {
        "success": True,
        "message": "Login successful.",
        "identifier": identifier,
        "loginType": login_type,
        "mobile": customer.get("mobile"),
        "email": customer.get("email"),
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
    identifier: str,
    login_type: str = "email",
) -> bool:
    try:
        login_type = _normalize_login_type(login_type)
        identifier = _normalize_identifier(
            identifier,
            login_type,
        )
    except ValueError:
        return False

    result = await website_otps_collection.delete_one(
        {
            "identifier": identifier,
            "login_type": login_type,
            "verified": True,
        }
    )

    return result.deleted_count > 0


async def clear_otp(
    identifier: str,
    login_type: str = "email",
) -> None:
    try:
        login_type = _normalize_login_type(login_type)
        identifier = _normalize_identifier(
            identifier,
            login_type,
        )
    except ValueError:
        return

    await website_otps_collection.delete_one(
        _otp_query(
            identifier=identifier,
            login_type=login_type,
        )
    )


async def get_otp_status(
    identifier: str,
    login_type: str = "email",
) -> Optional[dict]:
    try:
        login_type = _normalize_login_type(login_type)
        identifier = _normalize_identifier(
            identifier,
            login_type,
        )
    except ValueError:
        return None

    record = await website_otps_collection.find_one(
        _otp_query(
            identifier=identifier,
            login_type=login_type,
        ),
        {
            "otp": 0,
        },
    )

    if not record:
        return None

    return {
        "identifier": record.get("identifier"),
        "loginType": record.get(
            "login_type",
            "email",
        ),
        "created_at": record.get("created_at"),
        "expiresAt": record.get("expiresAt"),
        "attempts": record.get(
            "attempts",
            0,
        ),
        "verified": record.get(
            "verified",
            False,
        ),
        "verified_at": record.get(
            "verified_at"
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