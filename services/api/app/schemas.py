"""Versioned public request and response contracts."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .security import normalize_email


_EMAIL = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class EmailPayload(StrictModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value: str) -> str:
        normalized = normalize_email(value)
        if not _EMAIL.fullmatch(normalized):
            raise ValueError("invalid email address")
        return normalized


class ResetRequest(EmailPayload):
    pass


class ResetVerify(EmailPayload):
    code: str = Field(pattern=r"^\d{6}$")


class ResetComplete(EmailPayload):
    reset_token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=8, max_length=256)


class GenericAccepted(StrictModel):
    ok: bool = True
    message: str


class ResetVerified(StrictModel):
    ok: bool = True
    reset_token: str
    expires_in: int


class ResetCompleted(StrictModel):
    ok: bool = True


class AdminChallenge(EmailPayload):
    admin_secret: str = Field(min_length=1, max_length=512)
    prefer_email: bool = False


class AdminVerify(EmailPayload):
    code: str = Field(pattern=r"^\d{6}$")


class AdminTokenPayload(EmailPayload):
    elevation_token: str = Field(min_length=32, max_length=256)


class AdminTotpConfirm(AdminTokenPayload):
    code: str = Field(pattern=r"^\d{6}$")


class AdminChallengeAccepted(GenericAccepted):
    factor: str


class AdminVerified(StrictModel):
    ok: bool = True
    elevation_token: str
    expires_in: int
    factor: str
    totp_enrolled: bool


class AdminValidation(StrictModel):
    ok: bool = True
    valid: bool
    user_id: int | None = None
    expires_in: int | None = None
    totp_enrolled: bool = False


class AdminRevoked(StrictModel):
    ok: bool = True


class AdminTotpEnrollment(StrictModel):
    ok: bool = True
    qr_data_url: str
    manual_key: str
    expires_in: int


class AdminTotpConfirmed(StrictModel):
    ok: bool = True


class SkeletonResponse(StrictModel):
    detail: str = "Not implemented in this release"


class TelemetryEvent(StrictModel):
    """Privacy-preserving operational event; no user content is accepted."""

    installation_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    consent: bool
    event: str = Field(pattern=r"^(app_started|transcription_completed|transcription_failed|login_succeeded|login_failed)$")
    app_version: str = Field(min_length=1, max_length=64)
    engine: str | None = Field(default=None, max_length=64)
    duration_seconds: int | None = Field(default=None, ge=0, le=172800)
    estimated_cost_micros: int | None = Field(default=None, ge=0, le=10_000_000_000)
    region: str | None = Field(default=None, pattern=r"^[A-Z]{2}$")
    error_code: str | None = Field(default=None, pattern=r"^[A-Z0-9_:-]{1,96}$")


class TelemetryAccepted(StrictModel):
    ok: bool = True


class InstallationTokenExchange(StrictModel):
    installation_id: str = Field(pattern=r"^[a-f0-9-]{36}$")
    consent: bool
    app_version: str = Field(min_length=1, max_length=64)


class InstallationToken(StrictModel):
    access_token: str
    expires_in: int
