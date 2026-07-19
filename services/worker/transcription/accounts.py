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
    with conn.cursor() as cur:
        cur.execute(USERS_DDL)
    conn.commit()


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
        return {"ok": True, "user": _public(user)}
    finally:
        db.close_connection(conn)


def login(email: str, password: str):
    email = (email or "").strip().lower()
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE email = %s", (email,))
            if not user or not user.get("password_hash"):
                return {"ok": False, "error": "invalid_credentials"}
            if _hash_password(password or "", user["password_salt"]) != user["password_hash"]:
                return {"ok": False, "error": "invalid_credentials"}
            cur.execute("UPDATE users SET last_login_at = now() WHERE id = %s", (user["id"],))
        conn.commit()
        return {"ok": True, "user": _public(user)}
    finally:
        db.close_connection(conn)


def oauth_login(data: dict):
    """Pós-OAuth: conta existente → sessão; nova → pré-cadastro no frontend."""
    email = (data.get("email") or "").strip().lower()
    provider = data.get("auth_provider")
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE auth_provider = %s AND provider_id = %s",
                               (provider, str(data.get("provider_id"))))
            if not user and email:
                user = _fetch_user(cur, "WHERE email = %s", (email,))
            if user:
                cur.execute(
                    "UPDATE users SET last_login_at = now(), provider_scopes = %s WHERE id = %s",
                    (data.get("provider_scopes"), user["id"]),
                )
                conn.commit()
                return {"ok": True, "new": False, "user": _public(user)}
        return {"ok": True, "new": True}
    finally:
        db.close_connection(conn)


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


def elevate(email: str, admin_secret: str):
    """Elevação a administrador (Fase 1b, 2026-07-19): identidade JÁ autenticada
    (por qualquer método — e-mail+senha, Google, GitHub) + prova de conhecimento
    da credencial REAL do banco central (validada por ligação com ESSA senha,
    nunca a guardada) ⇒ role='admin' na tabela users da VPS.
    Chamar SEMPRE com o modo vps ativo (set_mode_override feito pelo CLI)."""
    email = (email or "").strip().lower()
    if not admin_secret:
        return {"ok": False, "error": "invalid_admin_credentials"}
    try:
        db.check(password_override=admin_secret)  # ligação real com a credencial digitada
    except Exception:
        return {"ok": False, "error": "invalid_admin_credentials"}
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE email = %s", (email,))
            if not user:
                return {"ok": False, "error": "not_found"}
            cur.execute("UPDATE users SET role = 'admin', updated_at = now() WHERE id = %s",
                        (user["id"],))
        conn.commit()
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE email = %s", (email,))
        return {"ok": True, "user": _public(user)}
    finally:
        db.close_connection(conn)


def reset_password(email: str, new_password: str):
    """Fase local: repõe a senha da conta desta máquina/banco. O reset por
    e-mail verificado chega com a API (Fase 2)."""
    email = (email or "").strip().lower()
    conn = db.connect()
    try:
        _ensure(conn)
        with conn.cursor() as cur:
            user = _fetch_user(cur, "WHERE email = %s", (email,))
            if not user:
                return {"ok": False, "error": "not_found"}
            salt = secrets.token_hex(16)
            cur.execute(
                "UPDATE users SET password_salt = %s, password_hash = %s, updated_at = now()"
                " WHERE id = %s",
                (salt, _hash_password(new_password, salt), user["id"]),
            )
        conn.commit()
        return {"ok": True}
    finally:
        db.close_connection(conn)
