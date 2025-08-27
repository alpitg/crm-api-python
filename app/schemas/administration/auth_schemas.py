from typing import Optional
from pydantic import BaseModel

from app.schemas.administration.users.users import UserWithPermissionsOut

class LoginRequest(BaseModel):
    userName: str
    password: str
    rememberMe: Optional[bool] = False

class TokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
    user: Optional[UserWithPermissionsOut] = None
