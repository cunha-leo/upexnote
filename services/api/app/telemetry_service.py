"""Privacy-preserving installation telemetry."""

from __future__ import annotations

from typing import Protocol

from .config import Settings
from .schemas import TelemetryEvent
from .security import keyed_hash


class TelemetryRepository(Protocol):
    def ensure_schema(self) -> None: ...
    def ingest(self, *, installation_hash: str, payload: TelemetryEvent) -> None: ...


class TelemetryService:
    def __init__(self, settings: Settings, repository: TelemetryRepository):
        self.settings = settings
        self.repository = repository

    def ensure_schema(self) -> None:
        self.repository.ensure_schema()

    def ingest(self, payload: TelemetryEvent) -> None:
        # An installation that has not opted in is intentionally invisible.
        if not payload.consent:
            return
        self.repository.ingest(
            installation_hash=keyed_hash(
                payload.installation_id, self.settings.reset_hmac_secret, "telemetry-installation"
            ),
            payload=payload,
        )
