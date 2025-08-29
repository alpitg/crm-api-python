from email.message import EmailMessage
import os
import smtplib
from typing import List, Union


def send_email(subject: str, recipients: Union[str, List[str]], body: str):
    """
    Send a plain text email.
    - Uses local SMTP (localhost:1025) if MAIL_MODE=local
    - Uses real SMTP (with login) if MAIL_MODE=real

    Env vars (for MAIL_MODE=real):
      MAIL_HOST, MAIL_PORT, MAIL_USER, MAIL_PASS, MAIL_USE_TLS (true/false)
    """

    if isinstance(recipients, str):
        recipients = [recipients]

    msg = EmailMessage()
    msg["From"] = os.getenv("MAIL_FROM", "dev@example.com")
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.set_content(body)

    mail_mode = os.getenv("MAIL_MODE", "local")  # "local" or "real"

    if mail_mode == "local":
        # Works with MailHog, Mailpit, aiosmtpd debug server
        smtp_host = os.getenv("MAIL_HOST", "localhost")
        smtp_port = int(os.getenv("MAIL_PORT", 1025))
        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            smtp.send_message(msg)
        print(f"✅ [LOCAL] Email sent to {', '.join(recipients)}")

    else:  # real SMTP (Gmail, Mailtrap, etc.)
        smtp_host = os.getenv("MAIL_HOST", "sandbox.smtp.mailtrap.io")
        smtp_port = int(os.getenv("MAIL_PORT", 587))
        smtp_user = os.getenv("MAIL_USER", "xxxxxx")
        smtp_pass = os.getenv("MAIL_PASS", "xxxxxx")
        use_tls = os.getenv("MAIL_USE_TLS", "true").lower() == "true"

        with smtplib.SMTP(smtp_host, smtp_port) as smtp:
            if use_tls:
                smtp.starttls()
            if smtp_user and smtp_pass:
                smtp.login(smtp_user, smtp_pass)
            smtp.send_message(msg)

        print(f"✅ [REAL] Email sent to {', '.join(recipients)} via {smtp_host}")
