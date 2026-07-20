"""Transactional persistence for administrative MFA sessions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import psycopg2
from psycopg2.extras import RealDictCursor

from .config import Settings
from .security import decrypt_totp_secret, verify_totp


ADMIN_MFA_DDL = """
CREATE TABLE IF NOT EXISTS admin_mfa (
    user_id bigint PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    totp_secret_encrypted text,
    totp_enabled_at timestamptz,
    totp_pending_encrypted text,
    totp_pending_expires_at timestamptz,
    totp_pending_attempts smallint NOT NULL DEFAULT 0,
    updated_at timestamptz NOT NULL DEFAULT now()
)
"""

ADMIN_CODES_DDL = """
CREATE TABLE IF NOT EXISTS admin_elevation_codes (
    id bigserial PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now(),
    email_hash text NOT NULL,
    ip_hash text NOT NULL,
    user_id bigint REFERENCES users(id) ON DELETE CASCADE,
    factor text NOT NULL,
    code_hash text,
    expires_at timestamptz,
    attempts smallint NOT NULL DEFAULT 0,
    verified_at timestamptz,
    session_token_hash text,
    session_expires_at timestamptz,
    last_validated_at timestamptz,
    revoked_at timestamptz,
    invalidated_at timestamptz
)
"""

ADMIN_INDEXES = (
    "CREATE INDEX IF NOT EXISTS admin_elevation_email_created_idx "
    "ON admin_elevation_codes (email_hash, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS admin_elevation_ip_created_idx "
    "ON admin_elevation_codes (ip_hash, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS admin_elevation_session_idx "
    "ON admin_elevation_codes (session_token_hash) WHERE session_token_hash IS NOT NULL",
)


@dataclass(frozen=True)
class ChallengeStart:
    accepted: bool
    challenge_id: int | None
    user_id: int | None
    recipient: str | None
    factor: str


@dataclass(frozen=True)
class FactorVerification:
    ok: bool
    reason: str
    user_id: int | None = None
    factor: str = "email"
    totp_enrolled: bool = False


@dataclass(frozen=True)
class SessionValidation:
    valid: bool
    user_id: int | None = None
    expires_in: int | None = None
    totp_enrolled: bool = False


class AdminElevationRepository(Protocol):
    def ensure_schema(self) -> None: ...
    def start_challenge(self, **kwargs) -> ChallengeStart: ...
    def invalidate_delivery(self, challenge_id: int, email: str, user_id: int) -> None: ...
    def verify_factor(self, **kwargs) -> FactorVerification: ...
    def validate_session(self, **kwargs) -> SessionValidation: ...
    def revoke_session(self, **kwargs) -> None: ...
    def begin_totp_enrollment(self, **kwargs) -> bool: ...
    def confirm_totp_enrollment(self, **kwargs) -> bool: ...


class PostgresAdminElevationRepository:
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
            (event, ok, email, user_id, detail, "api-0.2.0", "upexnote-api"),
        )

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(ADMIN_MFA_DDL)
                cur.execute(ADMIN_CODES_DDL)
                for statement in ADMIN_INDEXES:
                    cur.execute(statement)

    def start_challenge(
        self,
        *,
        email: str,
        email_hash: str,
        ip_hash: str,
        code_hash: str,
        credential_ok: bool,
        prefer_email: bool,
        ttl_seconds: int,
        window_seconds: int,
        email_limit: int,
        ip_limit: int,
    ) -> ChallengeStart:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 20))", (email_hash,))
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 21))", (ip_hash,))
                cur.execute(
                    """SELECT
                         count(*) FILTER (WHERE email_hash = %s) AS email_count,
                         count(*) FILTER (WHERE ip_hash = %s) AS ip_count
                       FROM admin_elevation_codes
                       WHERE created_at > now() - (%s * interval '1 second')""",
                    (email_hash, ip_hash, window_seconds),
                )
                counts = cur.fetchone()
                within_rate = counts["email_count"] < email_limit and counts["ip_count"] < ip_limit
                cur.execute(
                    """SELECT u.id, u.email, u.role, m.totp_enabled_at
                       FROM users u LEFT JOIN admin_mfa m ON m.user_id = u.id
                       WHERE lower(u.email) = %s AND u.deleted_at IS NULL LIMIT 1""",
                    (email,),
                )
                user = cur.fetchone()
                eligible = bool(
                    credential_ok and within_rate and user
                    and (user["role"] or "").lower() == "admin"
                )
                factor = "totp" if eligible and user["totp_enabled_at"] and not prefer_email else "email"
                stored_code_hash = code_hash if eligible and factor == "email" else None
                stored_user_id = int(user["id"]) if eligible else None
                cur.execute(
                    """INSERT INTO admin_elevation_codes
                       (email_hash, ip_hash, user_id, factor, code_hash, expires_at)
                       VALUES (%s,%s,%s,%s,%s,
                         CASE WHEN %s THEN now() + (%s * interval '1 second') ELSE NULL END)
                       RETURNING id""",
                    (email_hash, ip_hash, stored_user_id, factor, stored_code_hash,
                     eligible, ttl_seconds),
                )
                challenge_id = int(cur.fetchone()["id"])
                if eligible:
                    cur.execute(
                        """UPDATE admin_elevation_codes SET invalidated_at = now()
                           WHERE user_id = %s AND id <> %s AND verified_at IS NULL
                             AND invalidated_at IS NULL""",
                        (stored_user_id, challenge_id),
                    )
                detail = factor if eligible else (
                    "rate_limited" if not within_rate else
                    "invalid_admin_credentials" if not credential_ok else "account_ineligible"
                )
                self._event(cur, "admin_mfa_requested", eligible, email,
                            int(user["id"]) if user else None, detail)
                return ChallengeStart(
                    accepted=eligible,
                    challenge_id=challenge_id if eligible else None,
                    user_id=stored_user_id,
                    recipient=user["email"] if eligible and factor == "email" else None,
                    factor=factor,
                )

    def invalidate_delivery(self, challenge_id: int, email: str, user_id: int) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE admin_elevation_codes SET invalidated_at = now() WHERE id = %s",
                    (challenge_id,),
                )
                self._event(cur, "admin_mfa_failed", False, email, user_id, "delivery_failed")

    def verify_factor(
        self,
        *,
        email: str,
        email_hash: str,
        code: str,
        email_code_hash: str,
        session_token_hash: str,
        session_ttl_seconds: int,
        max_attempts: int,
    ) -> FactorVerification:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 20))", (email_hash,))
                cur.execute(
                    """SELECT c.id, c.user_id, c.factor, c.code_hash, c.attempts,
                              m.totp_secret_encrypted, m.totp_enabled_at
                       FROM admin_elevation_codes c
                       JOIN users u ON u.id = c.user_id
                       LEFT JOIN admin_mfa m ON m.user_id = c.user_id
                       WHERE c.email_hash = %s AND c.expires_at > now()
                         AND c.verified_at IS NULL AND c.revoked_at IS NULL
                         AND c.invalidated_at IS NULL
                         AND u.deleted_at IS NULL AND lower(u.role) = 'admin'
                       ORDER BY c.created_at DESC, c.id DESC LIMIT 1 FOR UPDATE OF c""",
                    (email_hash,),
                )
                row = cur.fetchone()
                if not row:
                    self._event(cur, "admin_mfa_failed", False, email, None, "invalid_or_expired_code")
                    return FactorVerification(False, "invalid_or_expired_code")
                user_id = int(row["user_id"])
                factor = row["factor"]
                matched = row["code_hash"] == email_code_hash if factor == "email" else False
                if factor == "totp" and row["totp_secret_encrypted"] and row["totp_enabled_at"]:
                    try:
                        secret = decrypt_totp_secret(
                            row["totp_secret_encrypted"], self.settings.reset_hmac_secret
                        )
                        matched = verify_totp(secret, code)
                    except ValueError:
                        matched = False
                next_attempt = int(row["attempts"]) + 1
                if not matched:
                    cur.execute(
                        """UPDATE admin_elevation_codes
                           SET attempts = %s,
                               invalidated_at = CASE WHEN %s >= %s THEN now() ELSE invalidated_at END
                           WHERE id = %s""",
                        (next_attempt, next_attempt, max_attempts, row["id"]),
                    )
                    reason = "attempts_exhausted" if next_attempt >= max_attempts else "invalid_code"
                    self._event(cur, "admin_mfa_failed", False, email, user_id, reason)
                    return FactorVerification(False, reason, user_id, factor, bool(row["totp_enabled_at"]))
                cur.execute(
                    """UPDATE admin_elevation_codes
                       SET attempts = %s, verified_at = now(), session_token_hash = %s,
                           session_expires_at = now() + (%s * interval '1 second')
                       WHERE id = %s""",
                    (next_attempt, session_token_hash, session_ttl_seconds, row["id"]),
                )
                self._event(cur, "admin_mfa_completed", True, email, user_id, factor)
                return FactorVerification(True, "verified", user_id, factor, bool(row["totp_enabled_at"]))

    def validate_session(self, *, email_hash: str, session_token_hash: str) -> SessionValidation:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT c.id, c.user_id, m.totp_enabled_at,
                              greatest(0, floor(extract(epoch FROM (c.session_expires_at - now()))))::int AS expires_in
                       FROM admin_elevation_codes c
                       JOIN users u ON u.id = c.user_id
                       LEFT JOIN admin_mfa m ON m.user_id = c.user_id
                       WHERE c.email_hash = %s AND c.session_token_hash = %s
                         AND c.verified_at IS NOT NULL AND c.session_expires_at > now()
                         AND c.revoked_at IS NULL AND c.invalidated_at IS NULL
                         AND u.deleted_at IS NULL AND lower(u.role) = 'admin'
                       ORDER BY c.verified_at DESC LIMIT 1 FOR UPDATE OF c""",
                    (email_hash, session_token_hash),
                )
                row = cur.fetchone()
                if not row:
                    return SessionValidation(False)
                cur.execute(
                    "UPDATE admin_elevation_codes SET last_validated_at = now() WHERE id = %s",
                    (row["id"],),
                )
                return SessionValidation(
                    True, int(row["user_id"]), int(row["expires_in"]),
                    bool(row["totp_enabled_at"]),
                )

    def revoke_session(self, *, email: str, email_hash: str, session_token_hash: str) -> None:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """UPDATE admin_elevation_codes SET revoked_at = now()
                       WHERE email_hash = %s AND session_token_hash = %s
                         AND revoked_at IS NULL RETURNING user_id""",
                    (email_hash, session_token_hash),
                )
                row = cur.fetchone()
                if row:
                    self._event(cur, "admin_mfa_revoked", True, email, int(row["user_id"]), "logout")

    def begin_totp_enrollment(
        self,
        *,
        email_hash: str,
        session_token_hash: str,
        encrypted_secret: str,
        ttl_seconds: int,
    ) -> bool:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT c.user_id FROM admin_elevation_codes c
                       JOIN users u ON u.id = c.user_id
                       WHERE c.email_hash = %s AND c.session_token_hash = %s
                         AND c.session_expires_at > now() AND c.revoked_at IS NULL
                         AND c.invalidated_at IS NULL AND u.deleted_at IS NULL
                         AND lower(u.role) = 'admin' LIMIT 1""",
                    (email_hash, session_token_hash),
                )
                row = cur.fetchone()
                if not row:
                    return False
                cur.execute(
                    """INSERT INTO admin_mfa
                       (user_id, totp_pending_encrypted, totp_pending_expires_at,
                        totp_pending_attempts, updated_at)
                       VALUES (%s,%s,now() + (%s * interval '1 second'),0,now())
                       ON CONFLICT (user_id) DO UPDATE SET
                         totp_pending_encrypted = EXCLUDED.totp_pending_encrypted,
                         totp_pending_expires_at = EXCLUDED.totp_pending_expires_at,
                         totp_pending_attempts = 0, updated_at = now()""",
                    (int(row["user_id"]), encrypted_secret, ttl_seconds),
                )
                return True

    def confirm_totp_enrollment(
        self,
        *,
        email: str,
        email_hash: str,
        session_token_hash: str,
        code: str,
        max_attempts: int,
    ) -> bool:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT c.user_id, m.totp_pending_encrypted, m.totp_pending_attempts
                       FROM admin_elevation_codes c
                       JOIN users u ON u.id = c.user_id
                       JOIN admin_mfa m ON m.user_id = c.user_id
                       WHERE c.email_hash = %s AND c.session_token_hash = %s
                         AND c.session_expires_at > now() AND c.revoked_at IS NULL
                         AND c.invalidated_at IS NULL AND u.deleted_at IS NULL
                         AND lower(u.role) = 'admin'
                         AND m.totp_pending_expires_at > now()
                         AND m.totp_pending_encrypted IS NOT NULL
                       LIMIT 1 FOR UPDATE OF m""",
                    (email_hash, session_token_hash),
                )
                row = cur.fetchone()
                if not row:
                    return False
                user_id = int(row["user_id"])
                try:
                    secret = decrypt_totp_secret(
                        row["totp_pending_encrypted"], self.settings.reset_hmac_secret
                    )
                    matched = verify_totp(secret, code)
                except ValueError:
                    matched = False
                attempts = int(row["totp_pending_attempts"]) + 1
                if not matched:
                    cur.execute(
                        """UPDATE admin_mfa SET totp_pending_attempts = %s,
                           totp_pending_encrypted = CASE WHEN %s >= %s THEN NULL ELSE totp_pending_encrypted END,
                           totp_pending_expires_at = CASE WHEN %s >= %s THEN NULL ELSE totp_pending_expires_at END,
                           updated_at = now() WHERE user_id = %s""",
                        (attempts, attempts, max_attempts, attempts, max_attempts, user_id),
                    )
                    self._event(cur, "admin_totp_enrollment_failed", False, email, user_id, "invalid_code")
                    return False
                cur.execute(
                    """UPDATE admin_mfa SET
                         totp_secret_encrypted = totp_pending_encrypted,
                         totp_enabled_at = now(), totp_pending_encrypted = NULL,
                         totp_pending_expires_at = NULL, totp_pending_attempts = 0,
                         updated_at = now() WHERE user_id = %s""",
                    (user_id,),
                )
                self._event(cur, "admin_totp_enrolled", True, email, user_id, "confirmed")
                return True
