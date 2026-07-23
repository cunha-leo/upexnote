"""Opaque installation tokens for privacy-preserving API calls."""
from __future__ import annotations
from typing import Protocol
from .config import Settings
from .security import generate_reset_token, keyed_hash

INSTALLATION_TOKEN_TTL_SECONDS = 90 * 24 * 60 * 60

class TokenRepository(Protocol):
    def ensure_schema(self) -> None: ...
    def issue(self, *, installation_hash: str, token_hash: str, ttl_seconds: int) -> None: ...
    def valid(self, *, installation_hash: str, token_hash: str) -> bool: ...

class InstallationTokenService:
    def __init__(self, settings: Settings, repository: TokenRepository): self.settings, self.repository = settings, repository
    def ensure_schema(self) -> None: self.repository.ensure_schema()
    def exchange(self, installation_id: str) -> tuple[str, int]:
        token = generate_reset_token()
        self.repository.issue(installation_hash=keyed_hash(installation_id, self.settings.reset_hmac_secret, "telemetry-installation"), token_hash=keyed_hash(token, self.settings.reset_hmac_secret, "telemetry-token"), ttl_seconds=INSTALLATION_TOKEN_TTL_SECONDS)
        return token, INSTALLATION_TOKEN_TTL_SECONDS
    def valid(self, installation_id: str, token: str) -> bool:
        return self.repository.valid(installation_hash=keyed_hash(installation_id, self.settings.reset_hmac_secret, "telemetry-installation"), token_hash=keyed_hash(token, self.settings.reset_hmac_secret, "telemetry-token"))
