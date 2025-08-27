from typing import Optional
from pydantic import BaseModel

class LoginRequest(BaseModel):
    userName: str
    password: str
    rememberMe: Optional[bool] = False

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
