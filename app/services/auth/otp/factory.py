from app.services.auth.otp.base import (
    OTPProvider,
)

from app.services.auth.otp.providers.sms.twilio_provider import (
    TwilioOTPProvider,
)


_twilio_provider = (
    TwilioOTPProvider()
)


def get_otp_provider(
    provider: str | None = None,
) -> OTPProvider:
    """
    Return configured OTP provider.

    Example:

        get_otp_provider("twilio")

    """

    provider_name = (
        provider
        or "twilio"
    ).lower().strip()

    # ========================================================
    # TWILIO
    # ========================================================

    if provider_name == "twilio":
        return _twilio_provider

    # ========================================================
    # FUTURE PROVIDERS
    # ========================================================

    # if provider_name == "msg91":
    #     return _msg91_provider

    # if provider_name == "aws":
    #     return _aws_provider

    raise ValueError(
        f"Unsupported OTP provider: "
        f"{provider_name}"
    )