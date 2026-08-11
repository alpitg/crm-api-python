from pydantic import BaseModel

from app.modules.website.auth.schemas.auth_schema import UserResponse


class MeResponse(BaseModel):
    success: bool
    user: UserResponse