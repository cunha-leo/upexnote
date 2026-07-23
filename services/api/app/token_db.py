from __future__ import annotations
import psycopg2
from .config import Settings

DDL = """CREATE TABLE IF NOT EXISTS installation_tokens (token_hash text PRIMARY KEY, installation_hash text NOT NULL, created_at timestamptz NOT NULL DEFAULT now(), expires_at timestamptz NOT NULL, revoked_at timestamptz); CREATE INDEX IF NOT EXISTS installation_tokens_installation_idx ON installation_tokens (installation_hash);"""
class PostgresTokenRepository:
    def __init__(self, settings: Settings): self.settings = settings
    def _connect(self): return psycopg2.connect(host=self.settings.db_host, port=self.settings.db_port, dbname=self.settings.db_name, user=self.settings.db_user, password=self.settings.db_password, connect_timeout=8, application_name="upexnote-api")
    def ensure_schema(self):
        with self._connect() as conn:
            with conn.cursor() as cur: cur.execute(DDL)
    def issue(self, *, installation_hash: str, token_hash: str, ttl_seconds: int):
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE installation_tokens SET revoked_at=now() WHERE installation_hash=%s AND revoked_at IS NULL", (installation_hash,))
                cur.execute("INSERT INTO installation_tokens (token_hash,installation_hash,expires_at) VALUES (%s,%s,now() + (%s * interval '1 second'))", (token_hash, installation_hash, ttl_seconds))
    def valid(self, *, installation_hash: str, token_hash: str) -> bool:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1 FROM installation_tokens WHERE installation_hash=%s AND token_hash=%s AND revoked_at IS NULL AND expires_at>now()", (installation_hash, token_hash)); return cur.fetchone() is not None
