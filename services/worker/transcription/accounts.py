"""
Identidade do UpexNote (item 13-C, 2026-07-18) — tabela `users` no banco do
modo ativo (SQLite local / Postgres VPS) + operações de conta.

Regras de produto (especificação do utilizador):
- A tabela regista COMO a pessoa entrou (auth_provider + escopos concedidos).
- `user_id` (username público) é ÚNICO, com verificação de disponibilidade e
  sugestões quando ocupado.
- Senha NUNCA em claro: PBKDF2-HMAC-SHA256 (120k iterações, salt aleatório);
  contas OAuth têm hash NULL.
- Admin NÃO é perfil de cadastro — é elevação por segundo fator (posse das
  credenciais do banco/VPS), tratada fora desta tabela.
- Telefone é campo de perfil; autenticação por SMS foi descartada (custo).
"""
import hashlib
import json
import re
import secrets

from . import db

# O DDL vive no db.py (o hub transcriptions referencia users(id) — a ordem
# de criação importa); este alias mantém compatibilidade.
USERS_DDL = db.USERS_DDL

_USER_COLS = ("id", "user_id", "email", "first_name", "last_name", "phone",
              "auth_provider", "role", "created_at", "last_login_at")


def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"),
                               bytes.fromhex(salt), 120_000).hex()


def _ensure(conn):
    # Schema COMPLETO (não só a users): as migrações de colunas (ex.:
    # users.deleted_at) vivem no ensure_schema — só criar a tabela deixava
    # bases antigas sem as colunas novas (bug real: login local, 2026-07-19).
    # Custa pouco: o ensure corre uma vez por processo/modo.
    db.ensure_schema(conn)


def _public(row_dict):
    """Nunca devolver salt/hash/provider_id para fora do worker."""
    out = {k: row_dict.get(k) for k in _USER_COLS}
    out["created_at"] = db._iso(out.get("created_at"))
    out["last_login_at"] = db._iso(out.get("last_login_at"))
    return out


def _fetch_user(cur, where_sql, params):
    cur.execute(f"SELECT * FROM users {where_sql}", params)
    rows = cur.fetchall()
    if not rows:
        return None
    cols = [c[0] for c in cur.description]
    return dict(zip(cols, rows[0]))


def _normalize_user_id(base: str) -> str:
    s = re.sub(r"[^a-z0-9._-]", "", (base or "").lower().replace(" ", ""))
    return s[:32] or "user"


def suggest_user_id(base: str):
    """Disponibilidade + sugestões (padrão de app moderna)."""
    conn = db.connect()
    try:
        _ensure(conn)
        wanted = _normalize_user_id(base)
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users WHERE user_id LIKE %s", (wanted + "%",))
            taken = {r[0] for r in cur.fetchall()}
        if wanted not in taken:
            return {"available": True, "user_id": wanted, "suggestions": []}
        suggestions = []
        for cand in [f"{wanted}{n}" for n in range(1, 100)]:
            if cand not in taken:
                suggestions.append(cand)
            if len(suggestions) == 3:
                break
        return {"available": False, "user_id": wanted, "suggestions": suggestions}
    finally:
        db.close_connection(conn)


def register(data: dict):
    """Cria a conta (e-mail+senha OU OAuth). data já validado pelo chamador."""
    email = (data.get("email") or "").strip().lower()
    user_id = _normalize_user_id(data.get("user_id") or email.split("@")[0])
    provider = data.get("auth_provider") or "email"
    password = data.get("password")
    if provider == "email" and not password:
        return {"ok": False, "error": "password_required"}
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            if _fetch_user(cur, "WHERE email = %s", (email,)):
                return {"ok": False, "error": "email_taken"}
            if _fetch_user(cur, "WHERE user_id = %s", (user_id,)):
                return {"ok": False, "error": "user_id_taken"}
            salt = hash_ = None
            if password:
                salt = secrets.token_hex(16)
                hash_ = _hash_password(password, salt)
            cur.execute(
                "INSERT INTO users (user_id, email, first_name, last_name, phone, auth_provider,"
                " provider_id, provider_scopes, password_salt, password_hash, last_login_at)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, now()) RETURNING id",
                (user_id, email, data.get("first_name"), data.get("last_name"), data.get("phone"),
                 provider, data.get("provider_id"), data.get("provider_scopes"), salt, hash_),
            )
            cur.fetchone()
        conn.commit()
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE email = %s", (email,))
    finally:
        db.close_connection(conn)
    db.log_event("register", ok=True, email=email, user_id=user["id"], detail=provider)
    return {"ok": True, "user": _public(user)}


def login(email: str, password: str):
    email = (email or "").strip().lower()
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE email = %s AND deleted_at IS NULL", (email,))
            if not user or not user.get("password_hash"):
                result = {"ok": False, "error": "invalid_credentials"}
            elif _hash_password(password or "", user["password_salt"]) != user["password_hash"]:
                result = {"ok": False, "error": "invalid_credentials"}
            else:
                cur.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (user["id"],))
                result = {"ok": True, "user": _public(user)}
        conn.commit()
    finally:
        db.close_connection(conn)
    db.log_event("login", ok=result["ok"], email=email,
                 user_id=result.get("user", {}).get("id") if result["ok"] else None,
                 detail="email")
    return result


def oauth_login(data: dict):
    """Pós-OAuth: conta existente → sessão; nova → pré-cadastro no frontend."""
    email = (data.get("email") or "").strip().lower()
    provider = data.get("auth_provider")
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE auth_provider = %s AND provider_id = %s AND deleted_at IS NULL",
                               (provider, str(data.get("provider_id"))))
            if not user and email:
                user = _fetch_user(cur, "WHERE email = %s AND deleted_at IS NULL", (email,))
            if user:
                cur.execute(
                    "UPDATE users SET last_login_at = now(), provider_scopes = %s WHERE id = %s",
                    (data.get("provider_scopes"), user["id"]),
                )
                conn.commit()
                result = {"ok": True, "new": False, "user": _public(user)}
            else:
                result = {"ok": True, "new": True}
    finally:
        db.close_connection(conn)
    if not result.get("new"):
        db.log_event("login", ok=True, email=email,
                     user_id=result["user"]["id"], detail=provider)
    return result


def update_profile(data: dict):
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            if not _fetch_user(cur, "WHERE id = %s", (int(data["id"]),)):
                return {"ok": False, "error": "not_found"}
            cur.execute(
                "UPDATE users SET first_name = %s, last_name = %s, phone = %s, updated_at = now()"
                " WHERE id = %s",
                (data.get("first_name"), data.get("last_name"), data.get("phone"), int(data["id"])),
            )
        conn.commit()
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE id = %s", (int(data["id"]),))
        return {"ok": True, "user": _public(user)}
    finally:
        db.close_connection(conn)


# ---------------------------------------------------------------------------
# Operações de ADMINISTRAÇÃO (aba admin, 2026-07-19). Guard server-side: o
# ator tem de ser role=admin NA BASE (nunca confiado do cliente). Toda a
# mutação deixa snapshot na audit_log ANTES de tocar nos dados.
# ---------------------------------------------------------------------------

def _row_snapshot(cur, table, pk):
    cur.execute(f"SELECT * FROM {table} WHERE id = %s", (int(pk),))
    rows = cur.fetchall()
    if not rows:
        return None
    cols = [c[0] for c in cur.description]
    snap = dict(zip(cols, rows[0]))
    snap.pop("password_salt", None)  # segredos NUNCA entram na auditoria
    snap.pop("password_hash", None)
    return snap


def admin_overview(actor_id):
    """Carga ÚNICA da aba de Administração: utilizadores + eventos + auditoria
    numa só ligação/processo (a UI filtra tudo localmente — padrão live/AJAX;
    feedback do utilizador 2026-07-19: nunca um round-trip por filtro)."""
    conn = db.connect()
    try:
        _ensure(conn)
        db.ensure_schema(conn)
        with conn.cursor() as cur:
            if not db.is_admin_user(cur, actor_id):
                return {"ok": False, "error": "forbidden"}
            cur.execute("""SELECT u.id, u.user_id, u.email, u.first_name, u.last_name,
                                  u.auth_provider, u.role, u.created_at, u.last_login_at, u.deleted_at,
                                  (SELECT count(*) FROM transcriptions t
                                   WHERE t.user_id = u.id AND t.deleted_at IS NULL) AS transcription_count
                           FROM users u ORDER BY u.id""")
            cols = [c[0] for c in cur.description]
            users = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.execute("""SELECT id, occurred_at, event, ok, email, user_id, detail, app_version, host
                           FROM access_events ORDER BY occurred_at DESC, id DESC LIMIT 500""")
            cols = [c[0] for c in cur.description]
            events = [dict(zip(cols, r)) for r in cur.fetchall()]
            cur.execute("""SELECT id, occurred_at, actor_user_id, action, table_name, record_id, snapshot
                           FROM audit_log ORDER BY occurred_at DESC, id DESC LIMIT 300""")
            cols = [c[0] for c in cur.description]
            audit = [dict(zip(cols, r)) for r in cur.fetchall()]
        for it in users:
            for k in ("created_at", "last_login_at", "deleted_at"):
                it[k] = db._iso(it.get(k))
            it["transcription_count"] = int(it["transcription_count"] or 0)
        for it in events:
            it["occurred_at"] = db._iso(it["occurred_at"])
            it["ok"] = bool(it["ok"]) if it["ok"] is not None else None
        for it in audit:
            it["occurred_at"] = db._iso(it["occurred_at"])
            if isinstance(it.get("snapshot"), str):
                try:
                    it["snapshot"] = json.loads(it["snapshot"])
                except Exception:
                    pass
        return {"ok": True, "users": users, "events": events, "audit": audit}
    finally:
        db.close_connection(conn)


def admin_list_users(actor_id, search=None, include_deleted=False):
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            if not db.is_admin_user(cur, actor_id):
                return {"ok": False, "error": "forbidden"}
            where, params = "WHERE 1=1", []
            if not include_deleted:
                where += " AND deleted_at IS NULL"
            if search:
                where += " AND (email ILIKE %s OR user_id ILIKE %s)"
                params += [f"%{search}%", f"%{search}%"]
            cur.execute(f"""SELECT u.id, u.user_id, u.email, u.first_name, u.last_name,
                                   u.auth_provider, u.role, u.created_at, u.last_login_at, u.deleted_at,
                                   (SELECT count(*) FROM transcriptions t
                                    WHERE t.user_id = u.id AND t.deleted_at IS NULL) AS transcription_count
                            FROM users u {where} ORDER BY u.id""", params)
            cols = [c[0] for c in cur.description]
            items = [dict(zip(cols, r)) for r in cur.fetchall()]
        for it in items:
            for k in ("created_at", "last_login_at", "deleted_at"):
                it[k] = db._iso(it.get(k))
            it["transcription_count"] = int(it["transcription_count"] or 0)
        return {"ok": True, "items": items}
    finally:
        db.close_connection(conn)


# Campos editáveis pelo admin (2026-07-19: edição COMPLETA do registo, não
# ações pontuais por campo — o id imutável arrasta tudo o resto).
_ADMIN_EDITABLE = ("email", "user_id", "first_name", "last_name", "phone", "role")


def admin_update_user(actor_id, user_pk, fields):
    """Edita qualquer combinação de campos do registo (e-mail, username, nomes,
    telefone, role). Snapshot na auditoria ANTES. Salvaguardas: o admin não
    altera o PRÓPRIO role (não se tranca fora) e o último admin não pode ser
    despromovido (a base nunca fica sem administrador)."""
    fields = {k: v for k, v in (fields or {}).items() if k in _ADMIN_EDITABLE}
    if not fields:
        return {"ok": False, "error": "nothing_to_update"}
    if "email" in fields:
        fields["email"] = (fields["email"] or "").strip().lower()
        if "@" not in fields["email"]:
            return {"ok": False, "error": "invalid_email"}
    if "user_id" in fields:
        fields["user_id"] = _normalize_user_id(fields["user_id"])
        if len(fields["user_id"]) < 3:
            return {"ok": False, "error": "invalid_user_id"}
    if "role" in fields and fields["role"] not in ("user", "admin"):
        return {"ok": False, "error": "invalid_role"}
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            if not db.is_admin_user(cur, actor_id):
                return {"ok": False, "error": "forbidden"}
            before = _row_snapshot(cur, "users", user_pk)
            if not before or before.get("deleted_at"):
                return {"ok": False, "error": "not_found"}
            if "role" in fields and fields["role"] != before.get("role"):
                if int(user_pk) == int(actor_id):
                    return {"ok": False, "error": "cannot_change_own_role"}
                if before.get("role") == "admin" and fields["role"] == "user":
                    cur.execute("SELECT count(*) FROM users WHERE role = 'admin' AND deleted_at IS NULL")
                    if int(cur.fetchone()[0]) <= 1:
                        return {"ok": False, "error": "last_admin"}
            if "email" in fields and fields["email"] != before.get("email"):
                if _fetch_user(cur, "WHERE email = %s AND id <> %s", (fields["email"], int(user_pk))):
                    return {"ok": False, "error": "email_taken"}
            if "user_id" in fields and fields["user_id"] != before.get("user_id"):
                if _fetch_user(cur, "WHERE user_id = %s AND id <> %s", (fields["user_id"], int(user_pk))):
                    return {"ok": False, "error": "user_id_taken"}
            db.audit(conn, actor_id, "update", "users", user_pk, before)
            sets = ", ".join(f"{k} = %s" for k in fields)
            cur.execute(f"UPDATE users SET {sets}, updated_at = now() WHERE id = %s",
                        list(fields.values()) + [int(user_pk)])
        conn.commit()
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE id = %s", (int(user_pk),))
        return {"ok": True, "user": _public(user)}
    finally:
        db.close_connection(conn)


def admin_delete_user(actor_id, user_pk, purge=False):
    """Apaga uma conta com CASCATA AUDITADA.
    - soft (default): deleted_at na conta + em cada transcrição dela; cada
      linha fica com snapshot na audit_log; tudo recuperável.
    - purge=True (dados de teste / pedido definitivo): snapshots primeiro,
      DELETE depois (satélites caem por ON DELETE CASCADE). Sem rasto, nunca."""
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            if not db.is_admin_user(cur, actor_id):
                return {"ok": False, "error": "forbidden"}
            if int(user_pk) == int(actor_id):
                return {"ok": False, "error": "cannot_delete_self"}
            before = _row_snapshot(cur, "users", user_pk)
            if not before:
                return {"ok": False, "error": "not_found"}
            cur.execute("SELECT id FROM transcriptions WHERE user_id = %s", (int(user_pk),))
            owned = [r[0] for r in cur.fetchall()]
            action = "purge" if purge else "delete"
            db.audit(conn, actor_id, action, "users", user_pk, before)
            for tid in owned:
                snap = _row_snapshot(cur, "transcriptions", tid)
                db.audit(conn, actor_id, action, "transcriptions", tid, snap)
            if purge:
                for tid in owned:
                    cur.execute("DELETE FROM transcriptions WHERE id = %s", (int(tid),))
                cur.execute("DELETE FROM users WHERE id = %s", (int(user_pk),))
            else:
                cur.execute("UPDATE users SET deleted_at = now(), updated_at = now() WHERE id = %s",
                            (int(user_pk),))
                for tid in owned:
                    cur.execute("UPDATE transcriptions SET deleted_at = now() WHERE id = %s AND deleted_at IS NULL",
                                (int(tid),))
        conn.commit()
        return {"ok": True, "purged": bool(purge), "cascade": len(owned)}
    finally:
        db.close_connection(conn)


def elevate(email: str, admin_secret: str):
    """Valida a segunda etapa administrativa sem promover a própria conta.

    Desde a v0.20.0, ``role=admin`` só pode ser atribuído por um administrador
    já autenticado na aba Administração. Este gate confirma que a identidade
    já autenticada pertence a uma conta admin ativa e que a credencial central
    digitada é válida. O terceiro fator (TOTP OU e-mail) é emitido pela API.
    """
    email = (email or "").strip().lower()
    if not admin_secret:
        return {"ok": False, "error": "invalid_admin_credentials"}
    try:
        db.check(password_override=admin_secret)  # ligação real com a credencial digitada
    except Exception:
        db.log_event("admin_elevate", ok=False, email=email, detail="bad_secret")
        return {"ok": False, "error": "invalid_admin_credentials"}
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE email = %s AND deleted_at IS NULL", (email,))
            if not user:
                return {"ok": False, "error": "not_found"}
            if (user.get("role") or "").lower() != "admin":
                db.log_event("admin_primary_verified", ok=False, email=email,
                             user_id=user["id"], detail="not_admin")
                return {"ok": False, "error": "not_admin"}
    finally:
        db.close_connection(conn)
    db.log_event("admin_primary_verified", ok=True, email=email, user_id=user["id"])
    return {"ok": True, "user": _public(user)}
