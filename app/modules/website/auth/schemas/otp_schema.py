from typing import Optional

from pydantic import BaseModel, Field, model_validator


# ============================================================
# SEND OTP
# ============================================================


class SendOTPRequest(BaseModel):
    email: Optional[str] = Field(
        default=None,
    )

    mobile: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=10,
    )

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.mobile:
            raise ValueError(
                "Either email or mobile is required."
            )

        if self.email and self.mobile:
            raise ValueError(
                "Provide either email or mobile, not both."
            )

        if self.email:
            self.email = self.email.strip().lower()

            if not self.email:
                raise ValueError(
                    "Email is required."
                )

        if self.mobile:
            self.mobile = self.mobile.strip()

            if not self.mobile.isdigit():
                raise ValueError(
                    "Mobile number must contain only digits."
                )

            if len(self.mobile) != 10:
                raise ValueError(
                    "Mobile number must be 10 digits."
                )

        return self


# ============================================================
# VERIFY OTP
# ============================================================


class VerifyOTPRequest(BaseModel):
    email: Optional[str] = Field(
        default=None,
    )

    mobile: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=10,
    )

    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
    )

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.mobile:
            raise ValueError(
                "Either email or mobile is required."
            )

        if self.email and self.mobile:
            raise ValueError(
                "Provide either email or mobile, not both."
            )

        if self.email:
            self.email = self.email.strip().lower()

            if not self.email:
                raise ValueError(
                    "Email is required."
                )

        if self.mobile:
            self.mobile = self.mobile.strip()

            if not self.mobile.isdigit():
                raise ValueError(
                    "Mobile number must contain only digits."
                )

            if len(self.mobile) != 10:
                raise ValueError(
                    "Mobile number must be 10 digits."
                )

        self.otp = self.otp.strip()

        if not self.otp.isdigit():
            raise ValueError(
                "OTP must contain only digits."
            )

        return self


# ============================================================
# RESEND OTP
# ============================================================


class ResendOTPRequest(BaseModel):
    email: Optional[str] = Field(
        default=None,
    )

    mobile: Optional[str] = Field(
        default=None,
        min_length=10,
        max_length=10,
    )

    @model_validator(mode="after")
    def validate_identifier(self):
        if not self.email and not self.mobile:
            raise ValueError(
                "Either email or mobile is required."
            )

        if self.email and self.mobile:
            raise ValueError(
                "Provide either email or mobile, not both."
            )

        if self.email:
            self.email = self.email.strip().lower()

            if not self.email:
                raise ValueError(
                    "Email is required."
                )

        if self.mobile:
            self.mobile = self.mobile.strip()

            if not self.mobile.isdigit():
                raise ValueError(
                    "Mobile number must be 10 digits."
                )

            if len(self.mobile) != 10:
                raise ValueError(
                    "Mobile number must be 10 digits."
                )

        return self


# ============================================================
# OTP RESPONSE
# ============================================================


class OTPResponse(BaseModel):
    success: bool
    message: str
    expiresIn: int | None = None
    retryAfter: int | None = None