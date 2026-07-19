"""Application service for password reset."""

from __future__ import annotations

import logging
import math

from .config import Settings
from .db import ResetRepository
from .emailer import ResetMailer
from .security import (
    generate_code,
    generate_reset_token,
    keyed_hash,
    new_password_credentials,
    normalize_email,
)


logger = logging.getLogger("upexnote.api")
GENERIC_REQUEST_MESSAGE = (
    "Se existir uma conta elegível para este e-mail, enviaremos um código de recuperação."
)


class ResetFlowError(ValueError):
    pass


class PasswordResetService:
    def __init__(self, settings: Settings, repository: ResetRepository, mailer: ResetMailer):
        self.settings = settings
        self.repository = repository
        self.mailer = mailer

    def ensure_schema(self) -> None:
        self.repository.ensure_schema()

    def health(self) -> None:
        self.repository.ping()

    def request_reset(self, email: str, client_ip: str) -> str:
        normalized = normalize_email(email)
        code = generate_code()
        try:
            started = self.repository.start_request(
                email=normalized,
                email_hash=keyed_hash(normalized, self.settings.reset_hmac_secret, "email"),
                ip_hash=keyed_hash(client_ip, self.settings.reset_hmac_secret, "ip"),
                code_hash=keyed_hash(code, self.settings.reset_hmac_secret, "code"),
                ttl_seconds=self.settings.reset_ttl_seconds,
                window_seconds=self.settings.reset_rate_window_seconds,
                email_limit=self.settings.reset_rate_email_max,
                ip_limit=self.settings.reset_rate_ip_max,
            )
            if started.accepted:
                try:
                    self.mailer.send_reset_code(
                        started.recipient or normalized,
                        code,
                        max(1, math.ceil(self.settings.reset_ttl_seconds / 60)),
                    )
                except Exception:
                    logger.exception("Password-reset email delivery failed")
                    if started.reset_id is not None and started.user_id is not None:
                        self.repository.invalidate_delivery(
                            started.reset_id, normalized, started.user_id
                        )
        except Exception:
            # Request stays non-enumerating even when a dependency is unavailable.
            logger.exception("Password-reset request could not be processed")
        return GENERIC_REQUEST_MESSAGE

    def verify_code(self, email: str, code: str) -> tuple[str, int]:
        normalized = normalize_email(email)
        token = generate_reset_token()
        result = self.repository.verify_code(
            email=normalized,
            email_hash=keyed_hash(normalized, self.settings.reset_hmac_secret, "email"),
            code_hash=keyed_hash(code, self.settings.reset_hmac_secret, "code"),
            reset_token_hash=keyed_hash(token, self.settings.reset_hmac_secret, "token"),
            token_ttl_seconds=self.settings.reset_token_ttl_seconds,
            max_attempts=self.settings.reset_max_attempts,
        )
        if not result.ok:
            raise ResetFlowError("invalid_or_expired_code")
        return token, self.settings.reset_token_ttl_seconds

    def complete_reset(self, email: str, token: str, new_password: str) -> None:
        normalized = normalize_email(email)
        salt, password_hash = new_password_credentials(new_password)
        result = self.repository.complete_reset(
            email=normalized,
            email_hash=keyed_hash(normalized, self.settings.reset_hmac_secret, "email"),
            reset_token_hash=keyed_hash(token, self.settings.reset_hmac_secret, "token"),
            password_salt=salt,
            password_hash=password_hash,
        )
        if not result.ok:
            raise ResetFlowError("invalid_or_expired_token")
