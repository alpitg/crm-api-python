from fastapi import APIRouter, HTTPException
from app.schemas.user import UserCreate, UserResponse
from app.models import user as user_model

router = APIRouter()

@router.post("/users", response_model=UserResponse)
async def create_user(user: UserCreate):
    existing = await user_model.get_user_by_email(user.email)
    if existing:
        raise HTTPException(status_code=400, detail="User already exists")
    new_user = await user_model.create_user(user.dict())
    return new_user
