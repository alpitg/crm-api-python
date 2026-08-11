from pydantic import BaseModel


class UserResponse(BaseModel):
    id: str
    mobile: str | None = None
    name: str | None = None
    email: str | None = None


class AuthResponse(BaseModel):
    success: bool
    message: str

    access_token: str
    refresh_token: str

    token_type: str = "bearer"

    user: UserResponse