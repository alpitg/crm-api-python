from typing import Optional

from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

from config import settings


# ============================================================
# TWILIO CONFIG
# ============================================================

TWILIO_ACCOUNT_SID = settings.TWILIO_ACCOUNT_SID

TWILIO_API_KEY = settings.TWILIO_API_KEY

TWILIO_API_SECRET = settings.TWILIO_API_SECRET

TWILIO_VERIFY_SERVICE_SID = (
    settings.TWILIO_VERIFY_SERVICE_SID
)


# ============================================================
# CLIENT
# ============================================================

_twilio_client: Optional[Client] = None


def _get_twilio_client() -> Client:
    """
    Create and reuse Twilio client.

    Authentication:
        Twilio API Key + API Secret

    Account:
        Twilio Account SID
    """

    global _twilio_client

    if _twilio_client is None:

        # ----------------------------------------------------
        # ACCOUNT SID
        # ----------------------------------------------------

        if not TWILIO_ACCOUNT_SID:
            raise RuntimeError(
                "TWILIO_ACCOUNT_SID is not configured."
            )

        # ----------------------------------------------------
        # API KEY
        # ----------------------------------------------------

        if not TWILIO_API_KEY:
            raise RuntimeError(
                "TWILIO_API_KEY is not configured."
            )

        # ----------------------------------------------------
        # API SECRET
        # ----------------------------------------------------

        if not TWILIO_API_SECRET:
            raise RuntimeError(
                "TWILIO_API_SECRET is not configured."
            )

        # ----------------------------------------------------
        # CREATE CLIENT
        # ----------------------------------------------------

        _twilio_client = Client(
            TWILIO_API_KEY,
            TWILIO_API_SECRET,
            TWILIO_ACCOUNT_SID,
        )

    return _twilio_client


# ============================================================
# MOBILE FORMAT
# ============================================================


def normalize_twilio_mobile(
    mobile: str,
) -> str:
    """
    Convert an Indian 10-digit mobile number
    into Twilio E.164 format.

    Example:

        9876543210
        ->
        +919876543210
    """

    if not mobile:
        raise ValueError(
            "Mobile number is required."
        )

    mobile = mobile.strip()

    # --------------------------------------------------------
    # Remove everything except digits
    # --------------------------------------------------------

    mobile = "".join(
        character
        for character in mobile
        if character.isdigit()
    )

    # --------------------------------------------------------
    # Validate length
    # --------------------------------------------------------

    if len(mobile) != 10:
        raise ValueError(
            "Please enter a valid 10-digit mobile number."
        )

    # --------------------------------------------------------
    # Validate Indian mobile prefix
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Convert to E.164
    # --------------------------------------------------------

    return f"+91{mobile}"


# ============================================================
# SEND OTP
# ============================================================


async def send_otp(
    mobile: str,
) -> dict:
    """
    Send OTP using Twilio Verify.

    Twilio handles:

    - OTP generation
    - OTP delivery
    - OTP expiration
    - OTP verification
    - verification attempt limits
    """

    try:

        # ----------------------------------------------------
        # NORMALIZE MOBILE
        # ----------------------------------------------------

        phone_number = normalize_twilio_mobile(
            mobile
        )

        # ----------------------------------------------------
        # VERIFY SERVICE
        # ----------------------------------------------------

        if not TWILIO_VERIFY_SERVICE_SID:
            raise RuntimeError(
                "TWILIO_VERIFY_SERVICE_SID "
                "is not configured."
            )

        # ----------------------------------------------------
        # GET TWILIO CLIENT
        # ----------------------------------------------------

        client = _get_twilio_client()

        # ----------------------------------------------------
        # SEND VERIFICATION
        # ----------------------------------------------------

        verification = (
            client.verify.v2
            .services(
                TWILIO_VERIFY_SERVICE_SID
            )
            .verifications
            .create(
                to=phone_number,
                channel="sms",
            )
        )

        # ----------------------------------------------------
        # RETURN RESULT
        # ----------------------------------------------------

        return {
            "success": True,
            "status": verification.status,
            "sid": verification.sid,
            "mobile": mobile,
            "twilio_mobile": phone_number,
        }

    except TwilioRestException as exc:

        # Don't expose sensitive Twilio details
        # directly to the frontend.

        print(
            "Twilio send OTP failed:",
            exc.msg,
        )

        raise RuntimeError(
            f"Unable to send OTP: {exc.msg}"
        ) from exc

    except Exception as exc:

        print(
            "Twilio send OTP error:",
            str(exc),
        )

        raise RuntimeError(
            f"Unable to send OTP: {str(exc)}"
        ) from exc


# ============================================================
# VERIFY OTP
# ============================================================


async def verify_otp(
    mobile: str,
    otp: str,
) -> bool:
    """
    Verify OTP using Twilio Verify.

    Returns:

        True
            OTP approved.

        False
            OTP invalid / expired / already used /
            verification failed.
    """

    # --------------------------------------------------------
    # OTP REQUIRED
    # --------------------------------------------------------

    if not otp:
        return False

    otp = otp.strip()

    # --------------------------------------------------------
    # OTP LENGTH
    # --------------------------------------------------------

    if len(otp) != 6:
        return False

    # --------------------------------------------------------
    # OTP NUMERIC
    # --------------------------------------------------------

    if not otp.isdigit():
        return False

    try:

        # ----------------------------------------------------
        # NORMALIZE MOBILE
        # ----------------------------------------------------

        phone_number = normalize_twilio_mobile(
            mobile
        )

        # ----------------------------------------------------
        # VERIFY SERVICE
        # ----------------------------------------------------

        if not TWILIO_VERIFY_SERVICE_SID:
            raise RuntimeError(
                "TWILIO_VERIFY_SERVICE_SID "
                "is not configured."
            )

        # ----------------------------------------------------
        # GET TWILIO CLIENT
        # ----------------------------------------------------

        client = _get_twilio_client()

        # ----------------------------------------------------
        # VERIFY CODE
        # ----------------------------------------------------

        verification_check = (
            client.verify.v2
            .services(
                TWILIO_VERIFY_SERVICE_SID
            )
            .verification_checks
            .create(
                to=phone_number,
                code=otp,
            )
        )

        # ----------------------------------------------------
        # CHECK STATUS
        # ----------------------------------------------------

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