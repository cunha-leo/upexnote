"""SMTP delivery without logging recipients, codes, or credentials."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from html import escape
from typing import Protocol

from .config import Settings


class ResetMailer(Protocol):
    def send_reset_code(self, recipient: str, code: str, expires_minutes: int) -> None: ...


class SmtpResetMailer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_reset_code(self, recipient: str, code: str, expires_minutes: int) -> None:
        message = EmailMessage()
        message["Subject"] = "Código de recuperação do UpexNote"
        message["From"] = f"{self.settings.smtp_from_name} <{self.settings.smtp_from_email}>"
        message["To"] = recipient
        message.set_content(
            "Recebemos um pedido para redefinir a senha da sua conta UpexNote.\n\n"
            f"Código: {code}\n\n"
            f"Este código expira em {expires_minutes} minutos. "
            "Se não fez este pedido, ignore esta mensagem."
        )
        safe_code = escape(code)
        message.add_alternative(
            "<html><body style=\"font-family:Arial,sans-serif;color:#201c2b\">"
            "<h2>Recuperação de senha do UpexNote</h2>"
            "<p>Use o código abaixo para continuar:</p>"
            f"<p style=\"font-size:28px;letter-spacing:8px;font-weight:700\">{safe_code}</p>"
            f"<p>O código expira em {expires_minutes} minutos.</p>"
            "<p>Se não fez este pedido, ignore esta mensagem.</p>"
            "</body></html>",
            subtype="html",
        )

        smtp_class = smtplib.SMTP_SSL if self.settings.smtp_ssl else smtplib.SMTP
        with smtp_class(
            self.settings.smtp_host,
            self.settings.smtp_port,
            timeout=15,
        ) as client:
            if self.settings.smtp_starttls:
                client.starttls()
            client.login(self.settings.smtp_username, self.settings.smtp_password)
            client.send_message(message)
