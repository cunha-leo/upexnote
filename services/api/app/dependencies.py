"""FastAPI dependency factories."""

from __future__ import annotations

from functools import lru_cache

from .config import get_settings
from .admin_db import PostgresAdminElevationRepository
from .admin_service import AdminElevationService
from .db import PostgresResetRepository
from .emailer import SmtpResetMailer
from .service import PasswordResetService
from .telemetry_db import PostgresTelemetryRepository
from .telemetry_service import TelemetryService
from .token_db import PostgresTokenRepository
from .token_service import InstallationTokenService
from .support_db import PostgresSupportRepository


@lru_cache(maxsize=1)
def get_reset_service() -> PasswordResetService:
    settings = get_settings()
    return PasswordResetService(
        settings,
        PostgresResetRepository(settings),
        SmtpResetMailer(settings),
    )


@lru_cache(maxsize=1)
def get_admin_elevation_service() -> AdminElevationService:
    settings = get_settings()
    return AdminElevationService(
        settings,
        PostgresAdminElevationRepository(settings),
        SmtpResetMailer(settings),
    )


@lru_cache(maxsize=1)
def get_telemetry_service() -> TelemetryService:
    settings = get_settings()
    return TelemetryService(settings, PostgresTelemetryRepository(settings))

@lru_cache(maxsize=1)
def get_installation_token_service() -> InstallationTokenService:
    settings = get_settings()
    return InstallationTokenService(settings, PostgresTokenRepository(settings))


@lru_cache(maxsize=1)
def get_support_repository() -> PostgresSupportRepository:
    """The support schema is deliberately independent from API public tables."""
    return PostgresSupportRepository(get_settings())
