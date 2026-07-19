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


class SkeletonResponse(StrictModel):
    detail: str = "Not implemented in this release"
