"""
utils/email_sender.py
---------------------
Sends the job digest email via Gmail SMTP.

WHY APP PASSWORD (not your real password)?
  Gmail has blocked "less secure apps" since 2022.
  Any script/program must use a 16-char App Password instead.
  This is NOT your real password – it only works for email sending,
  can be revoked anytime, and keeps your account safe.

HOW TO GET ONE (takes ~2 min):
  1. Visit https://myaccount.google.com/security
  2. Turn on 2-Step Verification
  3. Search "App passwords" → Select Mail + Device → Generate
  4. Copy the 16-char code into SENDER_APP_PASSWORD in .env
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import date

from utils.logger import get_logger

logger = get_logger("EmailSender")


def send_job_digest(html_body: str, plain_body: str, subject: str = "") -> bool:
    """
    Send the digest to all recipients listed in RECIPIENT_EMAILS.
    Returns True on success, False on failure.
    """
    sender_email    = os.getenv("SENDER_EMAIL", "").strip()
    app_password    = os.getenv("SENDER_APP_PASSWORD", "").strip()
    recipients_raw  = os.getenv("RECIPIENT_EMAILS", "").strip()

    if not sender_email:
        logger.error("SENDER_EMAIL not set in .env")
        return False
    if not app_password:
        logger.error("SENDER_APP_PASSWORD not set in .env")
        return False
    if not recipients_raw:
        logger.error("RECIPIENT_EMAILS not set in .env")
        return False

    recipients = [r.strip() for r in recipients_raw.split(",") if r.strip()]
    today = date.today().strftime("%B %d, %Y")
    subject = subject or f"🚀 Tech Job Digest – {today} | Fresh Openings Inside"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = f"Tech Job Agent <{sender_email}>"
    msg["To"]      = ", ".join(recipients)

    msg.attach(MIMEText(plain_body, "plain", "utf-8"))
    msg.attach(MIMEText(html_body,  "html",  "utf-8"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, app_password)
            server.sendmail(sender_email, recipients, msg.as_string())
        logger.info(f"Email sent to {len(recipients)} recipient(s): {', '.join(recipients)}")
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error(
            "Gmail authentication failed!\n"
            "  → Make sure SENDER_APP_PASSWORD is the 16-char App Password,\n"
            "    NOT your real Gmail password.\n"
            "  → Guide: https://support.google.com/accounts/answer/185833"
        )
        return False
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False