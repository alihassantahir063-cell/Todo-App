import smtplib
import ssl
from email.message import EmailMessage

from app.core.config import settings


def smtp_is_configured() -> bool:
    if not settings.smtp_host or not settings.smtp_from_email:
        return False
    has_username = bool(settings.smtp_username)
    has_password = bool(settings.smtp_password and settings.smtp_password.get_secret_value())
    return has_username == has_password


def send_password_reset_email(email: str, reset_url: str) -> None:
    if not smtp_is_configured():
        raise RuntimeError("SMTP settings are incomplete")

    message = EmailMessage()
    message["Subject"] = "Reset your Daymark password"
    message["From"] = settings.smtp_from_email
    message["To"] = email
    message.set_content(
        "We received a request to reset your Daymark password.\n\n"
        f"Use this link within 30 minutes to choose a new password:\n{reset_url}\n\n"
        "If you did not request this, you can ignore this email."
    )

    if settings.smtp_use_ssl:
        connection = smtplib.SMTP_SSL(
            settings.smtp_host,
            settings.smtp_port,
            timeout=10,
            context=ssl.create_default_context(),
        )
    else:
        connection = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10)

    with connection as smtp:
        if not settings.smtp_use_ssl:
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()
        if settings.smtp_username and settings.smtp_password:
            smtp.login(settings.smtp_username, settings.smtp_password.get_secret_value())
        smtp.send_message(message)
