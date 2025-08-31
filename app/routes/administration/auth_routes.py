import uuid
from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status
from datetime import datetime, timedelta, timezone
from app.db.mongo import db

from app.schemas.administration.auth_schemas import ForgotPasswordRequest, LoginRequest, ResetPasswordRequest, TokenResponse
from app.schemas.administration.users.users import AppInitOut, ChangePasswordRequest, UpdateUserProfileRequest, UserIn, UserOut
from app.services.users_service import get_user_with_permissions
from app.utils.auth_utils import create_access_token, create_refresh_token, decode_token, get_current_user, hash_password, verify_password
from core.sanitize import stringify_object_ids
from config import settings

router = APIRouter()
users_collection = db["users"]
reset_tokens_collection = db["reset_tokens"]  # collection for reset tokens

# ✅ Login
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    user: UserIn = await users_collection.find_one(
        {
            "$or": [
                {"userName": data.userName},
                {"emailAddress": data.userName},  # allow login with email too
            ]
        }
    )

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(data.password, user.get("password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.get("isActive", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")

    token_data = {"sub": str(user["_id"]), "email": user["emailAddress"]}
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(token_data)

    user_detail = await get_user_with_permissions(user["_id"])

    return {"accessToken": access_token, "refreshToken": refresh_token, "tokenType": "bearer", "user": user_detail}

# ✅ Refresh token
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


# ✅ Forgot password
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


    # # ✅ Send email
    # send_email(
    #     subject="Password Reset Request",
    #     recipients=[data.emailAddress],
    #     body=f"""
    #     <p>Hello {data.emailAddress},</p>
    #     <p>You requested a password reset. Click the link below to reset your password:</p>
    #     <p><a href="{reset_link}">Reset Password</a></p>
    #     <p>This link will expire in 1 hour.</p>
    #     """
    # )

    return {"message": "Password reset link sent to your email"}


# ✅ reset passowrd
@router.post("/reset-password")
async def reset_password(data: ResetPasswordRequest):
    token_doc = await reset_tokens_collection.find_one({"token": data.code})

    if not token_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired token")

    # Ensure expiresAt is timezone-aware (assuming it's UTC in DB)
    expires_at = token_doc["expiresAt"]
    if expires_at.tzinfo is None:  # naive datetime
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Token expired")

    # Update password
    hashed_pw = hash_password(data.newPassword)
    await users_collection.update_one(
        {"_id": ObjectId(token_doc["userId"])},
        {"$set": {"password": hashed_pw}}
    )

    # Delete used token
    await reset_tokens_collection.delete_one({"_id": token_doc["_id"]})

    return {"message": "Password reset successful"}


# ✅ Update password
@router.put("/users/{id}/change-password", status_code=status.HTTP_200_OK)
async def change_password(id: str, request: ChangePasswordRequest):
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    user = await users_collection.find_one({"_id": ObjectId(id)})

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # check old password
    if not verify_password(request.currentPassword, user.get("password", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # update with new password hash
    hashed_password = hash_password(request.newPassword)
    await users_collection.update_one(
        {"_id": ObjectId(id)},
        {"$set": {"password": hashed_password}}
    )

    return {"message": "Password updated successfully"}

#region User Profile

# ✅ get all data of user for app initialization
@router.get("/users/me/app-init", response_model=AppInitOut)
async def get_all(token_detail: dict = Depends(get_current_user)):

    user_id: str = token_detail.get("sub", "")

    if not ObjectId.is_valid(user_id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    user = await users_collection.find_one({"_id": ObjectId(user_id)})

    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # user detail
    user_detail = await get_user_with_permissions(user["_id"])

    return {"user": user_detail}


# ✅ Get current user profile
@router.get("/users/{id}/current-user-profile", response_model=UserOut)
async def get_current_user_profile(id: str):
    """
    Fetch current user profile for editing.
    """
    if not id or not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user ID"
        )

    user_doc = await users_collection.find_one({"_id": ObjectId(id), "isDeleted": {"$ne": True}})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Convert ObjectId fields to string
    user_doc = stringify_object_ids(user_doc)

    return UserOut(**user_doc)

# ✅ Update current user profile
@router.put("/users/{id}/current-user-profile", status_code=status.HTTP_200_OK)
async def update_current_user_profile(id: str, request: UpdateUserProfileRequest):
    # Validate ObjectId
    if not ObjectId.is_valid(id):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid user ID")

    # Fetch user
    user = await users_collection.find_one({"_id": ObjectId(id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prepare update data
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

    # Update in DB
    await users_collection.update_one({"_id": ObjectId(id)}, {"$set": update_data})

    return {"message": "Details updated successfully"}

#endregion