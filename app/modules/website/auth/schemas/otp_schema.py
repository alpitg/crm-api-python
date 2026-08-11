from pydantic import BaseModel, Field


class SendOTPRequest(BaseModel):
    mobile: str = Field(
        ...,
        min_length=10,
        max_length=10,
    )


class VerifyOTPRequest(BaseModel):
    mobile: str = Field(
        ...,
        min_length=10,
        max_length=10,
    )

    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
    )


class ResendOTPRequest(BaseModel):
    mobile: str = Field(
        ...,
        min_length=10,
        max_length=10,
    )


class OTPResponse(BaseModel):
    success: bool
    message: str
    expires_in: int | None = None
    retry_after: int | None = None