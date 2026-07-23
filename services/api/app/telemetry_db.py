"""PostgreSQL persistence for content-free installation telemetry."""

from __future__ import annotations

import psycopg2

from .config import Settings
from .schemas import TelemetryEvent


TELEMETRY_DDL = """
CREATE TABLE IF NOT EXISTS telemetry_installations (
    installation_hash text PRIMARY KEY,
    consented_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    app_version text NOT NULL,
    region char(2)
);
CREATE TABLE IF NOT EXISTS telemetry_events (
    id bigserial PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    installation_hash text NOT NULL REFERENCES telemetry_installations(installation_hash) ON DELETE CASCADE,
    event text NOT NULL,
    app_version text NOT NULL,
    engine text,
    duration_seconds integer,
    estimated_cost_micros bigint,
    region char(2),
    error_code text
);
CREATE INDEX IF NOT EXISTS telemetry_events_created_idx ON telemetry_events (created_at DESC);
"""


class PostgresTelemetryRepository:
    def __init__(self, settings: Settings): self.settings = settings

    def _connect(self):
        return psycopg2.connect(host=self.settings.db_host, port=self.settings.db_port,
            dbname=self.settings.db_name, user=self.settings.db_user,
            password=self.settings.db_password, connect_timeout=8, application_name="upexnote-api")

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur: cur.execute(TELEMETRY_DDL)

    def ingest(self, *, installation_hash: str, payload: TelemetryEvent) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""INSERT INTO telemetry_installations (installation_hash, app_version, region)
                    VALUES (%s,%s,%s) ON CONFLICT (installation_hash) DO UPDATE SET
                    last_seen_at=now(), app_version=EXCLUDED.app_version, region=EXCLUDED.region""",
                    (installation_hash, payload.app_version, payload.region))
                cur.execute("""INSERT INTO telemetry_events
                    (installation_hash,event,app_version,engine,duration_seconds,estimated_cost_micros,region,error_code)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (installation_hash, payload.event, payload.app_version, payload.engine,
                     payload.duration_seconds, payload.estimated_cost_micros, payload.region, payload.error_code))
