from fastapi import APIRouter, HTTPException, status
from datetime import timedelta
from app.db.mongo import db

from app.schemas.administration.auth_schemas import LoginRequest, TokenResponse
from app.schemas.administration.users.users import UserIn
from app.utils.auth_utils import create_access_token, verify_password

router = APIRouter()
users_collection = db["users"]


def user_helper(user) -> dict:
    user["id"] = str(user["_id"])
    return user


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
    return {"accessToken": access_token, "tokenType": "bearer"}
