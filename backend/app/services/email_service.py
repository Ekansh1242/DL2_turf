from __future__ import annotations

import logging
import os
import smtplib
import ssl
from dotenv import load_dotenv
load_dotenv()
from email.message import EmailMessage

logger = logging.getLogger("campussphere.email")

SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "no-reply@campussphere.local")


def is_email_configured() -> bool:
    return bool(SMTP_HOST and SMTP_USER and SMTP_PASS)


def send_booking_confirmation_email(
    to_email: str, subject: str, body_text: str, pdf_bytes: bytes, pdf_filename: str
) -> bool:
    """Send the booking confirmation with the PDF receipt attached.

    Returns True if the email was actually sent, False if skipped/failed.
    Never raises -- a booking that already succeeded in the DB should not
    be rolled back or reported as failed just because email delivery had
    a problem.
    """
    if not is_email_configured():
        logger.info("SMTP not configured -- skipping confirmation email to %s", to_email)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body_text)
    msg.add_attachment(pdf_bytes, maintype="application", subtype="pdf", filename=pdf_filename)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send booking confirmation email to %s", to_email)
        return False


def send_plain_email(to_email: str, subject: str, body_text: str) -> bool:
    """For notifications that don't need a PDF attachment -- waitlist
    slot-opened alerts, etc. Same never-raises contract as above."""
    if not is_email_configured():
        logger.info("SMTP not configured -- skipping email to %s", to_email)
        return False

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg.set_content(body_text)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception:
        logger.exception("Failed to send email to %s", to_email)
        return False
