"""FastAPI dependency factories."""

from __future__ import annotations

from functools import lru_cache

from .config import get_settings
from .db import PostgresResetRepository
from .emailer import SmtpResetMailer
from .service import PasswordResetService


@lru_cache(maxsize=1)
def get_reset_service() -> PasswordResetService:
    settings = get_settings()
    return PasswordResetService(
        settings,
        PostgresResetRepository(settings),
        SmtpResetMailer(settings),
    )
