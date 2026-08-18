from typing import Optional

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from config import settings

from app.services.auth.otp.base import OTPProvider


class TwilioOTPProvider(
    OTPProvider
):
    """
    Twilio Verify OTP provider.

    Authentication:

        Account SID
        API Key
        API Secret

    Twilio Verify handles:

        - OTP generation
        - OTP delivery
        - OTP expiration
        - OTP verification
        - verification attempts
    """

    def __init__(self):
        self.account_sid = (
            settings.TWILIO_ACCOUNT_SID
        )

        self.api_key = (
            settings.TWILIO_API_KEY
        )

        self.api_secret = (
            settings.TWILIO_API_SECRET
        )

        self.verify_service_sid = (
            settings.TWILIO_VERIFY_SERVICE_SID
        )

        self._client: Optional[Client] = None

    # ========================================================
    # CLIENT
    # ========================================================

    def _get_client(self) -> Client:
        """
        Create/reuse Twilio client.
        """

        if self._client is not None:
            return self._client

        if not self.account_sid:
            raise RuntimeError(
                "TWILIO_ACCOUNT_SID is not configured."
            )

        if not self.api_key:
            raise RuntimeError(
                "TWILIO_API_KEY is not configured."
            )

        if not self.api_secret:
            raise RuntimeError(
                "TWILIO_API_SECRET is not configured."
            )

        self._client = Client(
            self.api_key,
            self.api_secret,
            self.account_sid,
        )

        return self._client

    # ========================================================
    # PHONE NUMBER
    # ========================================================

    def _normalize_mobile(
        self,
        mobile: str,
    ) -> str:
        """
        Convert Indian mobile number
        to E.164 format.

        9876543210
        ->
        +919876543210
        """

        if not mobile:
            raise ValueError(
                "Mobile number is required."
            )

        mobile = mobile.strip()

        mobile = "".join(
            character
            for character in mobile
            if character.isdigit()
        )

        if len(mobile) != 10:
            raise ValueError(
                "Please enter a valid 10-digit mobile number."
            )

        if not mobile.startswith(
            (
                "6",
                "7",
                "8",
                "9",
            )
        ):
            raise ValueError(
                "Please enter a valid Indian mobile number."
            )

        return f"+91{mobile}"

    # ========================================================
    # SEND OTP
    # ========================================================

    async def send_otp(
        self,
        mobile: str,
    ) -> dict:

        try:

            phone_number = (
                self._normalize_mobile(
                    mobile
                )
            )

            if not self.verify_service_sid:
                raise RuntimeError(
                    "TWILIO_VERIFY_SERVICE_SID "
                    "is not configured."
                )

            client = self._get_client()

            verification = (
                client.verify.v2
                .services(
                    self.verify_service_sid
                )
                .verifications
                .create(
                    to=phone_number,
                    channel="sms",
                )
            )

            return {
                "success": True,
                "provider": "twilio",
                "provider_reference": (
                    verification.sid
                ),
                "status": (
                    verification.status
                ),
                "mobile": phone_number,
            }

        except TwilioRestException as exc:

            raise RuntimeError(
                f"Twilio OTP send failed: {exc.msg}"
            ) from exc

        except Exception as exc:

            raise RuntimeError(
                f"Twilio OTP send failed: {str(exc)}"
            ) from exc

    # ========================================================
    # VERIFY OTP
    # ========================================================

    async def verify_otp(
        self,
        mobile: str,
        otp: str,
    ) -> bool:

        if not otp:
            return False

        otp = otp.strip()

        if len(otp) != 6:
            return False

        if not otp.isdigit():
            return False

        try:

            phone_number = (
                self._normalize_mobile(
                    mobile
                )
            )

            if not self.verify_service_sid:
                raise RuntimeError(
                    "TWILIO_VERIFY_SERVICE_SID "
                    "is not configured."
                )

            client = self._get_client()

            verification_check = (
                client.verify.v2
                .services(
                    self.verify_service_sid
                )
                .verification_checks
                .create(
                    to=phone_number,
                    code=otp,
                )
            )

            return (
                verification_check.status
                == "approved"
            )

        except TwilioRestException as exc:

            print(
                "Twilio OTP verification failed:",
                exc.msg,
            )

            return False

        except Exception as exc:

            print(
                "OTP verification error:",
                str(exc),
            )

            return False