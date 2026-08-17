import hashlib
import secrets

from datetime import datetime, timedelta, timezone
from typing import Optional, Any

from app.db.mongo import db
from app.services.auth import sms_service
from app.services.auth.token_service import create_auth_tokens


OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 5
OTP_RESEND_COOLDOWN_SECONDS = 30
MAX_VERIFY_ATTEMPTS = 5
MAX_OTP_REQUESTS = 5
OTP_REQUEST_WINDOW_MINUTES = 15


website_otps_collection = db["website_otps"]
customers_collection = db["customers"]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _hash_otp(otp: str) -> str:
    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


def _normalize_mobile(mobile: str) -> str:
    if not mobile:
        raise ValueError(
            "Mobile number is required."
        )

    mobile = str(mobile).strip()

    mobile = "".join(
        character
        for character in mobile
        if character.isdigit()
    )

    if len(mobile) == 12 and mobile.startswith("91"):
        mobile = mobile[2:]

    if len(mobile) != 10:
        raise ValueError(
            "Please enter a valid 10-digit mobile number."
        )

    if not mobile.startswith(
        ("6", "7", "8", "9")
    ):
        raise ValueError(
            "Please enter a valid mobile number."
        )

    return mobile


def _normalize_datetime(
    value: datetime,
) -> datetime:
    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value


async def generate_and_store_otp(
    mobile: str,
) -> dict[str, Any]:

    mobile = _normalize_mobile(mobile)

    now = _now()

    existing_otp = (
        await website_otps_collection.find_one(
            {
                "mobile": mobile,
            }
        )
    )

    request_count = 0

    if existing_otp:

        last_sent_at = existing_otp.get(
            "created_at"
        )

        if last_sent_at:

            last_sent_at = _normalize_datetime(
                last_sent_at
            )

            elapsed = (
                now - last_sent_at
            ).total_seconds()

            if (
                elapsed
                < OTP_RESEND_COOLDOWN_SECONDS
            ):

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

        request_window_started_at = (
            existing_otp.get(
                "request_window_started_at"
            )
        )

        if request_window_started_at:

            request_window_started_at = (
                _normalize_datetime(
                    request_window_started_at
                )
            )

            elapsed_window = (
                now
                - request_window_started_at
            ).total_seconds()

            if (
                elapsed_window
                < OTP_REQUEST_WINDOW_MINUTES * 60
            ):

                request_count = int(
                    existing_otp.get(
                        "request_count",
                        0,
                    )
                )

                if (
                    request_count
                    >= MAX_OTP_REQUESTS
                ):

                    raise ValueError(
                        "Too many OTP requests. "
                        "Please try again later."
                    )

            else:

                request_count = 0

    otp = _generate_otp()

    otp_hash = _hash_otp(otp)

    expires_at = (
        now
        + timedelta(
            minutes=OTP_EXPIRY_MINUTES
        )
    )

    if (
        not existing_otp
        or not existing_otp.get(
            "request_window_started_at"
        )
    ):

        request_window_started_at = now

        request_count = 0

    else:

        request_window_started_at = (
            _normalize_datetime(
                existing_otp[
                    "request_window_started_at"
                ]
            )
        )

        elapsed_window = (
            now
            - request_window_started_at
        ).total_seconds()

        if (
            elapsed_window
            >= OTP_REQUEST_WINDOW_MINUTES * 60
        ):

            request_window_started_at = now

            request_count = 0

    request_count += 1

    await website_otps_collection.update_one(
        {
            "mobile": mobile,
        },
        {
            "$set": {
                "mobile": mobile,
                "otp_hash": otp_hash,
                "created_at": now,
                "expiresAt": expires_at,
                "attempts": 0,
                "verified": False,
                "verified_at": None,
                "request_count": request_count,
                "request_window_started_at": (
                    request_window_started_at
                ),
            }
        },
        upsert=True,
    )

    return {
        "mobile": mobile,
        "otp": otp,
        "expiresAt": expires_at,
        "expiresIn": OTP_EXPIRY_MINUTES * 60,
        "retryAfter": OTP_RESEND_COOLDOWN_SECONDS,
    }


async def send_login_otp(
    mobile: str,
) -> dict[str, Any]:

    try:

        result = await generate_and_store_otp(
            mobile=mobile
        )

    except ValueError as exc:

        return {
            "success": False,
            "message": str(exc),
        }

    try:

        await sms_service.send_otp(
            mobile=result["mobile"],
            otp=result["otp"],
        )

    except Exception as exc:

        await clear_otp(
            result["mobile"]
        )

        raise RuntimeError(
            "Unable to send OTP."
        ) from exc

    return {
        "success": True,
        "message": "OTP sent successfully.",
        "mobile": result["mobile"],
        "expiresIn": result["expiresIn"],
        "retryAfter": result["retryAfter"],
    }


async def resend_login_otp(
    mobile: str,
) -> dict[str, Any]:

    return await send_login_otp(
        mobile=mobile
    )


async def verify_otp(
    mobile: str,
    otp: str,
) -> bool:

    try:

        mobile = _normalize_mobile(
            mobile
        )

    except ValueError:

        return False

    if not otp:

        return False

    otp = str(otp).strip()

    if (
        len(otp) != OTP_LENGTH
        or not otp.isdigit()
    ):

        return False

    otp_record = (
        await website_otps_collection.find_one(
            {
                "mobile": mobile,
            }
        )
    )

    if not otp_record:

        return False

    if otp_record.get("verified"):

        return False

    expires_at = otp_record.get(
        "expiresAt"
    )

    if not expires_at:

        await website_otps_collection.delete_one(
            {
                "_id": otp_record["_id"],
            }
        )

        return False

    expires_at = _normalize_datetime(
        expires_at
    )

    now = _now()

    if now >= expires_at:

        await website_otps_collection.delete_one(
            {
                "_id": otp_record["_id"],
            }
        )

        return False

    attempts = int(
        otp_record.get(
            "attempts",
            0,
        )
    )

    if attempts >= MAX_VERIFY_ATTEMPTS:

        await website_otps_collection.delete_one(
            {
                "_id": otp_record["_id"],
            }
        )

        return False

    submitted_hash = _hash_otp(
        otp
    )

    stored_hash = str(
        otp_record.get(
            "otp_hash",
            "",
        )
    )

    if not secrets.compare_digest(
        stored_hash,
        submitted_hash,
    ):

        await website_otps_collection.update_one(
            {
                "_id": otp_record["_id"],
            },
            {
                "$inc": {
                    "attempts": 1,
                }
            },
        )

        return False

    result = (
        await website_otps_collection.update_one(
            {
                "_id": otp_record["_id"],
                "verified": False,
                "attempts": {
                    "$lt": MAX_VERIFY_ATTEMPTS,
                },
            },
            {
                "$set": {
                    "verified": True,
                    "verified_at": now,
                }
            },
        )
    )

    return result.modified_count > 0


async def verify_login_otp(
    mobile: str,
    otp: str,
) -> dict[str, Any]:

    try:

        mobile = _normalize_mobile(
            mobile
        )

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

    customer = (
        await customers_collection.find_one(
            {
                "mobile": mobile,
            }
        )
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

        try:

            insert_result = (
                await customers_collection.insert_one(
                    customer_document
                )
            )

            customer_document["_id"] = (
                insert_result.inserted_id
            )

            customer = customer_document

        except Exception:

            customer = (
                await customers_collection.find_one(
                    {
                        "mobile": mobile,
                    }
                )
            )

            if not customer:

                raise

    if (
        customer.get(
            "is_active",
            True,
        )
        is False
    ):

        return {
            "success": False,
            "message": "Customer account is inactive.",
        }

    customer_id = str(
        customer["_id"]
    )

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
            "mobile": customer.get(
                "mobile"
            ),
            "name": customer.get(
                "name"
            ),
            "email": customer.get(
                "email"
            ),
        },
        "access_token": tokens[
            "access_token"
        ],
        "refresh_token": tokens[
            "refresh_token"
        ],
        "token_type": tokens[
            "token_type"
        ],
        "expiresIn": tokens[
            "expiresIn"
        ],
    }


async def consume_verified_otp(
    mobile: str,
) -> bool:

    try:

        mobile = _normalize_mobile(
            mobile
        )

    except ValueError:

        return False

    result = (
        await website_otps_collection.delete_one(
            {
                "mobile": mobile,
                "verified": True,
            }
        )
    )

    return result.deleted_count > 0


async def clear_otp(
    mobile: str,
) -> None:

    try:

        mobile = _normalize_mobile(
            mobile
        )

    except ValueError:

        return

    await website_otps_collection.delete_one(
        {
            "mobile": mobile,
        }
    )


async def get_otp_status(
    mobile: str,
) -> Optional[dict[str, Any]]:

    try:

        mobile = _normalize_mobile(
            mobile
        )

    except ValueError:

        return None

    record = (
        await website_otps_collection.find_one(
            {
                "mobile": mobile,
            },
            {
                "otp_hash": 0,
            },
        )
    )

    if not record:

        return None

    return {
        "mobile": record.get(
            "mobile"
        ),
        "created_at": record.get(
            "created_at"
        ),
        "expiresAt": record.get(
            "expiresAt"
        ),
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
        "retryAfter": (
            OTP_RESEND_COOLDOWN_SECONDS
        ),
    }


async def delete_expired_otps() -> int:

    now = _now()

    result = (
        await website_otps_collection.delete_many(
            {
                "expiresAt": {
                    "$lt": now,
                }
            }
        )
    )

    return result.deleted_count