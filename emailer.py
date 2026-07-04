"""SMTP email sender — used after user approves a draft in Telegram."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_USER


def configured() -> bool:
    return bool(SMTP_USER and SMTP_PASS)


def send(to: str, subject: str, body: str) -> str:
    """Send a plain-text email. Returns 'sent' or an error string."""
    if not configured():
        return "SMTP not configured — add SMTP_USER and SMTP_PASS to .env"
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = SMTP_USER
        msg["To"] = to
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as s:
            s.ehlo()
            s.starttls()
            s.login(SMTP_USER, SMTP_PASS)
            s.sendmail(SMTP_USER, [to], msg.as_string())
        return "sent"
    except Exception as e:
        return f"failed: {e}"
