from pydantic import BaseModel, EmailStr
from typing import Optional

class UserCreate(BaseModel):
    name: str
    email: EmailStr

class UserInDB(UserCreate):
    id: str

class UserResponse(UserCreate):
    id: str
