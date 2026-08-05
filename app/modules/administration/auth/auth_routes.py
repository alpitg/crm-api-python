import uuid
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Response, status, Body, Cookie
from datetime import datetime, timedelta, timezone
from app.db.mongo import db

from app.modules.administration.auth.schemas.auth_schemas import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest, TokenResponse
from app.modules.administration.user.schemas.users import UserIn, UserOut
from app.modules.administration.user.schemas.users import AppInitOut, ChangePasswordRequest, UpdateUserProfileRequest
from app.modules.administration.user.services.user_service import get_user_with_permissions
from app.services.mail_service import send_email
from app.utils.auth_utils import create_access_token, create_refresh_token, decode_token, authenticate, hash_password, verify_password
from core.sanitize import stringify_object_ids
from config import settings

router = APIRouter()  # ✅ no global dependency

users_collection = db["users"]
reset_tokens_collection = db["reset_tokens"]

# -------------------- Public Routes -------------------- #
#region
@router.post("/login")
async def login(data: LoginRequest, response: Response):
    user: UserIn = await users_collection.find_one(
        {"$or": [{"userName": data.userName}, {"emailAddress": data.userName}]}
    )

    if not user or not verify_password(data.password, user.get("password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.get("isActive", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")

    token_data = {"sub": str(user["_id"]), "email": user["emailAddress"]}

    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )

    return {"accessToken": access_token, "tokenType": "bearer"}


@router.post("/refresh")
async def refresh_token(response: Response, refresh_token: str | None = Cookie(default=None)):
    if not refresh_token or refresh_token.strip() == "":
        response.delete_cookie(key="refresh_token", path="/")
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        payload = decode_token(refresh_token)
    except Exception as exc:
        response.delete_cookie(key="refresh_token", path="/")
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token") from exc

    if payload.get("type") != "refresh":
        response.delete_cookie(key="refresh_token", path="/")
        raise HTTPException(status_code=401, detail="Invalid token type")

    token_data = {"sub": payload.get("sub"), "email": payload.get("email")}
    new_access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)

    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=60 * 60 * 24 * 30,
        path="/",
    )

    return {"accessToken": new_access_token, "tokenType": "bearer"}

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(
        key="refresh_token",
        path="/",
        httponly=True,
        samesite="lax",
        secure=False,
    )
    return {"message": "Logged out"}

@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    user = await users_collection.find_one({"emailAddress": data.emailAddress})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    reset_link = f"{settings.FRONTEND_URL}/crm/reset-password?token={reset_token}"

    await reset_tokens_collection.insert_one({
        "userId": str(user["_id"]),
        "token": reset_token,
        "expiresAt": expires_at,
        "link": reset_link
    })

    # # Send email logic here
    email_body = (
        "Hello,\n\n"
        "**Code**: " + reset_token + "\n\n"
        "We received a request to reset your password for your CRM account.\n"
        f"Use the link below to reset it securely within the next hour:\n\n"
        f"{reset_link}\n\n"
        "If you did not request this change, you can ignore this email and your password will remain unchanged.\n\n"
        "Thank you,\n"
        "CRM Team, Artisan Studios"
    )

    send_email(
        subject="Password Reset Request",
        recipients=user["emailAddress"],
        body=email_body
    )

    return {"message": "Password reset link sent to your email."}


@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    token_doc = await reset_tokens_collection.find_one({"token": data.code})
    if not token_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    expires_at = token_doc["expiresAt"]
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    hashed_pw = hash_password(data.newPassword)
    await users_collection.update_one({"_id": ObjectId(token_doc["userId"])}, {"$set": {"password": hashed_pw}})
    await reset_tokens_collection.delete_one({"_id": token_doc["_id"]})

    return {"message": "Password reset successful"}
#endregion


# -------------------- Protected Routes -------------------- #

@router.put("/users/{id}/change-password", status_code=status.HTTP_200_OK)
async def change_password(id: str, request: ChangePasswordRequest, user=Depends(authenticate)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")
    db_user = await users_collection.find_one({"_id": ObjectId(id)})
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not verify_password(request.currentPassword, db_user.get("password", "")):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    hashed_password = hash_password(request.newPassword)
    await users_collection.update_one({"_id": ObjectId(id)}, {"$set": {"password": hashed_password}})

    return {"message": "Password updated successfully"}


@router.get("/users/me/app-init", response_model=AppInitOut)
async def get_all(token_detail: dict = Depends(authenticate)):
    user_id: str = token_detail.get("sub", "")
    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_detail = await get_user_with_permissions(user["_id"])
    return {"user": user_detail}


@router.get("/users/{id}/current-user-profile", response_model=UserOut)
async def authenticate_profile(id: str, user=Depends(authenticate)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    user_doc = await users_collection.find_one({"_id": ObjectId(id), "isDeleted": {"$ne": True}})
    if not user_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user_doc = stringify_object_ids(user_doc)
    return UserOut(**user_doc)


@router.put("/users/{id}/current-user-profile", status_code=status.HTTP_200_OK)
async def update_current_user_profile(id: str, request: UpdateUserProfileRequest, user=Depends(authenticate)):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    db_user = await users_collection.find_one({"_id": ObjectId(id)})
    if not db_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = {}
    if request.name is not None:
        update_data["name"] = request.name
    if request.surname is not None:
        update_data["surname"] = request.surname
    if request.emailAddress is not None:
        update_data["emailAddress"] = request.emailAddress
    if request.userName is not None:
        update_data["userName"] = request.userName

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No valid fields to update")

    await users_collection.update_one({"_id": ObjectId(id)}, {"$set": update_data})
    return {"message": "Details updated successfully"}
