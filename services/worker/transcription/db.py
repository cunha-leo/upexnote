"""
Escrita/leitura dos transcripts no Postgres da VPS (serviço dedicado
upexnote-db; ver docs/PROJECT_CONTEXT.md).

SCHEMA (hub-and-spoke, desde 2026-07-15 — ver Registro):
  transcriptions        HUB/matriz: identidade + metadados + FKs. NUNCA se
                        apaga a sério — delete é soft (deleted_at).
  transcript_texts      1:1: clean_text, raw_text, clean_path (o texto pesado).
  transcription_metrics 1:1: duration_s, cost_usd, processing_s.
  transcription_problems N:1: um aviso por linha, com reason_code (dimensão).
  engines / service_types / problem_reasons  dimensões.
  transcriptions_history  auditoria flat (snapshot antes de update/delete).

- Ligação (host/porta/base/user) vem de db_config.json (IGNORADO pelo Git).
- A PASSWORD vem do Windows Credential Manager (UPEXNOTE_PG_PASSWORD).
- best-effort: o ficheiro local é sempre o artefacto primário; se a VPS
  estiver em baixo só se regista um aviso — nunca se perde uma transcrição paga.
"""
import json
import os
import socket
import sys
from pathlib import Path

from .credentials import get_key

if getattr(sys, "frozen", False):
    _appdata = Path(os.environ.get("APPDATA", str(Path.home())))
    _candidates = [
        _appdata / "UpexNote" / "db_config.json",
        Path(sys.executable).resolve().parent / "db_config.json",
    ]
    CONFIG_PATH = next((p for p in _candidates if p.exists()), _candidates[0])
else:
    CONFIG_PATH = Path(__file__).resolve().parent / "db_config.json"
PG_PASSWORD_KEY = "UPEXNOTE_PG_PASSWORD"

# --------------------------------------------------------------------------
# Schema (hub-and-spoke) — tudo idempotente (CREATE IF NOT EXISTS + upserts).
# --------------------------------------------------------------------------
HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS transcriptions_history (
    history_id      bigserial PRIMARY KEY,
    archived_at     timestamptz NOT NULL DEFAULT now(),
    change_type     text NOT NULL,
    original_id     bigint,
    created_at      timestamptz,
    engine          text,
    source_filename text,
    source_path     text,
    language        text,
    duration_s      numeric,
    cost_usd        numeric,
    processing_s    numeric,
    validation_ok   boolean,
    problems        jsonb,
    clean_text      text,
    raw_text        text,
    clean_path      text,
    host            text
)
"""

SCHEMA_SQL = [
    """CREATE TABLE IF NOT EXISTS engines (
           id smallserial PRIMARY KEY,
           code text UNIQUE NOT NULL,
           label text,
           is_primary boolean NOT NULL DEFAULT false
       )""",
    """CREATE TABLE IF NOT EXISTS service_types (
           id smallserial PRIMARY KEY,
           code text UNIQUE NOT NULL,
           label text
       )""",
    """CREATE TABLE IF NOT EXISTS problem_reasons (
           code text PRIMARY KEY,
           label text,
           severity text NOT NULL DEFAULT 'warning'
       )""",
    """CREATE TABLE IF NOT EXISTS transcriptions (
           id bigserial PRIMARY KEY,
           created_at timestamptz NOT NULL DEFAULT now(),
           edited_at timestamptz,
           deleted_at timestamptz,
           engine_id smallint REFERENCES engines(id),
           service_type_id smallint REFERENCES service_types(id),
           language text,
           source_filename text,
           source_path text,
           validation_ok boolean,
           warnings_ack boolean NOT NULL DEFAULT false,
           host text
       )""",
    """CREATE TABLE IF NOT EXISTS transcript_texts (
           transcription_id bigint PRIMARY KEY REFERENCES transcriptions(id) ON DELETE CASCADE,
           clean_text text,
           raw_text text,
           clean_path text
       )""",
    """CREATE TABLE IF NOT EXISTS transcription_metrics (
           transcription_id bigint PRIMARY KEY REFERENCES transcriptions(id) ON DELETE CASCADE,
           duration_s numeric,
           cost_usd numeric,
           processing_s numeric
       )""",
    """CREATE TABLE IF NOT EXISTS transcription_problems (
           id bigserial PRIMARY KEY,
           transcription_id bigint REFERENCES transcriptions(id) ON DELETE CASCADE,
           reason_code text REFERENCES problem_reasons(code),
           detail text,
           detected_at timestamptz NOT NULL DEFAULT now()
       )""",
    HISTORY_DDL,
]

ENGINE_SEED = [
    ("assemblyai", "AssemblyAI Universal-3.5 Pro", True),
    ("whisper_openai", "whisper-1 (OpenAI)", False),
    ("deepgram", "Deepgram Nova-3", False),
    ("gpt4o_openai", "gpt-4o-transcribe (OpenAI)", False),
]
SERVICE_TYPE_SEED = [("file", "Ficheiro (áudio/vídeo)")]
REASON_SEED = [
    ("UNCLASSIFIED", "Aviso não classificado", "warning"),
    ("COVERAGE_GAP", "Cobertura de tempo incompleta", "warning"),
    ("HALLUCINATION_LOOP", "Possível alucinação / repetição", "warning"),
]

# Snapshot da linha atual (junta hub+texts+metrics+engine) para o histórico flat.
SNAPSHOT_JOIN = """
INSERT INTO transcriptions_history
(change_type, original_id, created_at, engine, source_filename, source_path,
 language, duration_s, cost_usd, processing_s, validation_ok, problems,
 clean_text, raw_text, clean_path, host)
SELECT %s, t.id, t.created_at, e.code, t.source_filename, t.source_path,
 t.language, m.duration_s, m.cost_usd, m.processing_s, t.validation_ok,
 (SELECT jsonb_agg(p.detail ORDER BY p.id) FROM transcription_problems p WHERE p.transcription_id = t.id),
 x.clean_text, x.raw_text, x.clean_path, t.host
FROM transcriptions t
LEFT JOIN engines e ON e.id = t.engine_id
LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
LEFT JOIN transcript_texts x ON x.transcription_id = t.id
WHERE t.id = %s
"""

# Variante SQLite: jsonb_agg não existe; json_group_array + subquery ordenada.
SNAPSHOT_JOIN_SQLITE = """
INSERT INTO transcriptions_history
(change_type, original_id, created_at, engine, source_filename, source_path,
 language, duration_s, cost_usd, processing_s, validation_ok, problems,
 clean_text, raw_text, clean_path, host)
SELECT %s, t.id, t.created_at, e.code, t.source_filename, t.source_path,
 t.language, m.duration_s, m.cost_usd, m.processing_s, t.validation_ok,
 (SELECT json_group_array(detail) FROM (
    SELECT detail FROM transcription_problems WHERE transcription_id = t.id ORDER BY id)),
 x.clean_text, x.raw_text, x.clean_path, t.host
FROM transcriptions t
LEFT JOIN engines e ON e.id = t.engine_id
LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
LEFT JOIN transcript_texts x ON x.transcription_id = t.id
WHERE t.id = %s
"""


def _snapshot_sql():
    return SNAPSHOT_JOIN_SQLITE if storage_mode() == "local" else SNAPSHOT_JOIN


def _iso(v):
    """created_at vem como datetime (psycopg2) ou string ISO (sqlite)."""
    if v is None:
        return None
    return v if isinstance(v, str) else v.isoformat()


def load_config():
    if not CONFIG_PATH.exists():
        return None
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_configured():
    return bool(load_config()) and bool(get_key(PG_PASSWORD_KEY))


# --------------------------------------------------------------------------
# Modo de armazenamento (item 13, Fase 1 — 2026-07-16):
#   "vps"   → Postgres na VPS por túnel SSH (modo administrador/power user)
#   "local" → SQLite embutido nesta máquina (modo utilizador: zero instalação,
#             zero manutenção — o "banco interno" invisível de toda app desktop)
# A escolha vem do ecrã de perfis (settings.json); sem escolha explícita, o
# default preserva o comportamento antigo: vps se houver config+password,
# local caso contrário (instalação virgem de um amigo → SQLite automático).
# --------------------------------------------------------------------------

def storage_mode() -> str:
    from . import paths
    mode = (paths.load_settings() or {}).get("storage_mode")
    if mode in ("local", "vps"):
        return mode
    return "vps" if is_configured() else "local"


def _sqlite_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "UpexNote"
    else:
        base = Path(__file__).resolve().parent
    return base / "upexnote.db"


# Tradução do SQL Postgres → SQLite. As queries do módulo ficam escritas UMA
# vez (dialeto Postgres); o adaptador converte o que difere. Regras cobertas:
# placeholders, ILIKE, now(), e os tipos/DEFAULTs do DDL.
_SQLITE_DDL_RULES = [
    ("bigserial PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("smallserial PRIMARY KEY", "INTEGER PRIMARY KEY AUTOINCREMENT"),
    ("timestamptz NOT NULL DEFAULT now()", "TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))"),
    ("timestamptz", "TEXT"),
    ("boolean NOT NULL DEFAULT false", "INTEGER NOT NULL DEFAULT 0"),
    ("boolean", "INTEGER"),
    ("jsonb", "TEXT"),
    ("numeric", "REAL"),
    ("smallint", "INTEGER"),
    ("bigint", "INTEGER"),
]


def _to_sqlite_sql(sql: str) -> str:
    for a, b in _SQLITE_DDL_RULES:
        sql = sql.replace(a, b)
    sql = sql.replace(" ILIKE ", " LIKE ")
    sql = sql.replace("now()", "strftime('%Y-%m-%dT%H:%M:%fZ','now')")
    return sql.replace("%s", "?")


class _SqliteCursor:
    """Adaptador mínimo: dá ao sqlite3.Cursor a cara do cursor psycopg2 que o
    resto do módulo usa (context manager + tradução do SQL)."""

    def __init__(self, cur):
        self._c = cur

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._c.close()

    def execute(self, sql, params=()):
        self._c.execute(_to_sqlite_sql(sql), params)
        return self

    def fetchone(self):
        return self._c.fetchone()

    def fetchall(self):
        return self._c.fetchall()

    @property
    def description(self):
        return self._c.description


class _SqliteConn:
    def __init__(self, con):
        self._con = con

    def cursor(self):
        return _SqliteCursor(self._con.cursor())

    def commit(self):
        self._con.commit()

    def rollback(self):
        self._con.rollback()

    def close(self):
        self._con.close()


def _connect_sqlite():
    import sqlite3
    if sqlite3.sqlite_version_info < (3, 35):
        raise RuntimeError(f"SQLite demasiado antigo ({sqlite3.sqlite_version}) — precisa de >=3.35 (RETURNING)")
    path = _sqlite_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(path))
    con.execute("PRAGMA foreign_keys = ON")
    con.execute("PRAGMA journal_mode = WAL")
    return _SqliteConn(con)


_active_tunnel = None


# --------------------------------------------------------------------------
# Túnel persistente (item 10 do backlog, 2026-07-16): a app lança um processo
# "guardião" (comando tunnel-keep) que abre o túnel SSH UMA vez e o mantém
# vivo; cada chamada do worker deteta-o pelo ficheiro de estado + probe TCP e
# liga direto — sem pagar o handshake SSH (~2-5s) a cada comando. Sem guardião
# vivo, cai no comportamento antigo (túnel próprio por chamada). O guardião
# morre sozinho quando a app fecha: o Rust segura o stdin dele; EOF = sair
# (funciona até em crash da app — sem processos órfãos).
# --------------------------------------------------------------------------

def _tunnel_state_path() -> Path:
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("APPDATA", str(Path.home()))) / "UpexNote"
    else:
        base = Path(__file__).resolve().parent
    return base / "tunnel_state.json"


def _keeper_port():
    """Porta local do túnel do guardião, se estiver mesmo vivo (probe TCP rápido)."""
    try:
        state = json.loads(_tunnel_state_path().read_text(encoding="utf-8"))
        port = int(state["port"])
    except Exception:
        return None
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.4):
            return port
    except OSError:
        return None


def run_tunnel_keeper() -> int:
    """
    Processo guardião: abre o túnel, publica a porta no ficheiro de estado e
    bloqueia a ler stdin até EOF (= a app fechou). Nunca imprime segredos.
    """
    if storage_mode() == "local":
        print(json.dumps({"type": "info", "message": "modo local (SQLite) — guardiao desnecessario"}))
        return 0
    cfg = load_config()
    ssh_cfg = (cfg or {}).get("ssh")
    if not ssh_cfg:
        print(json.dumps({"type": "info", "message": "sem seccao ssh no config — guardiao desnecessario"}))
        return 0
    from sshtunnel import SSHTunnelForwarder
    key_path = os.path.expanduser(ssh_cfg.get("key", "~/.ssh/upexnote_vps"))
    if not Path(key_path).exists():
        print(json.dumps({"type": "error", "message": f"chave SSH nao encontrada em {key_path}"}))
        return 1
    tunnel = SSHTunnelForwarder(
        (ssh_cfg.get("host", cfg["host"]), ssh_cfg.get("port", 22)),
        ssh_username=ssh_cfg.get("user", "root"),
        ssh_pkey=key_path,
        remote_bind_address=(ssh_cfg.get("remote_host", "127.0.0.1"), ssh_cfg.get("remote_port", cfg.get("port", 5432))),
        local_bind_address=("127.0.0.1", 0),
    )
    tunnel.start()
    state_path = _tunnel_state_path()
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"port": tunnel.local_bind_port, "pid": os.getpid()}), encoding="utf-8"
    )
    print(json.dumps({"type": "ready", "port": tunnel.local_bind_port}), flush=True)
    try:
        sys.stdin.read()  # bloqueia até a app fechar (EOF no pipe)
    except Exception:
        pass
    finally:
        try:
            tunnel.stop()
        except Exception:
            pass
        try:
            state_path.unlink()
        except OSError:
            pass
    return 0


def connect(cfg=None):
    """
    Liga ao Postgres. Se o db_config.json tiver a secção "ssh", a ligação
    passa por um TÚNEL SSH (porta do Postgres fechada ao público; a chave SSH
    da máquina é a credencial — funciona de qualquer rede/IP/VPN). Preferência:
    túnel do guardião persistente (rápido); fallback: túnel próprio por
    chamada. Sem "ssh", liga por TCP direto. Fechar SEMPRE com close_connection().
    """
    global _active_tunnel
    import psycopg2
    if storage_mode() == "local":
        return _connect_sqlite()

    cfg = cfg or load_config()
    if not cfg:
        raise RuntimeError("db_config.json não encontrado")
    pw = get_key(PG_PASSWORD_KEY)
    if not pw:
        raise RuntimeError(f"password do Postgres não configurada ({PG_PASSWORD_KEY})")

    def _pg(host, port):
        return psycopg2.connect(
            host=host,
            port=port,
            dbname=cfg["dbname"],
            user=cfg["user"],
            password=pw,
            sslmode=cfg.get("sslmode", "prefer"),
            connect_timeout=cfg.get("connect_timeout", 8),
        )

    host = cfg["host"]
    port = cfg.get("port", 5432)
    ssh_cfg = cfg.get("ssh")
    if not ssh_cfg:
        return _pg(host, port)

    # Caminho rápido: túnel do guardião já aberto
    keeper = _keeper_port()
    if keeper:
        try:
            return _pg("127.0.0.1", keeper)
        except Exception:
            pass  # guardião meio-morto → cai no túnel próprio

    from sshtunnel import SSHTunnelForwarder
    key_path = os.path.expanduser(ssh_cfg.get("key", "~/.ssh/upexnote_vps"))
    if not Path(key_path).exists():
        raise RuntimeError(
            f"chave SSH não encontrada em {key_path} — ver runbook no PROJECT_CONTEXT.md"
        )
    _active_tunnel = SSHTunnelForwarder(
        (ssh_cfg.get("host", host), ssh_cfg.get("port", 22)),
        ssh_username=ssh_cfg.get("user", "root"),
        ssh_pkey=key_path,
        remote_bind_address=(ssh_cfg.get("remote_host", "127.0.0.1"), ssh_cfg.get("remote_port", port)),
    )
    _active_tunnel.start()
    try:
        return _pg("127.0.0.1", _active_tunnel.local_bind_port)
    except Exception:
        _stop_tunnel()
        raise


def _stop_tunnel():
    global _active_tunnel
    if _active_tunnel is not None:
        try:
            _active_tunnel.stop()
        except Exception:
            pass
        _active_tunnel = None


def close_connection(conn):
    """Fecha a ligação E o túnel SSH (se existir). Usar sempre em vez de conn.close()."""
    try:
        if conn is not None:
            conn.close()
    finally:
        _stop_tunnel()


def ensure_schema(conn):
    """Cria todas as tabelas (idempotente) e semeia as dimensões."""
    with conn.cursor() as cur:
        for stmt in SCHEMA_SQL:
            cur.execute(stmt)
        for code, label, primary in ENGINE_SEED:
            cur.execute(
                "INSERT INTO engines (code, label, is_primary) VALUES (%s,%s,%s) "
                "ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, is_primary = EXCLUDED.is_primary",
                (code, label, primary),
            )
        for code, label in SERVICE_TYPE_SEED:
            cur.execute(
                "INSERT INTO service_types (code, label) VALUES (%s,%s) "
                "ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label",
                (code, label),
            )
        for code, label, severity in REASON_SEED:
            cur.execute(
                "INSERT INTO problem_reasons (code, label, severity) VALUES (%s,%s,%s) "
                "ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, severity = EXCLUDED.severity",
                (code, label, severity),
            )
    conn.commit()


# Compat: nome antigo ainda chamado nalguns sítios.
ensure_table = ensure_schema


def _engine_id(cur, code):
    cur.execute(
        "INSERT INTO engines (code) VALUES (%s) ON CONFLICT (code) DO UPDATE SET code = EXCLUDED.code RETURNING id",
        (code,),
    )
    return cur.fetchone()[0]


def _service_type_id(cur, code="file"):
    cur.execute(
        "INSERT INTO service_types (code) VALUES (%s) ON CONFLICT (code) DO UPDATE SET code = EXCLUDED.code RETURNING id",
        (code,),
    )
    return cur.fetchone()[0]


def _classify_problem(detail):
    """Heurística leve → reason_code. A classificação fina fica para quando a
    lógica de validação do worker emitir códigos diretamente."""
    d = (detail or "").lower()
    if "longe da duracao" in d or "cobertura" in d or "coverage" in d:
        return "COVERAGE_GAP"
    if "aluc" in d or "loop" in d or "repet" in d:
        return "HALLUCINATION_LOOP"
    return "UNCLASSIFIED"


def check():
    """Liga, garante o schema, devolve nº de transcrições ativas."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM transcriptions WHERE deleted_at IS NULL")
            rows = cur.fetchone()[0]
        return {"rows": rows}
    finally:
        close_connection(conn)


def _rows_to_dicts(cur):
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def library_summary():
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*)                         AS total,
                       COALESCE(sum(m.cost_usd), 0)     AS cost_total,
                       COALESCE(sum(m.duration_s), 0)   AS duration_total,
                       COALESCE(avg(m.processing_s), 0) AS proc_avg,
                       min(t.created_at)                AS first_at,
                       max(t.created_at)                AS last_at
                FROM transcriptions t
                LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
                WHERE t.deleted_at IS NULL
            """)
            t = _rows_to_dicts(cur)[0]
            cur.execute("""
                SELECT e.code AS engine,
                       count(*)                         AS count,
                       COALESCE(sum(m.cost_usd), 0)     AS cost,
                       COALESCE(sum(m.duration_s), 0)   AS duration,
                       COALESCE(avg(m.processing_s), 0) AS proc_avg
                FROM transcriptions t
                LEFT JOIN engines e ON e.id = t.engine_id
                LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
                WHERE t.deleted_at IS NULL
                GROUP BY e.code
                ORDER BY count DESC
            """)
            by_engine = _rows_to_dicts(cur)
        return {
            "total": int(t["total"]),
            "cost_total": float(t["cost_total"]),
            "duration_total": float(t["duration_total"]),
            "proc_avg": float(t["proc_avg"]),
            "first_at": _iso(t["first_at"]),
            "last_at": _iso(t["last_at"]),
            "by_engine": [
                {
                    "engine": r["engine"],
                    "count": int(r["count"]),
                    "cost": float(r["cost"]),
                    "duration": float(r["duration"]),
                    "proc_avg": float(r["proc_avg"]),
                }
                for r in by_engine
            ],
        }
    finally:
        close_connection(conn)


def library_list(limit=200, search=None):
    conn = connect()
    try:
        ensure_schema(conn)
        params = []
        where = "WHERE t.deleted_at IS NULL"
        if search:
            where += " AND t.source_filename ILIKE %s"
            params.append(f"%{search}%")
        params.append(int(limit))
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT t.id, t.created_at, e.code AS engine, t.source_filename, t.language,
                       m.duration_s, m.cost_usd, m.processing_s, t.validation_ok, t.warnings_ack,
                       x.clean_path
                FROM transcriptions t
                LEFT JOIN engines e ON e.id = t.engine_id
                LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
                LEFT JOIN transcript_texts x ON x.transcription_id = t.id
                {where}
                ORDER BY t.created_at DESC, t.id DESC
                LIMIT %s
            """, params)
            items = _rows_to_dicts(cur)
        for it in items:
            it["created_at"] = _iso(it["created_at"])
            for k in ("duration_s", "cost_usd", "processing_s"):
                it[k] = float(it[k]) if it[k] is not None else None
        return items
    finally:
        close_connection(conn)


def library_item(item_id):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT t.id, t.created_at, t.edited_at, e.code AS engine, t.source_filename,
                       t.source_path, t.language, m.duration_s, m.cost_usd, m.processing_s,
                       t.validation_ok, t.warnings_ack, x.clean_text, x.clean_path
                FROM transcriptions t
                LEFT JOIN engines e ON e.id = t.engine_id
                LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
                LEFT JOIN transcript_texts x ON x.transcription_id = t.id
                WHERE t.id = %s AND t.deleted_at IS NULL
            """, (int(item_id),))
            rows = _rows_to_dicts(cur)
            if not rows:
                return None
            it = rows[0]
            cur.execute(
                "SELECT detail FROM transcription_problems WHERE transcription_id = %s ORDER BY id",
                (int(item_id),),
            )
            it["problems"] = [r[0] for r in cur.fetchall()]
        it["created_at"] = _iso(it["created_at"])
        it["edited_at"] = _iso(it["edited_at"])
        for k in ("duration_s", "cost_usd", "processing_s"):
            it[k] = float(it[k]) if it[k] is not None else None
        return it
    finally:
        close_connection(conn)


def update_transcription(item_id, new_clean_text):
    """Edita a versão CLEAN. A raw NUNCA é tocada. Snapshot no histórico antes;
    reescreve o ficheiro clean no disco (best-effort)."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT x.clean_path FROM transcriptions t "
                "LEFT JOIN transcript_texts x ON x.transcription_id = t.id "
                "WHERE t.id = %s AND t.deleted_at IS NULL",
                (int(item_id),),
            )
            row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "not_found"}
            clean_path = row[0]
            cur.execute(_snapshot_sql(), ("update", int(item_id)))
            cur.execute(
                "UPDATE transcript_texts SET clean_text = %s WHERE transcription_id = %s",
                (new_clean_text, int(item_id)),
            )
            cur.execute("UPDATE transcriptions SET edited_at = now() WHERE id = %s", (int(item_id),))
        conn.commit()
        file_updated = False
        if clean_path:
            try:
                p = Path(clean_path)
                if p.exists():
                    p.write_text(new_clean_text, encoding="utf-8")
                    file_updated = True
            except Exception:
                pass
        return {"ok": True, "file_updated": file_updated}
    finally:
        close_connection(conn)


def acknowledge_warnings(item_id, ack=True):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM transcriptions WHERE id = %s AND deleted_at IS NULL", (int(item_id),))
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute("UPDATE transcriptions SET warnings_ack = %s WHERE id = %s", (bool(ack), int(item_id)))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


def delete_transcription(item_id):
    """Soft-delete: arquiva no histórico + marca deleted_at. A identidade (id) e
    o conteúdo ficam — recuperável, e nada que aponte para este id se parte."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM transcriptions WHERE id = %s AND deleted_at IS NULL", (int(item_id),))
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(_snapshot_sql(), ("delete", int(item_id)))
            cur.execute("UPDATE transcriptions SET deleted_at = now() WHERE id = %s", (int(item_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


def insert_transcription(record, log=print):
    """best-effort: devolve o id inserido ou None; nunca levanta exceção."""
    if storage_mode() == "vps":
        if not load_config():
            log("DB: db_config.json ausente — só ficheiro local (sem escrita na VPS).")
            return None
        if not get_key(PG_PASSWORD_KEY):
            log("DB: password do Postgres não configurada — só ficheiro local.")
            return None
    conn = None
    try:
        conn = connect()
        ensure_schema(conn)
        with conn.cursor() as cur:
            eng_id = _engine_id(cur, record.get("engine"))
            st_id = _service_type_id(cur, "file")
            cur.execute(
                "INSERT INTO transcriptions "
                "(engine_id, service_type_id, language, source_filename, source_path, validation_ok, host) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (eng_id, st_id, record.get("language"), record.get("source_filename"),
                 record.get("source_path"), record.get("validation_ok"),
                 record.get("host") or socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO transcript_texts (transcription_id, clean_text, raw_text, clean_path) VALUES (%s,%s,%s,%s)",
                (new_id, record.get("clean_text"), record.get("raw_text"), record.get("clean_path")),
            )
            cur.execute(
                "INSERT INTO transcription_metrics (transcription_id, duration_s, cost_usd, processing_s) VALUES (%s,%s,%s,%s)",
                (new_id, record.get("duration_s"), record.get("cost_usd"), record.get("processing_s")),
            )
            for p in (record.get("problems") or []):
                cur.execute(
                    "INSERT INTO transcription_problems (transcription_id, reason_code, detail) VALUES (%s,%s,%s)",
                    (new_id, _classify_problem(p), p),
                )
        conn.commit()
        where = "na base local (SQLite)" if storage_mode() == "local" else "no Postgres da VPS"
        log(f"DB: linha #{new_id} gravada {where}.")
        return new_id
    except Exception as e:  # noqa: BLE001 - best-effort, reportar e seguir
        log(f"DB: não gravou na base ({e}) — ficheiro local está seguro; sincroniza depois.")
        return None
    finally:
        close_connection(conn)


def migrate_v1_to_v2(log=print):
    """
    Migração ÚNICA do schema flat (v1) para o hub-and-spoke (v2). Segura:
    - deteta v1 pela coluna `clean_text` na tabela `transcriptions`;
    - renomeia a tabela antiga para `transcriptions_legacy_v1` (BACKUP, não apaga);
    - cria o schema novo e copia os dados PRESERVANDO os ids;
    - tudo numa transação, com verificação de contagens ANTES do commit;
    - `transcriptions_history` fica intacta.
    Idempotente: se já for v2, não faz nada. Só se aplica ao modo VPS (o
    SQLite local nasce já em v2 — não existe legado para migrar).
    """
    if storage_mode() == "local":
        log("Migração: modo local (SQLite) nasce em v2 — nada a migrar.")
        return {"ok": True, "migrated": False}
    conn = connect()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("""SELECT 1 FROM information_schema.columns
                           WHERE table_name='transcriptions' AND column_name='clean_text'""")
            is_v1 = cur.fetchone() is not None
            if not is_v1:
                log("Migração: já está em v2 (nada a fazer).")
                return {"ok": True, "migrated": False}

            cur.execute("SELECT count(*) FROM transcriptions")
            legacy_count = cur.fetchone()[0]
            log(f"Migração: v1 detetada, {legacy_count} transcrições. A renomear tabela antiga…")

            cur.execute("ALTER TABLE transcriptions RENAME TO transcriptions_legacy_v1")
            cur.execute("ALTER SEQUENCE transcriptions_id_seq RENAME TO transcriptions_legacy_v1_id_seq")

        # cria schema novo + semeia dimensões (usa a mesma conexão/transação)
        with conn.cursor() as cur:
            for stmt in SCHEMA_SQL:
                cur.execute(stmt)
            for code, label, primary in ENGINE_SEED:
                cur.execute(
                    "INSERT INTO engines (code, label, is_primary) VALUES (%s,%s,%s) "
                    "ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, is_primary = EXCLUDED.is_primary",
                    (code, label, primary))
            for code, label in SERVICE_TYPE_SEED:
                cur.execute("INSERT INTO service_types (code, label) VALUES (%s,%s) "
                            "ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label", (code, label))
            for code, label, severity in REASON_SEED:
                cur.execute("INSERT INTO problem_reasons (code, label, severity) VALUES (%s,%s,%s) "
                            "ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label", (code, label, severity))

            # garante que todos os motores presentes na legacy existem na dimensão
            cur.execute("SELECT DISTINCT engine FROM transcriptions_legacy_v1 WHERE engine IS NOT NULL")
            for (code,) in cur.fetchall():
                _engine_id(cur, code)

            # hub (preserva id, created_at, edited_at)
            cur.execute("""
                INSERT INTO transcriptions
                  (id, created_at, edited_at, engine_id, service_type_id, language,
                   source_filename, source_path, validation_ok, warnings_ack, host)
                SELECT l.id, l.created_at, l.edited_at, e.id, st.id, l.language,
                       l.source_filename, l.source_path, l.validation_ok,
                       COALESCE(l.warnings_ack, false), l.host
                FROM transcriptions_legacy_v1 l
                LEFT JOIN engines e ON e.code = l.engine
                CROSS JOIN (SELECT id FROM service_types WHERE code='file') st
            """)
            cur.execute("SELECT setval('transcriptions_id_seq', (SELECT COALESCE(max(id),1) FROM transcriptions))")

            cur.execute("""
                INSERT INTO transcript_texts (transcription_id, clean_text, raw_text, clean_path)
                SELECT id, clean_text, raw_text, clean_path FROM transcriptions_legacy_v1
            """)
            cur.execute("""
                INSERT INTO transcription_metrics (transcription_id, duration_s, cost_usd, processing_s)
                SELECT id, duration_s, cost_usd, processing_s FROM transcriptions_legacy_v1
            """)

            # problems: expandir o jsonb array em linhas, classificando cada uma
            cur.execute("SELECT id, problems FROM transcriptions_legacy_v1 WHERE problems IS NOT NULL")
            prob_rows = 0
            for tid, problems in cur.fetchall():
                if not problems:
                    continue
                for p in problems:
                    cur.execute(
                        "INSERT INTO transcription_problems (transcription_id, reason_code, detail) VALUES (%s,%s,%s)",
                        (tid, _classify_problem(p), p))
                    prob_rows += 1

            # verificação ANTES do commit
            cur.execute("SELECT count(*) FROM transcriptions")
            hub_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM transcript_texts")
            text_count = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM transcription_metrics")
            metric_count = cur.fetchone()[0]

            if hub_count != legacy_count or text_count != legacy_count or metric_count != legacy_count:
                conn.rollback()
                return {"ok": False, "error": "count_mismatch",
                        "legacy": legacy_count, "hub": hub_count, "texts": text_count, "metrics": metric_count}

        conn.commit()
        log(f"Migração OK: {hub_count} transcrições, {text_count} textos, {metric_count} métricas, "
            f"{prob_rows} problemas. Tabela antiga guardada como transcriptions_legacy_v1.")
        return {"ok": True, "migrated": True, "count": hub_count, "problems": prob_rows}
    except Exception as e:  # noqa: BLE001
        try:
            conn.rollback()
        except Exception:
            pass
        return {"ok": False, "error": str(e)}
    finally:
        close_connection(conn)
