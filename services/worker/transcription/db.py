"""
Escrita best-effort dos transcripts no Postgres da VPS (serviço dedicado
upexnote-db; ver docs/PROJECT_CONTEXT.md Registros (f)/(g)).

- Ligação (host/porta/base/user) vem de db_config.json (IGNORADO pelo Git).
- A PASSWORD vem do Windows Credential Manager
  (UPEXNOTE_PG_PASSWORD) — nunca fica em ficheiro.
- best-effort: o ficheiro local é sempre o artefacto primário. Se a VPS
  estiver em baixo, faltar config ou password, apenas se regista um aviso e
  o fluxo de transcrição continua — nunca se perde uma transcrição já paga.
"""
import json
import os
import socket
import sys
from pathlib import Path

from .credentials import get_key

if getattr(sys, "frozen", False):
    # Executavel empacotado (sidecar). A config (host/porta/base/user —
    # SEM password; essa fica no Credential Manager) e procurada por ordem:
    #   1. %APPDATA%\UpexNote\db_config.json — override do utilizador,
    #      sobrevive a atualizacoes da app;
    #   2. ao lado do proprio worker — versao incluida no zip portatil,
    #      para a app funcionar logo ao descompactar, sem passos manuais.
    _appdata = Path(os.environ.get("APPDATA", str(Path.home())))
    _candidates = [
        _appdata / "UpexNote" / "db_config.json",
        Path(sys.executable).resolve().parent / "db_config.json",
    ]
    CONFIG_PATH = next((p for p in _candidates if p.exists()), _candidates[0])
else:
    CONFIG_PATH = Path(__file__).resolve().parent / "db_config.json"
PG_PASSWORD_KEY = "UPEXNOTE_PG_PASSWORD"

DDL = """
CREATE TABLE IF NOT EXISTS transcriptions (
    id            bigserial PRIMARY KEY,
    created_at    timestamptz NOT NULL DEFAULT now(),
    engine        text NOT NULL,
    source_filename text,
    source_path   text,
    language      text,
    duration_s    numeric,
    cost_usd      numeric,
    processing_s  numeric,
    validation_ok boolean,
    problems      jsonb,
    clean_text    text,
    raw_text      text,
    clean_path    text,
    host          text
)
"""

# Histórico/auditoria: antes de cada edição ou delete, a linha atual é
# copiada para cá (o clean original nunca se perde; deletes são recuperáveis).
HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS transcriptions_history (
    history_id      bigserial PRIMARY KEY,
    archived_at     timestamptz NOT NULL DEFAULT now(),
    change_type     text NOT NULL,            -- 'update' | 'delete'
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

# Snapshot da linha atual para o histórico (usa SELECT ... para copiar tudo).
SNAPSHOT = """
INSERT INTO transcriptions_history
(change_type, original_id, created_at, engine, source_filename, source_path,
 language, duration_s, cost_usd, processing_s, validation_ok, problems,
 clean_text, raw_text, clean_path, host)
SELECT %s, id, created_at, engine, source_filename, source_path,
 language, duration_s, cost_usd, processing_s, validation_ok, problems,
 clean_text, raw_text, clean_path, host
FROM transcriptions WHERE id = %s
"""

INSERT = """
INSERT INTO transcriptions
(engine, source_filename, source_path, language, duration_s, cost_usd,
 processing_s, validation_ok, problems, clean_text, raw_text, clean_path, host)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
RETURNING id
"""


def load_config():
    if not CONFIG_PATH.exists():
        return None
    try:
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_configured():
    return bool(load_config()) and bool(get_key(PG_PASSWORD_KEY))


_active_tunnel = None


def connect(cfg=None):
    """
    Liga ao Postgres. Se o db_config.json tiver a secção "ssh", a ligação
    passa por um TUNEL SSH (porta do Postgres fechada ao público; a chave
    SSH da máquina é a credencial — funciona de qualquer rede/IP/VPN,
    decisão 2026-07-14: o utilizador viaja constantemente e usa VPN, pelo
    que allowlist de IP não serve). Sem "ssh", liga por TCP direto.
    Fechar SEMPRE com close_connection(conn), para o túnel não ficar preso.
    """
    global _active_tunnel
    import psycopg2
    cfg = cfg or load_config()
    if not cfg:
        raise RuntimeError("db_config.json não encontrado")
    pw = get_key(PG_PASSWORD_KEY)
    if not pw:
        raise RuntimeError(f"password do Postgres não configurada ({PG_PASSWORD_KEY})")

    host = cfg["host"]
    port = cfg.get("port", 5432)
    ssh_cfg = cfg.get("ssh")
    if ssh_cfg:
        from sshtunnel import SSHTunnelForwarder
        key_path = os.path.expanduser(ssh_cfg.get("key", "~/.ssh/upexnote_vps"))
        if not Path(key_path).exists():
            raise RuntimeError(
                f"chave SSH não encontrada em {key_path} — ver runbook de acesso à VPS no PROJECT_CONTEXT.md"
            )
        _active_tunnel = SSHTunnelForwarder(
            (ssh_cfg.get("host", host), ssh_cfg.get("port", 22)),
            ssh_username=ssh_cfg.get("user", "root"),
            ssh_pkey=key_path,
            remote_bind_address=(ssh_cfg.get("remote_host", "127.0.0.1"), ssh_cfg.get("remote_port", port)),
        )
        _active_tunnel.start()
        host, port = "127.0.0.1", _active_tunnel.local_bind_port

    try:
        return psycopg2.connect(
            host=host,
            port=port,
            dbname=cfg["dbname"],
            user=cfg["user"],
            password=pw,
            sslmode=cfg.get("sslmode", "prefer"),
            connect_timeout=cfg.get("connect_timeout", 8),
        )
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


def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute(DDL)
        # Migração leve: colunas novas + tabela de histórico (idempotente).
        cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS edited_at timestamptz")
        cur.execute("ALTER TABLE transcriptions ADD COLUMN IF NOT EXISTS warnings_ack boolean NOT NULL DEFAULT false")
        cur.execute(HISTORY_DDL)
    conn.commit()


def check():
    """Liga, garante a tabela, devolve nº de linhas. Levanta excecao se falhar."""
    conn = connect()
    try:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM transcriptions")
            rows = cur.fetchone()[0]
        return {"rows": rows}
    finally:
        close_connection(conn)


def _rows_to_dicts(cur):
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def library_summary():
    """
    Agregados para os dashboards da Biblioteca: totais e repartição por motor.
    Numeros devolvidos como float (JSON-friendly); datas como ISO string.
    """
    conn = connect()
    try:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT count(*)                         AS total,
                       COALESCE(sum(cost_usd), 0)       AS cost_total,
                       COALESCE(sum(duration_s), 0)     AS duration_total,
                       COALESCE(avg(processing_s), 0)   AS proc_avg,
                       min(created_at)                  AS first_at,
                       max(created_at)                  AS last_at
                FROM transcriptions
            """)
            t = _rows_to_dicts(cur)[0]
            cur.execute("""
                SELECT engine,
                       count(*)                       AS count,
                       COALESCE(sum(cost_usd), 0)     AS cost,
                       COALESCE(sum(duration_s), 0)   AS duration,
                       COALESCE(avg(processing_s), 0) AS proc_avg
                FROM transcriptions
                GROUP BY engine
                ORDER BY count DESC
            """)
            by_engine = _rows_to_dicts(cur)
        return {
            "total": int(t["total"]),
            "cost_total": float(t["cost_total"]),
            "duration_total": float(t["duration_total"]),
            "proc_avg": float(t["proc_avg"]),
            "first_at": t["first_at"].isoformat() if t["first_at"] else None,
            "last_at": t["last_at"].isoformat() if t["last_at"] else None,
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
    """
    Lista de transcricoes (METADADOS, sem os textos — payload leve), mais
    recentes primeiro. `search` filtra por nome do ficheiro (case-insensitive).
    """
    conn = connect()
    try:
        ensure_table(conn)
        params = []
        where = ""
        if search:
            where = "WHERE source_filename ILIKE %s"
            params.append(f"%{search}%")
        params.append(int(limit))
        with conn.cursor() as cur:
            cur.execute(f"""
                SELECT id, created_at, engine, source_filename, language,
                       duration_s, cost_usd, processing_s, validation_ok, warnings_ack, clean_path
                FROM transcriptions
                {where}
                ORDER BY created_at DESC, id DESC
                LIMIT %s
            """, params)
            items = _rows_to_dicts(cur)
        for it in items:
            it["created_at"] = it["created_at"].isoformat() if it["created_at"] else None
            for k in ("duration_s", "cost_usd", "processing_s"):
                it[k] = float(it[k]) if it[k] is not None else None
        return items
    finally:
        close_connection(conn)


def library_item(item_id):
    """Um registo completo INCLUINDO o texto (para a vista de detalhe)."""
    conn = connect()
    try:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, created_at, edited_at, engine, source_filename, source_path,
                       language, duration_s, cost_usd, processing_s, validation_ok, warnings_ack,
                       problems, clean_text, clean_path
                FROM transcriptions WHERE id = %s
            """, (int(item_id),))
            rows = _rows_to_dicts(cur)
        if not rows:
            return None
        it = rows[0]
        it["created_at"] = it["created_at"].isoformat() if it["created_at"] else None
        it["edited_at"] = it["edited_at"].isoformat() if it["edited_at"] else None
        for k in ("duration_s", "cost_usd", "processing_s"):
            it[k] = float(it[k]) if it[k] is not None else None
        return it
    finally:
        close_connection(conn)


def update_transcription(item_id, new_clean_text):
    """
    Edita a versão CLEAN de uma transcrição. A raw NUNCA é tocada (imutável).
    Antes de gravar, copia a linha atual para o histórico (reversível). Também
    reescreve o ficheiro clean no disco (best-effort), para não divergir.
    Devolve {ok, file_updated} ou {ok: False, error: 'not_found'}.
    """
    conn = connect()
    try:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT clean_path FROM transcriptions WHERE id = %s", (int(item_id),))
            row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "not_found"}
            clean_path = row[0]
            cur.execute(SNAPSHOT, ("update", int(item_id)))
            cur.execute(
                "UPDATE transcriptions SET clean_text = %s, edited_at = now() WHERE id = %s",
                (new_clean_text, int(item_id)),
            )
        conn.commit()
        file_updated = False
        if clean_path:
            try:
                p = Path(clean_path)
                if p.exists():
                    p.write_text(new_clean_text, encoding="utf-8")
                    file_updated = True
            except Exception:
                pass  # best-effort: o banco é a fonte de verdade da Biblioteca
        return {"ok": True, "file_updated": file_updated}
    finally:
        close_connection(conn)


def acknowledge_warnings(item_id, ack=True):
    """
    Marca (ou desmarca) os avisos de validação como revistos. É só um flag de
    estado — não mexe no conteúdo, por isso não precisa de snapshot no
    histórico (ao contrário de update/delete). Reversível a qualquer momento.
    """
    conn = connect()
    try:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM transcriptions WHERE id = %s", (int(item_id),))
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(
                "UPDATE transcriptions SET warnings_ack = %s WHERE id = %s",
                (bool(ack), int(item_id)),
            )
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


def delete_transcription(item_id):
    """
    Apaga uma transcrição da tabela ativa, DEPOIS de a arquivar no histórico
    (recuperável). Não toca em ficheiros no disco. Devolve {ok} ou not_found.
    """
    conn = connect()
    try:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM transcriptions WHERE id = %s", (int(item_id),))
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(SNAPSHOT, ("delete", int(item_id)))
            cur.execute("DELETE FROM transcriptions WHERE id = %s", (int(item_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


def insert_transcription(record, log=print):
    """best-effort: devolve o id inserido ou None; nunca levanta excecao."""
    if not load_config():
        log("DB: db_config.json ausente — só ficheiro local (sem escrita na VPS).")
        return None
    if not get_key(PG_PASSWORD_KEY):
        log("DB: password do Postgres não configurada — só ficheiro local.")
        return None
    conn = None
    try:
        conn = connect()
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute(INSERT, (
                record.get("engine"),
                record.get("source_filename"),
                record.get("source_path"),
                record.get("language"),
                record.get("duration_s"),
                record.get("cost_usd"),
                record.get("processing_s"),
                record.get("validation_ok"),
                json.dumps(record.get("problems") or []),
                record.get("clean_text"),
                record.get("raw_text"),
                record.get("clean_path"),
                record.get("host") or socket.gethostname(),
            ))
            new_id = cur.fetchone()[0]
        conn.commit()
        log(f"DB: linha #{new_id} gravada no Postgres da VPS.")
        return new_id
    except Exception as e:  # noqa: BLE001 - best-effort, reportar e seguir
        log(f"DB: não gravou na VPS ({e}) — ficheiro local está seguro; sincroniza depois.")
        return None
    finally:
        close_connection(conn)
