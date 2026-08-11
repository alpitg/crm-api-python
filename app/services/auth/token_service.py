from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import settings


# ============================================================
# CONFIG
# ============================================================

ALGORITHM = "HS256"

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30


# ============================================================
# SECURITY
# ============================================================

security = HTTPBearer(
    auto_error=False,
)


# ============================================================
# HELPERS
# ============================================================


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _create_token(
    payload: dict,
    expires_delta: timedelta,
) -> str:
    """
    Create JWT token.
    """

    now = _now()

    token_payload = payload.copy()

    token_payload.update(
        {
            "iat": now,
            "exp": now + expires_delta,
        }
    )

    return jwt.encode(
        token_payload,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


# ============================================================
# ACCESS TOKEN
# ============================================================


def create_access_token(
    customer_id: str,
    mobile: Optional[str] = None,
) -> str:
    """
    Create short-lived access token.
    """

    payload = {
        "sub": str(customer_id),
        "type": "access",
    }

    if mobile:
        payload["mobile"] = mobile

    return _create_token(
        payload=payload,
        expires_delta=timedelta(
            minutes=ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    )


# ============================================================
# REFRESH TOKEN
# ============================================================


def create_refresh_token(
    customer_id: str,
) -> str:
    """
    Create long-lived refresh token.
    """

    payload = {
        "sub": str(customer_id),
        "type": "refresh",
    }

    return _create_token(
        payload=payload,
        expires_delta=timedelta(
            days=REFRESH_TOKEN_EXPIRE_DAYS
        ),
    )


# ============================================================
# CREATE AUTH TOKENS
# ============================================================


def create_auth_tokens(
    customer_id: str,
    mobile: Optional[str] = None,
) -> dict:
    """
    Create access + refresh tokens.
    """

    access_token = create_access_token(
        customer_id=customer_id,
        mobile=mobile,
    )

    refresh_token = create_refresh_token(
        customer_id=customer_id,
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ============================================================
# DECODE TOKEN
# ============================================================


def decode_token(
    token: str,
) -> Optional[dict]:
    """
    Decode and validate JWT.

    Returns None if token is invalid or expired.
    """

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        return payload

    except JWTError:
        return None


# ============================================================
# VERIFY ACCESS TOKEN
# ============================================================


def verify_access_token(
    token: str,
) -> Optional[dict]:
    """
    Validate an access token.
    """

    payload = decode_token(
        token
    )

    if not payload:
        return None

    if payload.get("type") != "access":
        return None

    if not payload.get("sub"):
        return None

    return payload


# ============================================================
# VERIFY REFRESH TOKEN
# ============================================================


def verify_refresh_token(
    token: str,
) -> Optional[dict]:
    """
    Validate a refresh token.
    """

    payload = decode_token(
        token
    )

    if not payload:
        return None

    if payload.get("type") != "refresh":
        return None

    if not payload.get("sub"):
        return None

    return payload


# ============================================================
# CUSTOMER ID FROM TOKEN
# ============================================================


def get_customer_id_from_token(
    token: str,
) -> Optional[str]:
    """
    Extract customer ID from access token.
    """

    payload = verify_access_token(
        token
    )

    if not payload:
        return None

    customer_id = payload.get(
        "sub"
    )

    if not customer_id:
        return None

    return str(customer_id)


# ============================================================
# REFRESH ACCESS TOKEN
# ============================================================


def refresh_access_token(
    refresh_token: str,
) -> Optional[dict]:
    """
    Generate a new access token
    using a valid refresh token.
    """

    payload = verify_refresh_token(
        refresh_token
    )

    if not payload:
        return None

    customer_id = payload.get(
        "sub"
    )

    if not customer_id:
        return None

    access_token = create_access_token(
        customer_id=str(customer_id)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expiresIn": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


# ============================================================
# FASTAPI CURRENT CUSTOMER ID
# ============================================================


async def get_current_customer_id(
    credentials: HTTPAuthorizationCredentials = None,
) -> str:
    """
    FastAPI dependency.

    Reads:

        Authorization: Bearer <access_token>

    and returns customer ID.
    """

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    token = credentials.credentials

    customer_id = get_customer_id_from_token(
        token
    )

    if not customer_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={
                "WWW-Authenticate": "Bearer"
            },
        )

    return customer_id


# ============================================================
# CURRENT CUSTOMER
# ============================================================


async def get_current_customer(
    credentials: HTTPAuthorizationCredentials = None,
):
    """
    FastAPI dependency.

    Returns the authenticated customer document.
    """

    from app.db.mongo import db

    customer_id = await get_current_customer_id(
        credentials=credentials
    )

    from bson import ObjectId

    try:
        object_id = ObjectId(
            customer_id
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid customer ID.",
        )

    customer = await db[
        "customers"
    ].find_one(
        {
            "_id": object_id,
        }
    )

    if not customer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Customer not found.",
        )

    return customer


# ============================================================
# LOGOUT
# ============================================================


async def logout_customer(
    token: str,
) -> bool:
    """
    Logout helper.

    JWT access tokens are stateless, so simply deleting a
    token on the server is not possible.

    The client should remove its access/refresh tokens.

    This function is kept as a common auth-service interface
    so a token blacklist can be added later if required.
    """

    payload = verify_access_token(
        token
    )

    if not payload:
        return False

    return True