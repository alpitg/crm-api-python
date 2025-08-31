from typing import Optional
from pydantic import BaseModel, EmailStr

from app.schemas.administration.users.users import UserWithPermissionsOut

class LoginRequest(BaseModel):
    userName: str
    password: str
    rememberMe: Optional[bool] = False

class TokenResponse(BaseModel):
    accessToken: str
    refreshToken: str
    tokenType: str = "bearer"

class ForgotPasswordRequest(BaseModel):
    emailAddress: EmailStr

class ResetPasswordRequest(BaseModel):
    code: str
    newPassword: str
