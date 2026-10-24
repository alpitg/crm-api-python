
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================
# TYPES
# ============================================================

QuoteHomeType = Literal[
    "1 BHK",
    "2 BHK",
    "3 BHK",
    "4+ BHK",
    "Villa",
]


# ============================================================
# REQUEST SCHEMA
# ============================================================

class WebsiteQuoteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Customer's full name",
    )

    phone: str = Field(
        ...,
        pattern=r"^[6-9][0-9]{9}$",
        description="10-digit Indian mobile number",
    )

    homeType: QuoteHomeType = Field(
        ...,
        description="Customer's home type",
    )

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        if isinstance(value, str):
            value = " ".join(value.split())

        return value

    @field_validator("phone", mode="before")
    @classmethod
    def normalize_phone(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()

        return value


# ============================================================
# RESPONSE SCHEMA
# ============================================================

class WebsiteQuoteResponse(BaseModel):
    success: bool
    message: str
    quoteId: str
    createdAt: datetime
