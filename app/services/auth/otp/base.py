from abc import ABC, abstractmethod


class OTPProvider(ABC):
    """
    Base interface for all OTP providers.

    Every provider must implement:

        send_otp()
        verify_otp()
    """

    @abstractmethod
    async def send_otp(
        self,
        mobile: str,
    ) -> dict:
        """
        Send OTP.

        Returns:

        {
            "success": True,
            "provider": "twilio",
            "provider_reference": "...",
            "mobile": "+919876543210",
        }
        """
        raise NotImplementedError

    @abstractmethod
    async def verify_otp(
        self,
        mobile: str,
        otp: str,
    ) -> bool:
        """
        Verify OTP.

        Returns:

            True  -> verified
            False -> invalid
        """
        raise NotImplementedError