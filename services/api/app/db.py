"""Transactional PostgreSQL repository for reset codes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import Settings


RESET_CODES_DDL = """
CREATE TABLE IF NOT EXISTS reset_codes (
    id bigserial PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    email_hash text NOT NULL,
    ip_hash text NOT NULL,
    user_id bigint REFERENCES users(id) ON DELETE CASCADE,
    code_hash text,
    expires_at timestamptz,
    attempts smallint NOT NULL DEFAULT 0,
    verified_at timestamptz,
    reset_token_hash text,
    reset_token_expires_at timestamptz,
    used_at timestamptz,
    invalidated_at timestamptz
)
"""

RESET_INDEXES = (
    "CREATE INDEX IF NOT EXISTS reset_codes_email_created_idx "
    "ON reset_codes (email_hash, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS reset_codes_ip_created_idx "
    "ON reset_codes (ip_hash, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS reset_codes_token_idx "
    "ON reset_codes (reset_token_hash) WHERE reset_token_hash IS NOT NULL",
)


@dataclass(frozen=True)
class RequestStart:
    accepted: bool
    reset_id: int | None
    user_id: int | None
    recipient: str | None


@dataclass(frozen=True)
class VerifyResult:
    ok: bool
    reason: str
    user_id: int | None = None


@dataclass(frozen=True)
class CompleteResult:
    ok: bool
    reason: str
    user_id: int | None = None


class ResetRepository(Protocol):
    def ensure_schema(self) -> None: ...

    def ping(self) -> None: ...

    def start_request(
        self,
        *,
        email: str,
        email_hash: str,
        ip_hash: str,
        code_hash: str,
        ttl_seconds: int,
        window_seconds: int,
        email_limit: int,
        ip_limit: int,
    ) -> RequestStart: ...

    def invalidate_delivery(self, reset_id: int, email: str, user_id: int) -> None: ...

    def verify_code(
        self,
        *,
        email: str,
        email_hash: str,
        code_hash: str,
        reset_token_hash: str,
        token_ttl_seconds: int,
        max_attempts: int,
    ) -> VerifyResult: ...

    def complete_reset(
        self,
        *,
        email: str,
        email_hash: str,
        reset_token_hash: str,
        password_salt: str,
        password_hash: str,
    ) -> CompleteResult: ...


class PostgresResetRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _connect(self):
        return psycopg2.connect(
            host=self.settings.db_host,
            port=self.settings.db_port,
            dbname=self.settings.db_name,
            user=self.settings.db_user,
            password=self.settings.db_password,
            connect_timeout=8,
            application_name="upexnote-api",
        )

    @staticmethod
    def _event(cur, event: str, ok: bool, email: str, user_id: int | None, detail: str) -> None:
        cur.execute(
            """INSERT INTO access_events
               (event, ok, email, user_id, detail, app_version, host)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (event, ok, email, user_id, detail, "api-0.1.0", "upexnote-api"),
        )

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(RESET_CODES_DDL)
                for statement in RESET_INDEXES:
                    cur.execute(statement)

    def ping(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")

    def start_request(
        self,
        *,
        email: str,
        email_hash: str,
        ip_hash: str,
        code_hash: str,
        ttl_seconds: int,
        window_seconds: int,
        email_limit: int,
        ip_limit: int,
    ) -> RequestStart:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # A fixed lock order prevents concurrent requests from bypassing limits.
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (email_hash,))
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 1))", (ip_hash,))
                cur.execute(
                    """SELECT
                         count(*) FILTER (WHERE email_hash = %s) AS email_count,
                         count(*) FILTER (WHERE ip_hash = %s) AS ip_count
                       FROM reset_codes
                       WHERE created_at > now() - (%s * interval '1 second')""",
                    (email_hash, ip_hash, window_seconds),
                )
                counts = cur.fetchone()
                accepted = counts["email_count"] < email_limit and counts["ip_count"] < ip_limit
                cur.execute(
                    """SELECT id, email FROM users
                       WHERE lower(email) = %s AND deleted_at IS NULL LIMIT 1""",
                    (email,),
                )
                user = cur.fetchone()
                user_id = int(user["id"]) if user else None
                stored_code_hash = code_hash if accepted and user else None
                expires_expression = "now() + (%s * interval '1 second')" if stored_code_hash else "NULL"
                params = [email_hash, ip_hash, user_id, stored_code_hash]
                if stored_code_hash:
                    params.append(ttl_seconds)
                cur.execute(
                    f"""INSERT INTO reset_codes
                        (email_hash, ip_hash, user_id, code_hash, expires_at)
                        VALUES (%s,%s,%s,%s,{expires_expression}) RETURNING id""",
                    params,
                )
                reset_id = int(cur.fetchone()["id"])
                if stored_code_hash:
                    cur.execute(
                        """UPDATE reset_codes SET invalidated_at = now()
                           WHERE user_id = %s AND id <> %s AND used_at IS NULL
                             AND invalidated_at IS NULL""",
                        (user_id, reset_id),
                    )
                detail = "accepted" if stored_code_hash else ("rate_limited" if not accepted else "account_absent")
                self._event(cur, "password_reset_requested", bool(stored_code_hash), email, user_id, detail)
                return RequestStart(
                    accepted=bool(stored_code_hash),
                    reset_id=reset_id if stored_code_hash else None,
                    user_id=user_id,
                    recipient=user["email"] if stored_code_hash else None,
                )

    def invalidate_delivery(self, reset_id: int, email: str, user_id: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE reset_codes SET invalidated_at = now() WHERE id = %s AND used_at IS NULL",
                    (reset_id,),
                )
                self._event(cur, "password_reset_failed", False, email, user_id, "delivery_failed")

    def verify_code(
        self,
        *,
        email: str,
        email_hash: str,
        code_hash: str,
        reset_token_hash: str,
        token_ttl_seconds: int,
        max_attempts: int,
    ) -> VerifyResult:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (email_hash,))
                cur.execute(
                    """SELECT id, user_id, code_hash, attempts
                       FROM reset_codes
                       WHERE email_hash = %s AND user_id IS NOT NULL
                         AND code_hash IS NOT NULL AND expires_at > now()
                         AND verified_at IS NULL AND used_at IS NULL
                         AND invalidated_at IS NULL
                       ORDER BY created_at DESC, id DESC LIMIT 1 FOR UPDATE""",
                    (email_hash,),
                )
                row = cur.fetchone()
                if not row:
                    self._event(cur, "password_reset_failed", False, email, None, "invalid_or_expired_code")
                    return VerifyResult(False, "invalid_or_expired_code")
                user_id = int(row["user_id"])
                next_attempt = int(row["attempts"]) + 1
                if row["code_hash"] != code_hash:
                    cur.execute(
                        """UPDATE reset_codes
                           SET attempts = %s,
                               invalidated_at = CASE WHEN %s >= %s THEN now() ELSE invalidated_at END
                           WHERE id = %s""",
                        (next_attempt, next_attempt, max_attempts, row["id"]),
                    )
                    reason = "attempts_exhausted" if next_attempt >= max_attempts else "invalid_code"
                    self._event(cur, "password_reset_failed", False, email, user_id, reason)
                    return VerifyResult(False, reason, user_id)
                cur.execute(
                    """UPDATE reset_codes
                       SET attempts = %s, verified_at = now(), reset_token_hash = %s,
                           reset_token_expires_at = now() + (%s * interval '1 second')
                       WHERE id = %s""",
                    (next_attempt, reset_token_hash, token_ttl_seconds, row["id"]),
                )
                return VerifyResult(True, "verified", user_id)

    def complete_reset(
        self,
        *,
        email: str,
        email_hash: str,
        reset_token_hash: str,
        password_salt: str,
        password_hash: str,
    ) -> CompleteResult:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (email_hash,))
                cur.execute(
                    """SELECT r.id, r.user_id
                       FROM reset_codes r
                       JOIN users u ON u.id = r.user_id
                       WHERE r.email_hash = %s AND r.reset_token_hash = %s
                         AND r.verified_at IS NOT NULL
                         AND r.reset_token_expires_at > now()
                         AND r.used_at IS NULL AND r.invalidated_at IS NULL
                         AND u.deleted_at IS NULL
                       ORDER BY r.created_at DESC, r.id DESC LIMIT 1 FOR UPDATE""",
                    (email_hash, reset_token_hash),
                )
                row = cur.fetchone()
                if not row:
                    self._event(cur, "password_reset_failed", False, email, None, "invalid_or_expired_token")
                    return CompleteResult(False, "invalid_or_expired_token")
                user_id = int(row["user_id"])
                cur.execute(
                    """UPDATE users
                       SET password_salt = %s, password_hash = %s, updated_at = now()
                       WHERE id = %s AND deleted_at IS NULL""",
                    (password_salt, password_hash, user_id),
                )
                if cur.rowcount != 1:
                    self._event(cur, "password_reset_failed", False, email, user_id, "account_unavailable")
                    return CompleteResult(False, "account_unavailable", user_id)
                cur.execute("UPDATE reset_codes SET used_at = now() WHERE id = %s", (row["id"],))
                cur.execute(
                    """UPDATE reset_codes SET invalidated_at = now()
                       WHERE user_id = %s AND id <> %s AND used_at IS NULL
                         AND invalidated_at IS NULL""",
                    (user_id, row["id"]),
                )
                self._event(cur, "password_reset_completed", True, email, user_id, "completed")
                return CompleteResult(True, "completed", user_id)
