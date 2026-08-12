import logging
import os
from email.message import EmailMessage

import aiosmtplib

SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "") or SMTP_USER
SMTP_STARTTLS = os.environ.get("SMTP_STARTTLS", "true").lower() == "true"

logger = logging.getLogger("notifications.emailer")


async def send_email(to: str, subject: str, body: str) -> bool:
    if not SMTP_HOST:
        logger.warning("SMTP_HOST not set, skipping email")
        return False

    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER or None,
            password=SMTP_PASSWORD or None,
            start_tls=SMTP_STARTTLS,
        )
    except Exception:
        logger.warning("email failed for %s", to, exc_info=True)
        return False
    return True
