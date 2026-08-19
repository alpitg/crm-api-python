import random

from datetime import datetime, timedelta, timezone
from typing import Optional

from app.db.mongo import db
from app.services.auth.token_service import (
    create_auth_tokens,
)


# ============================================================
# CONFIG
# ============================================================

OTP_LENGTH = 6

OTP_EXPIRY_MINUTES = 5

OTP_RESEND_COOLDOWN_SECONDS = 30

MAX_VERIFY_ATTEMPTS = 5


# ============================================================
# COLLECTIONS
# ============================================================

website_otps_collection = db[
    "website_otps"
]

customers_collection = db[
    "customers"
]


# ============================================================
# HELPERS
# ============================================================


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _generate_otp() -> str:
    """
    Generate a 6-digit OTP.
    """

    return f"{random.randint(0, 999999):06d}"


def _normalize_mobile(
    mobile: str,
) -> str:
    """
    Normalize and validate mobile number.
    """

    if not mobile:
        raise ValueError(
            "Mobile number is required."
        )

    mobile = mobile.strip()

    mobile = "".join(
        character
        for character in mobile
        if character.isdigit()
    )

    if len(mobile) != 10:
        raise ValueError(
            "Please enter a valid 10-digit mobile number."
        )

    return mobile


def _normalize_datetime(
    value: datetime,
) -> datetime:
    """
    Ensure MongoDB datetime is timezone-aware.
    """

    if value.tzinfo is None:
        return value.replace(
            tzinfo=timezone.utc
        )

    return value


# ============================================================
# GENERATE + STORE OTP
# ============================================================


async def generate_and_store_otp(
    mobile: str,
) -> dict:
    """
    Generate and store a new OTP.

    Existing OTP for the same mobile number
    is replaced after cooldown.
    """

    mobile = _normalize_mobile(
        mobile
    )

    now = _now()

    existing_otp = await website_otps_collection.find_one(
        {
            "mobile": mobile,
        }
    )

    # --------------------------------------------------------
    # RESEND COOLDOWN
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # GENERATE OTP
    # --------------------------------------------------------

    otp = _generate_otp()

    expiresAt = (
        now
        + timedelta(
            minutes=OTP_EXPIRY_MINUTES
        )
    )

    # --------------------------------------------------------
    # STORE
    # --------------------------------------------------------

    await website_otps_collection.update_one(
        {
            "mobile": mobile,
        },
        {
            "$set": {
                "mobile": mobile,
                "otp": otp,
                "created_at": now,
                "expiresAt": expiresAt,
                "attempts": 0,
                "verified": False,
                "verified_at": None,
            }
        },
        upsert=True,
    )

    return {
        "mobile": mobile,
        "otp": otp,
        "expiresAt": expiresAt,
        "expiresIn": OTP_EXPIRY_MINUTES * 60,
        "retryAfter": OTP_RESEND_COOLDOWN_SECONDS,
    }


# ============================================================
# SEND LOGIN OTP
# ============================================================


async def send_login_otp(
    mobile: str,
) -> dict:
    """
    Generate and send login OTP.
    """

    try:

        result = await generate_and_store_otp(
            mobile=mobile
        )

    except ValueError as exc:

        return {
            "success": False,
            "message": str(exc),
        }

    # ========================================================
    # SMS PROVIDER
    # ========================================================
    #
    # IMPORTANT:
    #
    # Add your SMS provider here.
    #
    # Example:
    #
    # await sms_service.send_otp(
    #     mobile=result["mobile"],
    #     otp=result["otp"],
    # )
    #
    # ========================================================

    # DEVELOPMENT ONLY
    #
    # print(
    #     f"LOGIN OTP for {result['mobile']}: "
    #     f"{result['otp']}"
    # )

    return {
        "success": True,
        "message": "OTP sent successfully.",
        "mobile": result["mobile"],
        "expiresIn": result["expiresIn"],
        "retryAfter": result["retryAfter"],
    }


# ============================================================
# RESEND LOGIN OTP
# ============================================================


async def resend_login_otp(
    mobile: str,
) -> dict:
    """
    Resend login OTP.
    """

    try:

        result = await generate_and_store_otp(
            mobile=mobile
        )

    except ValueError as exc:

        return {
            "success": False,
            "message": str(exc),
        }

    # ========================================================
    # SMS PROVIDER
    # ========================================================

    # await sms_service.send_otp(
    #     mobile=result["mobile"],
    #     otp=result["otp"],
    # )

    return {
        "success": True,
        "message": "OTP resent successfully.",
        "mobile": result["mobile"],
        "expiresIn": result["expiresIn"],
        "retryAfter": result["retryAfter"],
    }


# ============================================================
# VERIFY OTP
# ============================================================


async def verify_otp(
    mobile: str,
    otp: str,
) -> bool:
    """
    Verify OTP.

    Returns:
        True  -> valid
        False -> invalid / expired / blocked
    """

    try:

        mobile = _normalize_mobile(
            mobile
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

    # --------------------------------------------------------
    # FIND OTP
    # --------------------------------------------------------

    otp_record = await website_otps_collection.find_one(
        {
            "mobile": mobile,
        }
    )

    if not otp_record:
        return False

    # --------------------------------------------------------
    # ALREADY VERIFIED
    # --------------------------------------------------------

    if otp_record.get("verified"):
        return False

    # --------------------------------------------------------
    # EXPIRY
    # --------------------------------------------------------

    now = _now()

    expiresAt = otp_record.get(
        "expiresAt"
    )

    if not expiresAt:

        await website_otps_collection.delete_one(
            {
                "_id": otp_record["_id"],
            }
        )

        return False

    expiresAt = _normalize_datetime(
        expiresAt
    )

    if now >= expiresAt:

        await website_otps_collection.delete_one(
            {
                "_id": otp_record["_id"],
            }
        )

        return False

    # --------------------------------------------------------
    # MAX ATTEMPTS
    # --------------------------------------------------------

    attempts = otp_record.get(
        "attempts",
        0,
    )

    if attempts >= MAX_VERIFY_ATTEMPTS:

        await website_otps_collection.delete_one(
            {
                "_id": otp_record["_id"],
            }
        )

        return False

    # --------------------------------------------------------
    # COMPARE
    # --------------------------------------------------------

    stored_otp = str(
        otp_record.get(
            "otp",
            ""
        )
    )

    if stored_otp != otp:

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

    # --------------------------------------------------------
    # VERIFIED
    # --------------------------------------------------------

    await website_otps_collection.update_one(
        {
            "_id": otp_record["_id"],
        },
        {
            "$set": {
                "verified": True,
                "verified_at": now,
            }
        },
    )

    return True


# ============================================================
# VERIFY LOGIN OTP
# ============================================================


async def verify_login_otp(
    mobile: str,
    otp: str,
) -> dict:
    """
    Complete website login flow.

    Steps:

    1. Verify OTP
    2. Find customer by mobile
    3. Create customer if not found
    4. Generate access token
    5. Generate refresh token
    6. Consume OTP
    7. Return customer + tokens
    """

    # --------------------------------------------------------
    # NORMALIZE MOBILE
    # --------------------------------------------------------

    try:

        mobile = _normalize_mobile(
            mobile
        )

    except ValueError as exc:

        return {
            "success": False,
            "message": str(exc),
        }

    # --------------------------------------------------------
    # VERIFY OTP
    # --------------------------------------------------------

    verified = await verify_otp(
        mobile=mobile,
        otp=otp,
    )

    if not verified:

        return {
            "success": False,
            "message": "Invalid or expired OTP.",
        }

    # --------------------------------------------------------
    # FIND CUSTOMER
    # --------------------------------------------------------

    customer = await customers_collection.find_one(
        {
            "mobile": mobile,
        }
    )

    # --------------------------------------------------------
    # CREATE CUSTOMER IF NOT FOUND
    # --------------------------------------------------------

    if not customer:

        now = _now()

        customer_document = {
            "mobile": mobile,
            "name": "user",
            "email": None,
            "description": None,
            "createdAt": now,
            "updatedAt": now,
            "isActive": True,
        }

        insert_result = (
            await customers_collection.insert_one(
                customer_document
            )
        )

        customer_document["_id"] = (
            insert_result.inserted_id
        )

        customer = customer_document

    # --------------------------------------------------------
    # CUSTOMER ACTIVE CHECK
    # --------------------------------------------------------

    if customer.get(
        "isActive",
        True,
    ) is False:

        return {
            "success": False,
            "message": "Customer account is inactive.",
        }

    # --------------------------------------------------------
    # CUSTOMER ID
    # --------------------------------------------------------

    customer_id = str(
        customer["_id"]
    )

    # --------------------------------------------------------
    # CREATE JWT TOKENS
    # --------------------------------------------------------

    tokens = create_auth_tokens(
        customer_id=customer_id,
        mobile=mobile,
    )

    # --------------------------------------------------------
    # CONSUME OTP
    # --------------------------------------------------------

    await consume_verified_otp(
        mobile=mobile
    )

    # --------------------------------------------------------
    # RESPONSE
    # --------------------------------------------------------

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


# ============================================================
# CONSUME VERIFIED OTP
# ============================================================


async def consume_verified_otp(
    mobile: str,
) -> bool:
    """
    Delete verified OTP.

    Prevents OTP reuse.
    """

    try:

        mobile = _normalize_mobile(
            mobile
        )

    except ValueError:

        return False

    result = await website_otps_collection.delete_one(
        {
            "mobile": mobile,
            "verified": True,
        }
    )

    return (
        result.deleted_count > 0
    )


# ============================================================
# CLEAR OTP
# ============================================================


async def clear_otp(
    mobile: str,
) -> None:
    """
    Delete OTP for mobile.
    """

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


# ============================================================
# OTP STATUS
# ============================================================


async def get_otp_status(
    mobile: str,
) -> Optional[dict]:
    """
    Get OTP status without exposing OTP.
    """

    try:

        mobile = _normalize_mobile(
            mobile
        )

    except ValueError:

        return None

    record = await website_otps_collection.find_one(
        {
            "mobile": mobile,
        },
        {
            "otp": 0,
        },
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
    }


# ============================================================
# CLEANUP EXPIRED OTPs
# ============================================================


async def delete_expired_otps() -> int:
    """
    Delete expired OTP records.

    Can be called from a scheduled background job.
    """

    now = _now()

    result = await website_otps_collection.delete_many(
        {
            "expiresAt": {
                "$lt": now,
            }
        }
    )

    return result.deleted_count