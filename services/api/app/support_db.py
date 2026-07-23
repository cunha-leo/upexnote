"""Persistence for the isolated ``support`` product schema.

The tickets hub intentionally contains only the current, searchable state.
Descriptions, conversation, evidence and workflow history are satellites so a
case remains reconstructable without turning one wide table into a dumping
ground. Attachment bytes never enter PostgreSQL.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Any

import psycopg2
import psycopg2.extras

from .config import Settings


SUPPORT_DDL = """
CREATE SCHEMA IF NOT EXISTS support;

CREATE TABLE IF NOT EXISTS support.identities (
    id bigserial PRIMARY KEY,
    username text UNIQUE NOT NULL,
    email text UNIQUE NOT NULL,
    display_name text,
    role text NOT NULL DEFAULT 'customer' CHECK (role IN ('customer','support','admin','system')),
    lifecycle_state text NOT NULL DEFAULT 'active' CHECK (lifecycle_state IN ('active','cancelled')),
    credential_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now(),
    disabled_at timestamptz
);

CREATE TABLE IF NOT EXISTS support.tickets (
    id bigserial PRIMARY KEY,
    ticket_number text UNIQUE NOT NULL,
    identity_id bigint NOT NULL REFERENCES support.identities(id),
    assignee_identity_id bigint REFERENCES support.identities(id),
    status text NOT NULL DEFAULT 'open' CHECK (status IN ('open','in_progress','pending_customer','resolved','closed')),
    category text NOT NULL DEFAULT 'general',
    priority text NOT NULL DEFAULT 'normal' CHECK (priority IN ('low','normal','high')),
    subject text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now(),
    resolved_at timestamptz,
    closed_at timestamptz
);
CREATE INDEX IF NOT EXISTS tickets_queue_idx ON support.tickets(status, updated_at DESC);
CREATE INDEX IF NOT EXISTS tickets_identity_idx ON support.tickets(identity_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS tickets_assignee_idx ON support.tickets(assignee_identity_id, updated_at DESC);

CREATE TABLE IF NOT EXISTS support.ticket_metadata (
    ticket_id bigint PRIMARY KEY REFERENCES support.tickets(id) ON DELETE RESTRICT,
    captured_by_identity_id bigint REFERENCES support.identities(id),
    app_version text,
    platform text,
    locale text,
    context jsonb NOT NULL DEFAULT '{}'::jsonb,
    captured_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS support.ticket_descriptions (
    ticket_id bigint PRIMARY KEY REFERENCES support.tickets(id) ON DELETE RESTRICT,
    created_by_identity_id bigint REFERENCES support.identities(id),
    body text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS support.ticket_comments (
    id bigserial PRIMARY KEY,
    ticket_id bigint NOT NULL REFERENCES support.tickets(id) ON DELETE RESTRICT,
    author_kind text NOT NULL CHECK (author_kind IN ('customer','support','admin','system')),
    author_identity_id bigint REFERENCES support.identities(id),
    author_label text,
    body text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ticket_comments_timeline_idx ON support.ticket_comments(ticket_id, id);

CREATE TABLE IF NOT EXISTS support.ticket_attachments (
    id bigserial PRIMARY KEY,
    ticket_id bigint NOT NULL REFERENCES support.tickets(id) ON DELETE RESTRICT,
    comment_id bigint REFERENCES support.ticket_comments(id) ON DELETE RESTRICT,
    uploaded_by_identity_id bigint REFERENCES support.identities(id),
    original_filename text NOT NULL,
    stored_filename text NOT NULL,
    content_type text NOT NULL,
    byte_size bigint NOT NULL CHECK (byte_size >= 0),
    sha256 char(64) NOT NULL,
    spool_path text,
    archive_state text NOT NULL DEFAULT 'pending' CHECK (archive_state IN ('pending','archiving','archived','failed')),
    drive_path text,
    archived_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ticket_attachments_archive_idx ON support.ticket_attachments(archive_state, created_at);

CREATE TABLE IF NOT EXISTS support.ticket_status_history (
    id bigserial PRIMARY KEY,
    ticket_id bigint NOT NULL REFERENCES support.tickets(id) ON DELETE RESTRICT,
    from_status text,
    to_status text NOT NULL,
    actor_kind text NOT NULL CHECK (actor_kind IN ('customer','support','admin','system')),
    actor_identity_id bigint REFERENCES support.identities(id),
    reason text,
    changed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ticket_status_history_idx ON support.ticket_status_history(ticket_id, id);

CREATE TABLE IF NOT EXISTS support.ticket_assignments (
    id bigserial PRIMARY KEY,
    ticket_id bigint NOT NULL REFERENCES support.tickets(id) ON DELETE RESTRICT,
    assigned_by_identity_id bigint REFERENCES support.identities(id),
    assigned_to_identity_id bigint REFERENCES support.identities(id),
    assignment_state text NOT NULL DEFAULT 'assigned' CHECK (assignment_state IN ('assigned','unassigned')),
    reason text,
    assigned_at timestamptz NOT NULL DEFAULT now(),
    changed_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ticket_assignments_history_idx ON support.ticket_assignments(ticket_id, id);

CREATE TABLE IF NOT EXISTS support.ticket_notifications (
    id bigserial PRIMARY KEY,
    ticket_id bigint NOT NULL REFERENCES support.tickets(id) ON DELETE RESTRICT,
    recipient text NOT NULL,
    notification_type text NOT NULL,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    state text NOT NULL DEFAULT 'pending' CHECK (state IN ('pending','sent','failed')),
    attempts integer NOT NULL DEFAULT 0,
    last_error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    sent_at timestamptz
);
CREATE INDEX IF NOT EXISTS ticket_notifications_pending_idx ON support.ticket_notifications(state, created_at);

CREATE TABLE IF NOT EXISTS support.ticket_audit (
    id bigserial PRIMARY KEY,
    ticket_id bigint NOT NULL REFERENCES support.tickets(id) ON DELETE RESTRICT,
    action text NOT NULL,
    actor_kind text NOT NULL CHECK (actor_kind IN ('customer','support','admin','system')),
    actor_identity_id bigint REFERENCES support.identities(id),
    snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ticket_audit_timeline_idx ON support.ticket_audit(ticket_id, id);

ALTER TABLE support.identities ADD COLUMN IF NOT EXISTS username text;
ALTER TABLE support.identities ADD COLUMN IF NOT EXISTS role text NOT NULL DEFAULT 'customer';
ALTER TABLE support.identities ADD COLUMN IF NOT EXISTS lifecycle_state text NOT NULL DEFAULT 'active';
ALTER TABLE support.identities ADD COLUMN IF NOT EXISTS updated_at timestamptz NOT NULL DEFAULT now();
ALTER TABLE support.tickets ADD COLUMN IF NOT EXISTS assignee_identity_id bigint REFERENCES support.identities(id);
ALTER TABLE support.ticket_metadata ADD COLUMN IF NOT EXISTS captured_by_identity_id bigint REFERENCES support.identities(id);
ALTER TABLE support.ticket_descriptions ADD COLUMN IF NOT EXISTS created_by_identity_id bigint REFERENCES support.identities(id);
ALTER TABLE support.ticket_attachments ADD COLUMN IF NOT EXISTS uploaded_by_identity_id bigint REFERENCES support.identities(id);
"""


class PostgresSupportRepository:
    def __init__(self, settings: Settings):
        self.settings = settings

    def _connect(self):
        return psycopg2.connect(host=self.settings.db_host, port=self.settings.db_port,
            dbname=self.settings.db_name, user=self.settings.db_user,
            password=self.settings.db_password, connect_timeout=8, application_name="upexnote-api")

    def ensure_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(SUPPORT_DDL)

    @staticmethod
    def _hash(secret: str) -> str:
        return hashlib.sha256(secret.encode("utf-8")).hexdigest()

    def identity(self, *, email: str, username: str, display_name: str | None, client_secret: str) -> dict[str, Any] | None:
        """Create or resume an opaque desktop support identity.

        A device secret is generated locally and stored in the OS credential
        vault. It is neither an account password nor a database credential.
        Unknown secrets cannot claim an existing e-mail's ticket history.
        """
        digest = self._hash(client_secret)
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id, email, username, credential_hash, disabled_at FROM support.identities WHERE email=%s", (email,))
                existing = cur.fetchone()
                if existing:
                    identity_id, _, _, saved, disabled_at = existing
                    if disabled_at or not hmac.compare_digest(saved, digest):
                        return None
                    cur.execute("UPDATE support.identities SET username=%s, display_name=coalesce(%s, display_name), updated_at=now(), last_seen_at=now() WHERE id=%s", (username, display_name, identity_id))
                else:
                    cur.execute("INSERT INTO support.identities(username,email,display_name,credential_hash) VALUES (%s,%s,%s,%s) RETURNING id", (username, email, display_name, digest))
                    identity_id = cur.fetchone()[0]
        return {"id": identity_id, "email": email, "username": username, "display_name": display_name}

    def provision_staff_identity(self, *, email: str, role: str = "admin") -> dict[str, Any]:
        """Mirror an authenticated platform operator for attributable support work.

        This row is not a customer login. Its non-secret marker prevents the
        customer identity endpoint from ever resuming it.
        """
        local = email.split("@", 1)[0].lower()
        username = f"{role}.{''.join(ch for ch in local if ch.isalnum() or ch in '._-')[:60]}"
        marker = "staff:" + hashlib.sha256(email.lower().encode("utf-8")).hexdigest()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id,username,display_name FROM support.identities WHERE email=%s", (email.lower(),))
                row = cur.fetchone()
                if row:
                    identity_id, saved_username, display_name = row
                    cur.execute("UPDATE support.identities SET role=%s,lifecycle_state='active',updated_at=now(),last_seen_at=now() WHERE id=%s", (role, identity_id))
                    return {"id": identity_id, "email": email.lower(), "username": saved_username, "display_name": display_name}
                cur.execute("INSERT INTO support.identities(username,email,display_name,role,credential_hash) VALUES (%s,%s,%s,%s,%s) RETURNING id", (username, email.lower(), local, role, marker))
                identity_id = cur.fetchone()[0]
        return {"id": identity_id, "email": email.lower(), "username": username, "display_name": local}

    def create_ticket(self, identity_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as conn:
            with conn.cursor() as cur:
                # The temporary value is unique even with concurrent creates;
                # the stable, human-facing number is derived from the matrix id.
                temp_number = f"TMP-{secrets.token_hex(12)}"
                cur.execute("""INSERT INTO support.tickets(ticket_number,identity_id,category,priority,subject)
                    VALUES (%s,%s,%s,%s,%s) RETURNING id""", (temp_number, identity_id, payload["category"], payload["priority"], payload["subject"]))
                ticket_id = cur.fetchone()[0]
                number = f"UN-{ticket_id:06d}"
                cur.execute("UPDATE support.tickets SET ticket_number=%s WHERE id=%s", (number, ticket_id))
                cur.execute("INSERT INTO support.ticket_descriptions(ticket_id,created_by_identity_id,body) VALUES (%s,%s,%s)", (ticket_id, identity_id, payload["body"]))
                cur.execute("INSERT INTO support.ticket_metadata(ticket_id,captured_by_identity_id,app_version,platform,locale,context) VALUES (%s,%s,%s,%s,%s,%s)",
                            (ticket_id, identity_id, payload.get("app_version"), payload.get("platform"), payload.get("locale"), psycopg2.extras.Json(payload.get("context") or {})))
                cur.execute("INSERT INTO support.ticket_status_history(ticket_id,to_status,actor_kind,actor_identity_id,reason) VALUES (%s,'open','customer',%s,'ticket_created')", (ticket_id, identity_id))
                self._audit(cur, ticket_id, "ticket_created", "customer", identity_id, {"ticket_number": number})
                cur.execute("SELECT email FROM support.identities WHERE id=%s", (identity_id,))
                recipient = cur.fetchone()[0]
                cur.execute("INSERT INTO support.ticket_notifications(ticket_id,recipient,notification_type,payload) VALUES (%s,%s,'ticket_received',%s)",
                            (ticket_id, recipient, psycopg2.extras.Json({"ticket_number": number, "subject": payload["subject"]})))
        return {"id": ticket_id, "ticket_number": number, "status": "open"}

    def queue_notification(self, ticket_id: int, recipient: str, notification_type: str, payload: dict[str, Any]) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("INSERT INTO support.ticket_notifications(ticket_id,recipient,notification_type,payload) VALUES (%s,%s,%s,%s)", (ticket_id, recipient, notification_type, psycopg2.extras.Json(payload)))

    def pending_notifications(self, ticket_id: int) -> list[dict[str, Any]]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id,recipient,notification_type,payload FROM support.ticket_notifications WHERE ticket_id=%s AND state='pending' ORDER BY id", (ticket_id,))
                return [dict(row) for row in cur.fetchall()]

    def complete_notification(self, notification_id: int, error: str | None = None) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE support.ticket_notifications SET attempts=attempts+1,state=%s,sent_at=CASE WHEN %s IS NULL THEN now() ELSE sent_at END,last_error=%s WHERE id=%s", ("sent" if error is None else "failed", error, error, notification_id))

    def list_tickets(self, identity_id: int | None = None, *, status: str | None = None) -> list[dict[str, Any]]:
        where, params = [], []
        if identity_id is not None:
            where.append("t.identity_id=%s"); params.append(identity_id)
        if status:
            where.append("t.status=%s"); params.append(status)
        clause = (" WHERE " + " AND ".join(where)) if where else ""
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""SELECT t.id,t.ticket_number,t.status,t.category,t.priority,t.subject,t.created_at,t.updated_at,
                    i.email,i.display_name,(SELECT count(*) FROM support.ticket_comments c WHERE c.ticket_id=t.id) AS comments,
                    (SELECT count(*) FROM support.ticket_attachments a WHERE a.ticket_id=t.id) AS attachments
                    FROM support.tickets t JOIN support.identities i ON i.id=t.identity_id""" + clause + " ORDER BY t.updated_at DESC", params)
                return [dict(row) for row in cur.fetchall()]

    def ticket_detail(self, ticket_id: int, identity_id: int | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                owner_clause, params = (" AND t.identity_id=%s", [ticket_id, identity_id]) if identity_id is not None else ("", [ticket_id])
                cur.execute("""SELECT t.*,i.email,i.display_name,d.body AS description,m.app_version,m.platform,m.locale,m.context
                    FROM support.tickets t JOIN support.identities i ON i.id=t.identity_id
                    JOIN support.ticket_descriptions d ON d.ticket_id=t.id
                    LEFT JOIN support.ticket_metadata m ON m.ticket_id=t.id WHERE t.id=%s""" + owner_clause, params)
                ticket = cur.fetchone()
                if not ticket:
                    return None
                cur.execute("SELECT id,author_kind,author_label,body,created_at FROM support.ticket_comments WHERE ticket_id=%s ORDER BY id", (ticket_id,))
                comments = [dict(row) for row in cur.fetchall()]
                cur.execute("SELECT id,original_filename,content_type,byte_size,sha256,archive_state,drive_path,created_at FROM support.ticket_attachments WHERE ticket_id=%s ORDER BY id", (ticket_id,))
                attachments = [dict(row) for row in cur.fetchall()]
                cur.execute("SELECT from_status,to_status,actor_kind,reason,changed_at FROM support.ticket_status_history WHERE ticket_id=%s ORDER BY id", (ticket_id,))
                history = [dict(row) for row in cur.fetchall()]
        result = dict(ticket); result.update(comments=comments, attachments=attachments, status_history=history)
        return result

    def add_comment(self, ticket_id: int, *, body: str, author_kind: str, author_identity_id: int | None, author_label: str | None) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                if author_kind == "customer":
                    cur.execute("SELECT id FROM support.tickets WHERE id=%s AND identity_id=%s", (ticket_id, author_identity_id))
                    if not cur.fetchone(): return None
                else:
                    cur.execute("SELECT id FROM support.tickets WHERE id=%s", (ticket_id,))
                    if not cur.fetchone(): return None
                cur.execute("INSERT INTO support.ticket_comments(ticket_id,author_kind,author_identity_id,author_label,body) VALUES (%s,%s,%s,%s,%s) RETURNING id,author_kind,author_label,body,created_at", (ticket_id, author_kind, author_identity_id, author_label, body))
                comment = dict(cur.fetchone())
                cur.execute("UPDATE support.tickets SET updated_at=now() WHERE id=%s", (ticket_id,))
                self._audit(cur, ticket_id, "comment_added", author_kind, author_identity_id, {"comment_id": comment["id"]})
        return comment

    def transition_status(self, ticket_id: int, *, to_status: str, actor_kind: str, actor_identity_id: int | None, reason: str | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT status FROM support.tickets WHERE id=%s FOR UPDATE", (ticket_id,))
                row = cur.fetchone()
                if not row: return None
                previous = row["status"]
                cur.execute("""UPDATE support.tickets SET status=%s, updated_at=now(),
                    resolved_at=CASE WHEN %s='resolved' THEN now() ELSE resolved_at END,
                    closed_at=CASE WHEN %s='closed' THEN now() ELSE closed_at END WHERE id=%s""", (to_status, to_status, to_status, ticket_id))
                cur.execute("INSERT INTO support.ticket_status_history(ticket_id,from_status,to_status,actor_kind,actor_identity_id,reason) VALUES (%s,%s,%s,%s,%s,%s)", (ticket_id, previous, to_status, actor_kind, actor_identity_id, reason))
                self._audit(cur, ticket_id, "status_changed", actor_kind, actor_identity_id, {"from": previous, "to": to_status, "reason": reason})
        return {"id": ticket_id, "status": to_status}

    def assign_ticket(self, ticket_id: int, *, assignee_identity_id: int | None, assigned_by_identity_id: int, reason: str | None = None) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id FROM support.tickets WHERE id=%s FOR UPDATE", (ticket_id,))
                if not cur.fetchone(): return None
                cur.execute("UPDATE support.tickets SET assignee_identity_id=%s, updated_at=now() WHERE id=%s", (assignee_identity_id, ticket_id))
                state = "assigned" if assignee_identity_id else "unassigned"
                cur.execute("INSERT INTO support.ticket_assignments(ticket_id,assigned_by_identity_id,assigned_to_identity_id,assignment_state,reason) VALUES (%s,%s,%s,%s,%s)", (ticket_id, assigned_by_identity_id, assignee_identity_id, state, reason))
                self._audit(cur, ticket_id, "ticket_assigned", "admin", assigned_by_identity_id, {"assignee_identity_id": assignee_identity_id, "reason": reason})
        return {"id": ticket_id, "assignee_identity_id": assignee_identity_id}

    def add_attachment(self, ticket_id: int, *, identity_id: int, original_filename: str, stored_filename: str, content_type: str, byte_size: int, sha256: str, spool_path: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("SELECT id FROM support.tickets WHERE id=%s AND identity_id=%s", (ticket_id, identity_id))
                if not cur.fetchone(): return None
                cur.execute("""INSERT INTO support.ticket_attachments(ticket_id,uploaded_by_identity_id,original_filename,stored_filename,content_type,byte_size,sha256,spool_path)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id,original_filename,content_type,byte_size,sha256,archive_state,created_at""",
                    (ticket_id, identity_id, original_filename, stored_filename, content_type, byte_size, sha256, spool_path))
                item = dict(cur.fetchone())
                cur.execute("UPDATE support.tickets SET updated_at=now() WHERE id=%s", (ticket_id,))
                self._audit(cur, ticket_id, "attachment_added", "customer", identity_id, {"attachment_id": item["id"], "sha256": sha256})
        return item

    @staticmethod
    def _audit(cur, ticket_id: int, action: str, actor_kind: str, actor_id: int | None, snapshot: dict[str, Any]) -> None:
        cur.execute("INSERT INTO support.ticket_audit(ticket_id,action,actor_kind,actor_identity_id,snapshot) VALUES (%s,%s,%s,%s,%s)",
                    (ticket_id, action, actor_kind, actor_id, psycopg2.extras.Json(snapshot)))
