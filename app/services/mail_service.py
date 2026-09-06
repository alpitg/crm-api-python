from email.message import EmailMessage
import os
import smtplib
from typing import List, Union


def send_email(
    subject: str,
    recipients: Union[str, List[str]],
    body: str,
):
    """
    Send a plain text email.

    Uses local SMTP when MAIL_MODE=local.
    Uses real SMTP when MAIL_MODE=real.

    Env vars for MAIL_MODE=real:
    MAIL_HOST
    MAIL_PORT
    MAIL_USER
    MAIL_PASS
    MAIL_USE_TLS
    MAIL_FROM
    """

    if isinstance(recipients, str):
        recipients = [recipients]

    msg = EmailMessage()
    msg["From"] = os.getenv("MAIL_FROM", "dev@example.com")
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    mail_mode = os.getenv("MAIL_MODE", "local")

    if mail_mode == "local":
        smtp_host = os.getenv("MAIL_HOST", "localhost")
        smtp_port = int(os.getenv("MAIL_PORT", 1025))

        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.send_message(msg)

        print(
            f"✅ [LOCAL] Email sent to {', '.join(recipients)}"
        )

    else:
        smtp_host = os.getenv(
            "MAIL_HOST",
            "sandbox.smtp.mailtrap.io",
        )
        smtp_port = int(os.getenv("MAIL_PORT", 587))
        smtp_user = os.getenv("MAIL_USER", "xxxxxx")
        smtp_pass = os.getenv("MAIL_PASS", "xxxxxx")
        use_tls = (
            os.getenv("MAIL_USE_TLS", "true").lower() == "true"
        )

        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            if use_tls:
                smtp.starttls()

            if smtp_user and smtp_pass:
                smtp.login(smtp_user, smtp_pass)

            smtp.send_message(msg)

        print(
            f"✅ [REAL] Email sent to {', '.join(recipients)} "
            f"via {smtp_host}"
        )


async def send_otp(
    email: str,
    otp: str,
):
    """
    Send login OTP to customer's email.
    """

    if not email:
        raise ValueError("Email address is required.")

    if not otp:
        raise ValueError("OTP is required.")

    subject = "Your Login OTP"

    body = (
        "Hello,\n\n"
        f"Your login OTP is: {otp}\n\n"
        "This OTP is valid for 5 minutes.\n"
        "Please do not share this OTP with anyone.\n\n"
        "Thank you."
    )

    send_email(
        subject=subject,
        recipients=email,
        body=body,
    )
