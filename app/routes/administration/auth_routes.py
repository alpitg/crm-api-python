import uuid
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status, Body
from datetime import datetime, timedelta, timezone
from app.db.mongo import db

from app.schemas.administration.auth_schemas import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest, TokenResponse
from app.schemas.administration.users.users import AppInitOut, ChangePasswordRequest, UpdateUserProfileRequest, UserIn, UserOut
from app.services.users_service import get_user_with_permissions
from app.utils.auth_utils import create_access_token, create_refresh_token, decode_token, authenticate, hash_password, verify_password
from core.sanitize import stringify_object_ids
from config import settings

router = APIRouter()  # ✅ no global dependency

users_collection = db["users"]
reset_tokens_collection = db["reset_tokens"]

# -------------------- Public Routes -------------------- #
#region
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    user: UserIn = await users_collection.find_one(
        {"$or": [{"userName": data.userName}, {"emailAddress": data.userName}]}
    )
    if not user or not verify_password(data.password, user.get("password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.get("isActive", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")

    token_data = {"sub": str(user["_id"]), "email": user["emailAddress"]}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(token_data)

    user_detail = await get_user_with_permissions(user["_id"])
    return {"accessToken": access_token, "refreshToken": refresh_token, "tokenType": "bearer", "user": user_detail}


@router.post("/refresh")
async def refresh_token(refresh_token: str):
    try:
        payload = decode_token(refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        token_data = {"sub": payload.get("sub"), "email": payload.get("emailAddress")}
        new_access_token = create_access_token(token_data)
        return {"accessToken": new_access_token, "tokenType": "bearer"}
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")


@router.post("/forgot-password")
async def forgot_password(data: ForgotPasswordRequest):
    user = await users_collection.find_one({"emailAddress": data.emailAddress})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    reset_token = str(uuid.uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"

    await reset_tokens_collection.insert_one({
        "userId": str(user["_id"]),
        "token": reset_token,
        "expiresAt": expires_at,
        "link": reset_link
    })

    # # Send email logic here
    # send_email(...)

    return {"message": "Password reset link sent to your email"}


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
