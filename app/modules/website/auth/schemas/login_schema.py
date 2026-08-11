from pydantic import BaseModel, Field


class WebsiteLoginRequest(BaseModel):
    mobile: str = Field(
        min_length=10,
        max_length=10,
    )