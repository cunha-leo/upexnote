"""Environment-only configuration for the UpexNote API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


class ConfigurationError(RuntimeError):
    """Raised when a required deployment setting is absent or invalid."""


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigurationError(f"Missing required environment variable: {name}")
    return value


def _integer(name: str, default: int, minimum: int = 1) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if value < minimum:
        raise ConfigurationError(f"{name} must be at least {minimum}")
    return value


def _boolean(name: str, default: bool) -> bool:
    raw = os.getenv(name, str(default)).strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    raise ConfigurationError(f"{name} must be true or false")


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    reset_hmac_secret: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_from_email: str
    smtp_from_name: str
    smtp_starttls: bool
    smtp_ssl: bool
    reset_ttl_seconds: int
    reset_token_ttl_seconds: int
    reset_max_attempts: int
    reset_rate_window_seconds: int
    reset_rate_email_max: int
    reset_rate_ip_max: int
    admin_code_ttl_seconds: int
    admin_session_ttl_seconds: int
    admin_max_attempts: int
    admin_rate_window_seconds: int
    admin_rate_email_max: int
    admin_rate_ip_max: int
    support_spool_dir: str = "/data/support-spool"
    support_attachment_max_bytes: int = 10 * 1024 * 1024
    support_admin_email: str = "support@upexflow.com"

    @classmethod
    def from_environment(cls) -> "Settings":
        secret = _required("UPEXNOTE_RESET_HMAC_SECRET")
        if len(secret) < 32:
            raise ConfigurationError("UPEXNOTE_RESET_HMAC_SECRET must contain at least 32 characters")
        smtp_ssl = _boolean("UPEXNOTE_SMTP_SSL", False)
        smtp_starttls = _boolean("UPEXNOTE_SMTP_STARTTLS", not smtp_ssl)
        if smtp_ssl and smtp_starttls:
            raise ConfigurationError("SMTP SSL and STARTTLS cannot both be enabled")
        return cls(
            db_host=os.getenv("UPEXNOTE_DB_HOST", "upexnote-db").strip() or "upexnote-db",
            db_port=_integer("UPEXNOTE_DB_PORT", 5432),
            db_name=_required("UPEXNOTE_DB_NAME"),
            db_user=_required("UPEXNOTE_DB_USER"),
            db_password=_required("UPEXNOTE_DB_PASSWORD"),
            reset_hmac_secret=secret,
            smtp_host=_required("UPEXNOTE_SMTP_HOST"),
            smtp_port=_integer("UPEXNOTE_SMTP_PORT", 587),
            smtp_username=_required("UPEXNOTE_SMTP_USERNAME"),
            smtp_password=_required("UPEXNOTE_SMTP_PASSWORD"),
            smtp_from_email=_required("UPEXNOTE_SMTP_FROM_EMAIL"),
            smtp_from_name=os.getenv("UPEXNOTE_SMTP_FROM_NAME", "UpexNote").strip() or "UpexNote",
            smtp_starttls=smtp_starttls,
            smtp_ssl=smtp_ssl,
            reset_ttl_seconds=_integer("UPEXNOTE_RESET_TTL_SECONDS", 600, 60),
            reset_token_ttl_seconds=_integer("UPEXNOTE_RESET_TOKEN_TTL_SECONDS", 600, 60),
            reset_max_attempts=_integer("UPEXNOTE_RESET_MAX_ATTEMPTS", 5),
            reset_rate_window_seconds=_integer("UPEXNOTE_RESET_RATE_WINDOW_SECONDS", 900, 60),
            reset_rate_email_max=_integer("UPEXNOTE_RESET_RATE_EMAIL_MAX", 3),
            reset_rate_ip_max=_integer("UPEXNOTE_RESET_RATE_IP_MAX", 10),
            admin_code_ttl_seconds=_integer("UPEXNOTE_ADMIN_CODE_TTL_SECONDS", 600, 60),
            admin_session_ttl_seconds=_integer("UPEXNOTE_ADMIN_SESSION_TTL_SECONDS", 28800, 300),
            admin_max_attempts=_integer("UPEXNOTE_ADMIN_MAX_ATTEMPTS", 5),
            admin_rate_window_seconds=_integer("UPEXNOTE_ADMIN_RATE_WINDOW_SECONDS", 900, 60),
            admin_rate_email_max=_integer("UPEXNOTE_ADMIN_RATE_EMAIL_MAX", 3),
            admin_rate_ip_max=_integer("UPEXNOTE_ADMIN_RATE_IP_MAX", 10),
            support_spool_dir=os.getenv("UPEXNOTE_SUPPORT_SPOOL_DIR", "/data/support-spool").strip() or "/data/support-spool",
            support_attachment_max_bytes=_integer("UPEXNOTE_SUPPORT_ATTACHMENT_MAX_BYTES", 10 * 1024 * 1024, 1),
            support_admin_email=os.getenv("UPEXNOTE_SUPPORT_ADMIN_EMAIL", "support@upexflow.com").strip() or "support@upexflow.com",
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings.from_environment()
