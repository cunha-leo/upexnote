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


def connect(cfg=None):
    import psycopg2
    cfg = cfg or load_config()
    if not cfg:
        raise RuntimeError("db_config.json não encontrado")
    pw = get_key(PG_PASSWORD_KEY)
    if not pw:
        raise RuntimeError(f"password do Postgres não configurada ({PG_PASSWORD_KEY})")
    return psycopg2.connect(
        host=cfg["host"],
        port=cfg.get("port", 5432),
        dbname=cfg["dbname"],
        user=cfg["user"],
        password=pw,
        sslmode=cfg.get("sslmode", "prefer"),
        connect_timeout=cfg.get("connect_timeout", 8),
    )


def ensure_table(conn):
    with conn.cursor() as cur:
        cur.execute(DDL)
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
        conn.close()


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
        if conn:
            conn.close()
