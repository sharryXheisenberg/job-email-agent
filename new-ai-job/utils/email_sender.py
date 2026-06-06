import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from .logger import get_logger

logger = get_logger("EmailSender")

def send_email(sender_email, password, recipients, subject, html_content, text_content):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender_email
        msg["To"] = ", ".join(recipients)

        msg.attach(MIMEText(text_content, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, recipients, msg.as_string())
        
        logger.info(f"Email successfully sent to {len(recipients)} recipients.")
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        raise e
