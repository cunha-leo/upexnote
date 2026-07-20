"""SMTP delivery without logging recipients, codes, or credentials."""

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from html import escape
from typing import Protocol

from .config import Settings


class ResetMailer(Protocol):
    def send_reset_code(self, recipient: str, code: str, expires_minutes: int) -> None: ...


class AdminMailer(Protocol):
    def send_admin_code(self, recipient: str, code: str, expires_minutes: int) -> None: ...


class SmtpResetMailer:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_reset_code(self, recipient: str, code: str, expires_minutes: int) -> None:
        self._send_code(
            recipient,
            code,
            expires_minutes,
            "Código de recuperação do UpexNote",
            "Recuperação de senha do UpexNote",
            "Recebemos um pedido para redefinir a senha da sua conta UpexNote.",
        )

    def send_admin_code(self, recipient: str, code: str, expires_minutes: int) -> None:
        self._send_code(
            recipient,
            code,
            expires_minutes,
            "Código de acesso administrativo do UpexNote",
            "Confirmação de acesso administrativo",
            "Recebemos um pedido para abrir uma sessão administrativa no UpexNote.",
        )

    def _send_code(
        self,
        recipient: str,
        code: str,
        expires_minutes: int,
        subject: str,
        heading: str,
        introduction: str,
    ) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{self.settings.smtp_from_name} <{self.settings.smtp_from_email}>"
        message["To"] = recipient
        message.set_content(
            f"{introduction}\n\n"
            f"Código: {code}\n\n"
            f"Este código expira em {expires_minutes} minutos. "
            "Se não fez este pedido, ignore esta mensagem."
        )
        safe_code = escape(code)
        message.add_alternative(
            "<html><body style=\"font-family:Arial,sans-serif;color:#201c2b\">"
            f"<h2>{escape(heading)}</h2>"
            f"<p>{escape(introduction)}</p>"
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
