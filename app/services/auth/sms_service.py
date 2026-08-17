import httpx

from config import settings


class SMSServiceError(Exception):
    pass


class SMSService:
    BASE_URL = "https://api.msg91.com/api/v5/flow/"

    def __init__(self):
        self.auth_key = settings.MSG91_AUTH_KEY
        self.sender_id = settings.MSG91_SENDER_ID
        self.template_id = settings.MSG91_OTP_TEMPLATE_ID

    @staticmethod
    def _normalize_mobile(mobile: str) -> str:
        mobile = str(mobile).strip()

        mobile = "".join(
            character
            for character in mobile
            if character.isdigit()
        )

        if len(mobile) == 10:
            mobile = f"91{mobile}"

        if len(mobile) != 12 or not mobile.startswith("91"):
            raise SMSServiceError(
                "Invalid mobile number."
            )

        return mobile

    async def send_otp(
        self,
        *,
        mobile: str,
        otp: str,
    ) -> bool:
        mobile = self._normalize_mobile(mobile)

        if not otp:
            raise SMSServiceError(
                "OTP is required."
            )

        payload = {
            "flow_id": self.template_id,
            "sender": self.sender_id,
            "recipients": [
                {
                    "mobiles": mobile,
                    "VAR1": otp,
                }
            ],
        }

        headers = {
            "authkey": self.auth_key,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(
                timeout=10.0
            ) as client:

                response = await client.post(
                    self.BASE_URL,
                    json=payload,
                    headers=headers,
                )

        except httpx.RequestError as exc:
            raise SMSServiceError(
                "Unable to connect to SMS provider."
            ) from exc

        if response.status_code >= 400:
            raise SMSServiceError(
                f"SMS provider returned HTTP "
                f"{response.status_code}."
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise SMSServiceError(
                "Invalid response from SMS provider."
            ) from exc

        if data.get("type") != "success":
            raise SMSServiceError(
                data.get(
                    "message",
                    "SMS delivery failed.",
                )
            )

        return True


sms_service = SMSService()