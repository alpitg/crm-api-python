from bson import ObjectId
from fastapi import APIRouter, HTTPException, status
from datetime import timedelta
from app.db.mongo import db

from app.schemas.administration.auth_schemas import LoginRequest, TokenResponse
from app.schemas.administration.users.users import ChangePasswordRequest, UpdateUserProfileRequest, UserIn, UserOut
from app.services.users_service import get_user_with_permissions
from app.utils.auth_utils import create_access_token, hash_password, verify_password
from core.sanitize import stringify_object_ids

router = APIRouter()
users_collection = db["users"]


def user_helper(user) -> dict:
    user["id"] = str(user["_id"])
    return user


# ✅ Login
@router.post("/login", response_model=TokenResponse)
async def login(data: LoginRequest):
    user: UserIn = await users_collection.find_one({"userName": data.userName})

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(data.password, user.get("password", "")):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.get("isActive", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is not active")

    token_data = {
        "sub": str(user["_id"]),
        "userName": user["userName"],
    }

    access_token = create_access_token(data=token_data, expires_delta=timedelta(minutes=30))
    user_detail = await get_user_with_permissions(user["_id"])

    return {"accessToken": access_token, "tokenType": "bearer", "user": user_detail}


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