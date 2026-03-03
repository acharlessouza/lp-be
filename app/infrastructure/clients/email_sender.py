from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.application.ports.email_sender_port import EmailSenderPort


logger = logging.getLogger(__name__)


class ConsoleEmailSender(EmailSenderPort):
    def send_password_reset_email(self, *, to_email: str, reset_link: str) -> None:
        logger.info("password_reset_email to=%s link=%s", to_email, reset_link)


class SMTPEmailSender(EmailSenderPort):
    def __init__(self, *, host: str, port: int, user: str, password: str, sender: str):
        self._host = host
        self._port = port
        self._user = user
        self._password = password
        self._sender = sender

    def send_password_reset_email(self, *, to_email: str, reset_link: str) -> None:
        message = EmailMessage()
        message["Subject"] = "Recuperacao de senha"
        message["From"] = self._sender
        message["To"] = to_email
        message.set_content(
            "Recebemos uma solicitacao para redefinir sua senha. "
            f"Use o link a seguir: {reset_link}"
        )

        with smtplib.SMTP(self._host, self._port, timeout=15) as smtp:
            smtp.starttls()
            if self._user:
                smtp.login(self._user, self._password)
            smtp.send_message(message)
