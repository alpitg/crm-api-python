from typing import Optional
from pydantic import BaseModel

class LoginRequest(BaseModel):
    userName: str
    password: str
    rememberMe: Optional[bool] = False

class TokenResponse(BaseModel):
    accessToken: str
    tokenType: str = "bearer"
