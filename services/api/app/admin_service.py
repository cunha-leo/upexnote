"""Administrative elevation: account + admin secret + e-mail/TOTP factor."""

from __future__ import annotations

import logging
import math

from .admin_db import AdminElevationRepository
from .config import Settings
from .emailer import AdminMailer
from .security import (
    constant_time_equal,
    encrypt_totp_secret,
    generate_code,
    generate_reset_token,
    generate_totp_secret,
    keyed_hash,
    normalize_email,
    qr_svg_data_url,
    totp_uri,
)


logger = logging.getLogger("upexnote.api")
GENERIC_ADMIN_MESSAGE = "Se a conta for elegível, enviaremos o próximo passo de segurança."


class AdminFlowError(ValueError):
    pass


class AdminElevationService:
    def __init__(self, settings: Settings, repository: AdminElevationRepository, mailer: AdminMailer):
        self.settings = settings
        self.repository = repository
        self.mailer = mailer

    def ensure_schema(self) -> None:
        self.repository.ensure_schema()

    def request_challenge(
        self, email: str, admin_secret: str, client_ip: str, prefer_email: bool = False
    ) -> tuple[str, str]:
        normalized = normalize_email(email)
        code = generate_code()
        try:
            started = self.repository.start_challenge(
                email=normalized,
                email_hash=keyed_hash(normalized, self.settings.reset_hmac_secret, "admin-email"),
                ip_hash=keyed_hash(client_ip, self.settings.reset_hmac_secret, "admin-ip"),
                code_hash=keyed_hash(code, self.settings.reset_hmac_secret, "admin-code"),
                credential_ok=constant_time_equal(admin_secret, self.settings.db_password),
                prefer_email=prefer_email,
                ttl_seconds=self.settings.admin_code_ttl_seconds,
                window_seconds=self.settings.admin_rate_window_seconds,
                email_limit=self.settings.admin_rate_email_max,
                ip_limit=self.settings.admin_rate_ip_max,
            )
            if started.accepted and started.factor == "email":
                try:
                    self.mailer.send_admin_code(
                        started.recipient or normalized,
                        code,
                        max(1, math.ceil(self.settings.admin_code_ttl_seconds / 60)),
                    )
                except Exception:
                    logger.exception("Administrative MFA email delivery failed")
                    if started.challenge_id is not None and started.user_id is not None:
                        self.repository.invalidate_delivery(
                            started.challenge_id, normalized, started.user_id
                        )
            return GENERIC_ADMIN_MESSAGE, started.factor if started.accepted else "email"
        except Exception:
            logger.exception("Administrative MFA challenge could not be processed")
            return GENERIC_ADMIN_MESSAGE, "email"

    def verify_factor(self, email: str, code: str) -> tuple[str, int, str, bool]:
        normalized = normalize_email(email)
        token = generate_reset_token()
        result = self.repository.verify_factor(
            email=normalized,
            email_hash=keyed_hash(normalized, self.settings.reset_hmac_secret, "admin-email"),
            code=code,
            email_code_hash=keyed_hash(code, self.settings.reset_hmac_secret, "admin-code"),
            session_token_hash=keyed_hash(token, self.settings.reset_hmac_secret, "admin-session"),
            session_ttl_seconds=self.settings.admin_session_ttl_seconds,
            max_attempts=self.settings.admin_max_attempts,
        )
        if not result.ok:
            raise AdminFlowError("invalid_or_expired_code")
        return token, self.settings.admin_session_ttl_seconds, result.factor, result.totp_enrolled

    def validate_session(self, email: str, token: str):
        normalized = normalize_email(email)
        return self.repository.validate_session(
            email_hash=keyed_hash(normalized, self.settings.reset_hmac_secret, "admin-email"),
            session_token_hash=keyed_hash(token, self.settings.reset_hmac_secret, "admin-session"),
        )

    def revoke_session(self, email: str, token: str) -> None:
        normalized = normalize_email(email)
        self.repository.revoke_session(
            email=normalized,
            email_hash=keyed_hash(normalized, self.settings.reset_hmac_secret, "admin-email"),
            session_token_hash=keyed_hash(token, self.settings.reset_hmac_secret, "admin-session"),
        )

    def begin_totp_enrollment(self, email: str, token: str) -> tuple[str, str, int]:
        normalized = normalize_email(email)
        secret = generate_totp_secret()
        encrypted = encrypt_totp_secret(secret, self.settings.reset_hmac_secret)
        ok = self.repository.begin_totp_enrollment(
            email_hash=keyed_hash(normalized, self.settings.reset_hmac_secret, "admin-email"),
            session_token_hash=keyed_hash(token, self.settings.reset_hmac_secret, "admin-session"),
            encrypted_secret=encrypted,
            ttl_seconds=self.settings.admin_code_ttl_seconds,
        )
        if not ok:
            raise AdminFlowError("invalid_or_expired_session")
        uri = totp_uri(secret, normalized)
        return qr_svg_data_url(uri), secret, self.settings.admin_code_ttl_seconds

    def confirm_totp_enrollment(self, email: str, token: str, code: str) -> None:
        normalized = normalize_email(email)
        ok = self.repository.confirm_totp_enrollment(
            email=normalized,
            email_hash=keyed_hash(normalized, self.settings.reset_hmac_secret, "admin-email"),
            session_token_hash=keyed_hash(token, self.settings.reset_hmac_secret, "admin-session"),
            code=code,
            max_attempts=self.settings.admin_max_attempts,
        )
        if not ok:
            raise AdminFlowError("invalid_or_expired_code")
