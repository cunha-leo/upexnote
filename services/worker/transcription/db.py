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
import re
import socket
import sys
from html import unescape as _html_unescape
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

# ADF-01: documento estruturado (clean -> blocos), hub-and-spoke por ID,
# mesmo padrao das transcricoes (decisao de arquitetura 05/08/2026, ver
# docs/FEATURE_VALIDATION_AND_ROADMAP.md). transcription_id liga ao transcript
# de origem; blocos/glossario pendurados por FK, exclusao em cascata; delete
# real e' soft (deleted_at) + snapshot em documents_history, igual ao resto.
#
# Schema Postgres proprio `documents` (corrigido em 2026-08-07 — nascera em
# `public` por engano; ver Registro em PROJECT_CONTEXT.md e migrate_documents_
# schema() abaixo): mesmo espirito de `support`/`data_studio`, submodulo
# isolado. SQLite (modo local) nao tem esse conceito de schema — continua
# tudo num namespace so; a traducao `_to_sqlite_sql()` remove o prefixo
# "documents." e faz do "CREATE SCHEMA" um no-op so' para esse backend.
DOCUMENTS_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS documents.documents_history (
    history_id       bigserial PRIMARY KEY,
    archived_at      timestamptz NOT NULL DEFAULT now(),
    change_type      text NOT NULL,
    original_id      bigint,
    created_at       timestamptz,
    transcription_id bigint,
    engine           text,
    profile          text,
    title            text,
    objective        text,
    blocks           jsonb,
    jargon           jsonb,
    host             text
)
"""

# ADF-02 (fatia 3, 09/08/2026 — ver docs/NOTEBOOK_ARCHITECTURE.md secao 7 e
# 14): fundacao do dominio `notebooks` — arvore de colecoes (pasta/projeto/
# caderno/seccao) + nota vazia. Mesmo espirito isolado de `documents`: schema
# Postgres proprio, historico flat proprio, dono explicito (_actor). O
# conteudo da nota fica so' texto simples nesta fatia (note_contents.body) —
# a estrutura rica (blocos com IDs estaveis) e' fatia 5, ainda nao aqui.
# Linhagem para transcript/documento (note_sources) e' fatia 4 ("Salvar no
# Caderno"), tambem fora desta fatia.
NOTEBOOK_COLLECTIONS_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.collections (
    id          bigserial PRIMARY KEY,
    created_at  timestamptz NOT NULL DEFAULT now(),
    edited_at   timestamptz,
    deleted_at  timestamptz,
    user_id     bigint REFERENCES users(id),
    parent_id   bigint REFERENCES notebooks.collections(id) ON DELETE CASCADE,
    kind        text NOT NULL DEFAULT 'notebook'
                CHECK (kind IN ('folder', 'project', 'notebook', 'section')),
    title       text NOT NULL,
    position    integer NOT NULL DEFAULT 0,
    host        text
)
"""

NOTEBOOK_NOTES_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.notes (
    id            bigserial PRIMARY KEY,
    created_at    timestamptz NOT NULL DEFAULT now(),
    edited_at     timestamptz,
    deleted_at    timestamptz,
    user_id       bigint REFERENCES users(id),
    collection_id bigint REFERENCES notebooks.collections(id) ON DELETE CASCADE,
    title         text,
    host          text
)
"""

NOTEBOOK_NOTE_CONTENTS_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.note_contents (
    note_id bigint PRIMARY KEY REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    body    text
)
"""

# ADF-02 fatia 4 (09/08/2026 — "Passagem controlada", ver NOTEBOOK_ARCHITECTURE
# secao 3): linhagem explicita de "Salvar no Caderno". 1:1 com a nota nesta
# fatia (uma nota nasce de NO MAXIMO uma previa/transcricao) — nao referencia
# viva: o conteudo ja foi COPIADO para note_contents no momento da gravacao;
# regenerar a previa em `documents` nunca sobrescreve isto.
NOTEBOOK_NOTE_SOURCES_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.note_sources (
    note_id          bigint PRIMARY KEY REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    transcription_id bigint REFERENCES transcriptions(id),
    document_id      bigint REFERENCES documents.structured_documents(id),
    created_at       timestamptz NOT NULL DEFAULT now()
)
"""

# Historico flat, um por entidade (mesmo espirito de documents_history, so
# que sem agregacao de filhos — collections/notes desta fatia nao tem
# satelites 1:N ainda, por isso a mesma query serve Postgres e SQLite depois
# da traducao de prefixo/placeholder, sem precisar de variante _SQLITE).
NOTEBOOK_COLLECTIONS_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.collections_history (
    history_id  bigserial PRIMARY KEY,
    archived_at timestamptz NOT NULL DEFAULT now(),
    change_type text NOT NULL,
    original_id bigint,
    created_at  timestamptz,
    user_id     bigint,
    parent_id   bigint,
    kind        text,
    title       text,
    host        text
)
"""

NOTEBOOK_NOTES_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.notes_history (
    history_id    bigserial PRIMARY KEY,
    archived_at   timestamptz NOT NULL DEFAULT now(),
    change_type   text NOT NULL,
    original_id   bigint,
    created_at    timestamptz,
    user_id       bigint,
    collection_id bigint,
    title         text,
    body          text,
    host          text
)
"""

# ADF-02 (fatia 5, 11/08/2026 — "Editor rico essencial", ver secção 14 item 5):
# versões recuperáveis da nota. NÃO é o mesmo histórico de auditoria de
# notes_history (rasto interno de qualquer update) — este é visível ao
# utilizador ("recuperar versão antiga") e só ganha uma linha quando ele pede
# explicitamente um ponto de recuperação, nunca a cada tecla do autosave.
NOTEBOOK_NOTE_VERSIONS_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.note_versions (
    id         bigserial PRIMARY KEY,
    note_id    bigint NOT NULL REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    title      text,
    body       text,
    user_id    bigint,
    host       text
)
"""

# ADF-02 (fatia 6, 11/08/2026 — "Anotações e referências", ver secção 9):
# âncora híbrida — id do bloco + offsets + texto selecionado + contexto
# próximo — para a UI tentar reposicionar o comentário depois de uma edição
# em vez de depender só de busca textual frágil. `status` reflete o resultado
# dessa tentativa; quem decide a lógica de reposicionamento é a UI, aqui só se
# guarda o estado resultante.
NOTEBOOK_ANNOTATIONS_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.annotations (
    id               bigserial PRIMARY KEY,
    note_id          bigint NOT NULL REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    created_at       timestamptz NOT NULL DEFAULT now(),
    edited_at        timestamptz,
    deleted_at       timestamptz,
    resolved_at      timestamptz,
    user_id          bigint,
    block_id         text,
    start_offset     integer,
    end_offset       integer,
    selected_text    text,
    context_snippet  text,
    body             text NOT NULL,
    status           text NOT NULL DEFAULT 'valid'
                     CHECK (status IN ('valid', 'moved', 'broken')),
    host             text
)
"""

# "references" é palavra reservada em Postgres/SQL — daí `note_references`,
# no mesmo espírito de `note_contents`/`note_sources`/`note_versions`.
NOTEBOOK_NOTE_REFERENCES_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.note_references (
    id          bigserial PRIMARY KEY,
    note_id     bigint NOT NULL REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    created_at  timestamptz NOT NULL DEFAULT now(),
    deleted_at  timestamptz,
    user_id     bigint,
    title       text,
    url         text,
    note_text   text,
    host        text
)
"""

NOTEBOOK_ANNOTATIONS_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.annotations_history (
    history_id   bigserial PRIMARY KEY,
    archived_at  timestamptz NOT NULL DEFAULT now(),
    change_type  text NOT NULL,
    original_id  bigint,
    created_at   timestamptz,
    user_id      bigint,
    note_id      bigint,
    block_id     text,
    body         text,
    host         text
)
"""

NOTEBOOK_NOTE_REFERENCES_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.note_references_history (
    history_id   bigserial PRIMARY KEY,
    archived_at  timestamptz NOT NULL DEFAULT now(),
    change_type  text NOT NULL,
    original_id  bigint,
    created_at   timestamptz,
    user_id      bigint,
    note_id      bigint,
    title        text,
    url          text,
    host         text
)
"""

# ADF-02 (backlinks, 11/08/2026 — ligação nota-a-nota, ver PROJECT_CONTEXT.md
# secção 12, Registro do mesmo dia). Diferente de `note_references` (link
# externo ou nota livre): aqui `to_note_id` aponta para OUTRA nota do próprio
# Caderno. Direcionado (from → to) de propósito — "backlinks" é sempre a
# leitura inversa (quem aponta para mim), calculada em `notebook_links`, não
# uma segunda linha gravada. Sem parsing de `[[wikilinks]]` no corpo: o
# utilizador escolhe a nota-alvo explicitamente, o que evita ambiguidade de
# título duplicado e mantém o custo de implementação baixo.
NOTEBOOK_NOTE_LINKS_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.note_links (
    id            bigserial PRIMARY KEY,
    from_note_id  bigint NOT NULL REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    to_note_id    bigint NOT NULL REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    created_at    timestamptz NOT NULL DEFAULT now(),
    deleted_at    timestamptz,
    user_id       bigint,
    host          text
)
"""

NOTEBOOK_NOTE_LINKS_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.note_links_history (
    history_id    bigserial PRIMARY KEY,
    archived_at   timestamptz NOT NULL DEFAULT now(),
    change_type   text NOT NULL,
    original_id   bigint,
    created_at    timestamptz,
    user_id       bigint,
    from_note_id  bigint,
    to_note_id    bigint,
    host          text
)
"""

# ADF-02 (fatia 7, 11/08/2026 — "Dicionário e glossário", ver secção 10 e 14
# item 7): palavra-chave pessoal solta (`keywords`) e definição vinculada à
# nota (`glossary_entries`). Nesta primeira passagem `source` é sempre
# 'manual' (o utilizador escreve a definição) — "provedores desacoplados"
# (dicionário externo/API) é a evolução natural, não implementada agora; a
# coluna já existe para não exigir migração quando isso chegar.
NOTEBOOK_KEYWORDS_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.keywords (
    id         bigserial PRIMARY KEY,
    note_id    bigint NOT NULL REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    user_id    bigint,
    term       text NOT NULL,
    host       text
)
"""

NOTEBOOK_GLOSSARY_ENTRIES_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.glossary_entries (
    id         bigserial PRIMARY KEY,
    note_id    bigint NOT NULL REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    deleted_at timestamptz,
    user_id    bigint,
    term       text NOT NULL,
    definition text NOT NULL,
    source     text NOT NULL DEFAULT 'manual',
    language   text,
    host       text
)
"""

NOTEBOOK_KEYWORDS_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.keywords_history (
    history_id  bigserial PRIMARY KEY,
    archived_at timestamptz NOT NULL DEFAULT now(),
    change_type text NOT NULL,
    original_id bigint,
    created_at  timestamptz,
    user_id     bigint,
    note_id     bigint,
    term        text,
    host        text
)
"""

NOTEBOOK_GLOSSARY_ENTRIES_HISTORY_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.glossary_entries_history (
    history_id  bigserial PRIMARY KEY,
    archived_at timestamptz NOT NULL DEFAULT now(),
    change_type text NOT NULL,
    original_id bigint,
    created_at  timestamptz,
    user_id     bigint,
    note_id     bigint,
    term        text,
    definition  text,
    host        text
)
"""

# ADF-02 (fatia 8, 11/08/2026 — "Exportação e pacote para IA", ver secção 12
# e 14 item 8). `exports` é só METADADOS (formato + camadas escolhidas) —
# nunca o conteúdo/binário em si, por regra explícita da arquitetura; o
# conteúdo é gerado on-the-fly a cada pedido. `context_packages` é diferente:
# manifesto + prompt são texto simples pequeno, pensados para serem
# reabertos/reenviados depois — por isso esses SIM ficam persistidos.
NOTEBOOK_EXPORTS_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.exports (
    id         bigserial PRIMARY KEY,
    note_id    bigint NOT NULL REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    user_id    bigint,
    format     text NOT NULL,
    layers     text,
    host       text
)
"""

NOTEBOOK_CONTEXT_PACKAGES_DDL = """
CREATE TABLE IF NOT EXISTS notebooks.context_packages (
    id         bigserial PRIMARY KEY,
    note_id    bigint NOT NULL REFERENCES notebooks.notes(id) ON DELETE CASCADE,
    created_at timestamptz NOT NULL DEFAULT now(),
    user_id    bigint,
    layers     text,
    manifest   text,
    prompt     text,
    host       text
)
"""

# users vive AQUI (não só em accounts.py) porque o hub transcriptions
# referencia users(id) — a ordem de criação importa. accounts.py reutiliza.
USERS_DDL = """CREATE TABLE IF NOT EXISTS users (
    id bigserial PRIMARY KEY,
    user_id text UNIQUE NOT NULL,
    email text UNIQUE NOT NULL,
    first_name text,
    last_name text,
    phone text,
    auth_provider text NOT NULL,
    provider_id text,
    provider_scopes text,
    password_salt text,
    password_hash text,
    role text NOT NULL DEFAULT 'user',
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz,
    deleted_at timestamptz,
    last_login_at timestamptz
)"""

# ---------------------------------------------------------------------------
# Padrão de dados (definido pelo utilizador, 2026-07-19):
# - Tabelas vivas guardam SEMPRE o valor atual + trio de datas
#   created_at (dt_issue) / updated_at (dt_change) / deleted_at (dt_ret).
# - Editar = update no lugar + updated_at. EXCEÇÃO: conteúdo de transcrição
#   (transcript_texts) continua a versionar em edição (decisão v0.4.0 — obra).
# - Apagar = soft-delete + snapshot integral na audit_log. deleted_at
#   preenchido é a pista para procurar o rasto na auditoria.
# - audit_log é GENÉRICA (snapshot JSON por linha): nem tabela gigante de
#   colunas, nem um histórico-espelho por tabela. Hard delete (dados de teste)
#   também deixa snapshot ANTES de destruir — deleção sem rasto não existe.
# ---------------------------------------------------------------------------
AUDIT_DDL = """CREATE TABLE IF NOT EXISTS audit_log (
    id bigserial PRIMARY KEY,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    actor_user_id bigint,
    action text NOT NULL,
    table_name text NOT NULL,
    record_id bigint,
    snapshot jsonb
)"""

EVENTS_DDL = """CREATE TABLE IF NOT EXISTS access_events (
    id bigserial PRIMARY KEY,
    occurred_at timestamptz NOT NULL DEFAULT now(),
    event text NOT NULL,
    ok boolean,
    email text,
    user_id bigint,
    detail text,
    app_version text,
    host text
)"""

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
    USERS_DDL,
    AUDIT_DDL,
    EVENTS_DDL,
    """CREATE TABLE IF NOT EXISTS transcriptions (
           id bigserial PRIMARY KEY,
           created_at timestamptz NOT NULL DEFAULT now(),
           edited_at timestamptz,
           deleted_at timestamptz,
           engine_id smallint REFERENCES engines(id),
           service_type_id smallint REFERENCES service_types(id),
           user_id bigint REFERENCES users(id),
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
    "CREATE SCHEMA IF NOT EXISTS documents",
    """CREATE TABLE IF NOT EXISTS documents.structured_documents (
           id bigserial PRIMARY KEY,
           created_at timestamptz NOT NULL DEFAULT now(),
           edited_at timestamptz,
           deleted_at timestamptz,
           transcription_id bigint REFERENCES transcriptions(id) ON DELETE CASCADE,
           user_id bigint REFERENCES users(id),
           engine_id smallint REFERENCES engines(id),
           profile text NOT NULL DEFAULT 'detalhado',
           title text,
           objective text,
           raw_clean_check_ok boolean,
           host text
       )""",
    """CREATE TABLE IF NOT EXISTS documents.document_blocks (
           id bigserial PRIMARY KEY,
           document_id bigint REFERENCES documents.structured_documents(id) ON DELETE CASCADE,
           block_key text NOT NULL,
           position integer NOT NULL,
           block_type text NOT NULL,
           heading text,
           content text,
           speaker text,
           block_timestamp text
       )""",
    """CREATE TABLE IF NOT EXISTS documents.document_glossary (
           id bigserial PRIMARY KEY,
           document_id bigint REFERENCES documents.structured_documents(id) ON DELETE CASCADE,
           term text NOT NULL,
           meaning text
       )""",
    """CREATE TABLE IF NOT EXISTS documents.document_metrics (
           document_id bigint PRIMARY KEY REFERENCES documents.structured_documents(id) ON DELETE CASCADE,
           processing_s numeric,
           input_tokens integer,
           output_tokens integer
       )""",
    DOCUMENTS_HISTORY_DDL,
    "CREATE SCHEMA IF NOT EXISTS notebooks",
    NOTEBOOK_COLLECTIONS_DDL,
    NOTEBOOK_NOTES_DDL,
    NOTEBOOK_NOTE_CONTENTS_DDL,
    NOTEBOOK_NOTE_SOURCES_DDL,
    NOTEBOOK_NOTE_VERSIONS_DDL,
    NOTEBOOK_ANNOTATIONS_DDL,
    NOTEBOOK_NOTE_REFERENCES_DDL,
    NOTEBOOK_KEYWORDS_DDL,
    NOTEBOOK_GLOSSARY_ENTRIES_DDL,
    NOTEBOOK_EXPORTS_DDL,
    NOTEBOOK_CONTEXT_PACKAGES_DDL,
    NOTEBOOK_NOTE_LINKS_DDL,
    NOTEBOOK_COLLECTIONS_HISTORY_DDL,
    NOTEBOOK_NOTES_HISTORY_DDL,
    NOTEBOOK_ANNOTATIONS_HISTORY_DDL,
    NOTEBOOK_NOTE_REFERENCES_HISTORY_DDL,
    NOTEBOOK_KEYWORDS_HISTORY_DDL,
    NOTEBOOK_GLOSSARY_ENTRIES_HISTORY_DDL,
    NOTEBOOK_NOTE_LINKS_HISTORY_DDL,
]

ENGINE_SEED = [
    ("assemblyai", "AssemblyAI Universal-3.5 Pro", True),
    ("whisper_openai", "whisper-1 (OpenAI)", False),
    ("deepgram", "Deepgram Nova-3", False),
    ("gpt4o_openai", "gpt-4o-transcribe (OpenAI)", False),
]
# Motores de FORMATACAO (clean -> documento), dimensao PARTILHADA com os de
# transcricao (mesma tabela `engines` — so um lookup code->label->id; ver
# coluna `kind` adicionada em _ensure_document_columns). Mantido como lista
# estatica aqui (nao importa registry.py) para nao acoplar db.py ao SDK de
# cada provedor so para escrever no banco.
FORMAT_ENGINE_SEED = [
    ("deepseek", "DeepSeek (deepseek-v4-flash)"),
    ("grok", "Grok (grok-4-fast)"),
    ("gpt5_mini", "OpenAI (gpt-5-mini)"),
    ("claude_haiku", "Claude Haiku 4.5"),
    ("gemini", "Gemini (gemini-3.6-flash)"),
    ("claude_sonnet", "Claude Sonnet 5"),
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


# Snapshot do documento (hub+blocos+glossario) para o historico flat, antes
# de editar/apagar. blocks/jargon vao agregados (mesma logica de "problems"
# em SNAPSHOT_JOIN, so que dois agregados em vez de um).
DOC_SNAPSHOT_JOIN = """
INSERT INTO documents.documents_history
(change_type, original_id, created_at, transcription_id, engine, profile, title, objective, blocks, jargon, host)
SELECT %s, d.id, d.created_at, d.transcription_id, e.code, d.profile, d.title, d.objective,
 (SELECT jsonb_agg(jsonb_build_object('block_key', b.block_key, 'type', b.block_type,
    'heading', b.heading, 'content', b.content, 'speaker', b.speaker, 'timestamp', b.block_timestamp)
    ORDER BY b.position) FROM documents.document_blocks b WHERE b.document_id = d.id),
 (SELECT jsonb_agg(jsonb_build_object('term', g.term, 'meaning', g.meaning) ORDER BY g.id)
    FROM documents.document_glossary g WHERE g.document_id = d.id),
 d.host
FROM documents.structured_documents d
LEFT JOIN engines e ON e.id = d.engine_id
WHERE d.id = %s
"""

# Variante SQLite: sem jsonb_build_object/jsonb_agg — monta um JSON de texto
# simples (json_group_array + json_object) equivalente.
DOC_SNAPSHOT_JOIN_SQLITE = """
INSERT INTO documents_history
(change_type, original_id, created_at, transcription_id, engine, profile, title, objective, blocks, jargon, host)
SELECT %s, d.id, d.created_at, d.transcription_id, e.code, d.profile, d.title, d.objective,
 (SELECT json_group_array(json_object('block_key', block_key, 'type', block_type,
    'heading', heading, 'content', content, 'speaker', speaker, 'timestamp', block_timestamp)) FROM (
    SELECT * FROM document_blocks WHERE document_id = d.id ORDER BY position)),
 (SELECT json_group_array(json_object('term', term, 'meaning', meaning)) FROM (
    SELECT * FROM document_glossary WHERE document_id = d.id ORDER BY id)),
 d.host
FROM structured_documents d
LEFT JOIN engines e ON e.id = d.engine_id
WHERE d.id = %s
"""


# Snapshots do dominio `notebooks` (fatia 3): sem filhos 1:N nesta fatia,
# entao uma unica query serve os dois dialetos (a traducao de prefixo/
# placeholder de _to_sqlite_sql já basta — sem jsonb_agg a resolver).
NOTEBOOK_COLLECTION_SNAPSHOT_JOIN = """
INSERT INTO notebooks.collections_history
(change_type, original_id, created_at, user_id, parent_id, kind, title, host)
SELECT %s, c.id, c.created_at, c.user_id, c.parent_id, c.kind, c.title, c.host
FROM notebooks.collections c
WHERE c.id = %s
"""

NOTEBOOK_NOTE_SNAPSHOT_JOIN = """
INSERT INTO notebooks.notes_history
(change_type, original_id, created_at, user_id, collection_id, title, body, host)
SELECT %s, n.id, n.created_at, n.user_id, n.collection_id, n.title, nc.body, n.host
FROM notebooks.notes n
LEFT JOIN notebooks.note_contents nc ON nc.note_id = n.id
WHERE n.id = %s
"""

# fatia 5 — snapshot RECUPERÁVEL (não é rasto de auditoria): guarda o estado
# ATUAL antes de sobrescrever, só quando pedido explicitamente (ver
# notebook_note_version_create/_restore).
NOTEBOOK_NOTE_VERSION_SNAPSHOT_JOIN = """
INSERT INTO notebooks.note_versions (note_id, title, body, user_id, host)
SELECT n.id, n.title, nc.body, %s, n.host
FROM notebooks.notes n
LEFT JOIN notebooks.note_contents nc ON nc.note_id = n.id
WHERE n.id = %s
RETURNING id
"""

# fatia 6 — mesmo espírito de NOTEBOOK_NOTE_SNAPSHOT_JOIN, para anotações e
# referências.
NOTEBOOK_ANNOTATION_SNAPSHOT_JOIN = """
INSERT INTO notebooks.annotations_history
(change_type, original_id, created_at, user_id, note_id, block_id, body, host)
SELECT %s, a.id, a.created_at, a.user_id, a.note_id, a.block_id, a.body, a.host
FROM notebooks.annotations a
WHERE a.id = %s
"""

NOTEBOOK_NOTE_REFERENCE_SNAPSHOT_JOIN = """
INSERT INTO notebooks.note_references_history
(change_type, original_id, created_at, user_id, note_id, title, url, host)
SELECT %s, r.id, r.created_at, r.user_id, r.note_id, r.title, r.url, r.host
FROM notebooks.note_references r
WHERE r.id = %s
"""

# fatia 7 — mesmo espírito.
NOTEBOOK_KEYWORD_SNAPSHOT_JOIN = """
INSERT INTO notebooks.keywords_history
(change_type, original_id, created_at, user_id, note_id, term, host)
SELECT %s, k.id, k.created_at, k.user_id, k.note_id, k.term, k.host
FROM notebooks.keywords k
WHERE k.id = %s
"""

NOTEBOOK_GLOSSARY_SNAPSHOT_JOIN = """
INSERT INTO notebooks.glossary_entries_history
(change_type, original_id, created_at, user_id, note_id, term, definition, host)
SELECT %s, g.id, g.created_at, g.user_id, g.note_id, g.term, g.definition, g.host
FROM notebooks.glossary_entries g
WHERE g.id = %s
"""

NOTEBOOK_NOTE_LINK_SNAPSHOT_JOIN = """
INSERT INTO notebooks.note_links_history
(change_type, original_id, created_at, user_id, from_note_id, to_note_id, host)
SELECT %s, l.id, l.created_at, l.user_id, l.from_note_id, l.to_note_id, l.host
FROM notebooks.note_links l
WHERE l.id = %s
"""


def _snapshot_sql():
    return SNAPSHOT_JOIN_SQLITE if storage_mode() == "local" else SNAPSHOT_JOIN


def _doc_snapshot_sql():
    return DOC_SNAPSHOT_JOIN_SQLITE if storage_mode() == "local" else DOC_SNAPSHOT_JOIN


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

_mode_override = None


def set_mode_override(mode):
    """Força um modo SÓ neste processo (ex.: login de administrador feito a
    partir de uma sessão local — as contas admin vivem na VPS). Não grava."""
    global _mode_override
    _mode_override = mode if mode in ("local", "vps") else None


def storage_mode() -> str:
    if _mode_override:
        return _mode_override
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
    # SQLite nao tem schemas (namespace unico) — o "documents" so existe pra
    # separar o submodulo no Postgres (ver DOCUMENTS_HISTORY_DDL). O CREATE
    # SCHEMA vira no-op e o prefixo "documents." e' removido das tabelas.
    if sql.strip().upper().startswith("CREATE SCHEMA"):
        return "SELECT 1"
    sql = sql.replace("documents.", "")
    # notebooks: "collections"/"notes" são nomes demasiado genéricos para
    # desaparecer no namespace único do SQLite (colidiriam com outra coisa
    # mais cedo ou mais tarde) — em vez de remover o prefixo, prefixa-se a
    # tabela (decisão explícita em NOTEBOOK_ARCHITECTURE.md secção 7).
    sql = sql.replace("notebooks.", "notebook_")
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


def connect(cfg=None, password_override=None):
    """
    Liga ao Postgres. Se o db_config.json tiver a secção "ssh", a ligação
    passa por um TÚNEL SSH (porta do Postgres fechada ao público; a chave SSH
    da máquina é a credencial — funciona de qualquer rede/IP/VPN). Preferência:
    túnel do guardião persistente (rápido); fallback: túnel próprio por
    chamada. Sem "ssh", liga por TCP direto. Fechar SEMPRE com close_connection().
    `password_override`: valida uma credencial DIGITADA (gate do administrador —
    prova de conhecimento, não de posse da máquina) em vez da guardada.
    """
    global _active_tunnel
    import psycopg2
    if storage_mode() == "local":
        return _connect_sqlite()

    cfg = cfg or load_config()
    if not cfg:
        raise RuntimeError("db_config.json não encontrado")
    pw = password_override or get_key(PG_PASSWORD_KEY)
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


def _has_column(cur, table, column):
    if storage_mode() == "local":
        cur.execute(f"SELECT name FROM pragma_table_info('{table}') WHERE name=%s", (column,))
    else:
        cur.execute("""SELECT 1 FROM information_schema.columns
                       WHERE table_name=%s AND column_name=%s""", (table, column))
    return cur.fetchone() is not None


def _ensure_owner_column(conn):
    """Migrações idempotentes de colunas em bases pré-existentes:
    - user_id no hub (isolamento por utilizador, 2026-07-19);
    - trio de datas (padrão de dados, 2026-07-19) onde falta;
    - kind em engines (ADF-01, 06/08/2026): distingue motor de transcrição
      (áudio->texto) de motor de formatação (clean->documento), na MESMA
      tabela dimensão — so' um lookup code/label, nao justifica duplicar."""
    with conn.cursor() as cur:
        if not _has_column(cur, "transcriptions", "user_id"):
            cur.execute("ALTER TABLE transcriptions ADD COLUMN user_id bigint REFERENCES users(id)")
        if not _has_column(cur, "users", "deleted_at"):
            cur.execute("ALTER TABLE users ADD COLUMN deleted_at timestamptz")
        if not _has_column(cur, "engines", "kind"):
            cur.execute("ALTER TABLE engines ADD COLUMN kind text NOT NULL DEFAULT 'transcription'")


_ensured_modes = set()


def ensure_schema(conn):
    """Cria todas as tabelas (idempotente) e semeia as dimensões.
    Corre UMA vez por processo/modo: cada statement é uma ida-e-volta pelo
    túnel — repetir o ensure em cada connect() do mesmo comando só soma
    latência (visto no login admin da v0.18.1)."""
    mode = storage_mode()
    if mode in _ensured_modes:
        return
    with conn.cursor() as cur:
        for stmt in SCHEMA_SQL:
            cur.execute(stmt)
    _ensure_owner_column(conn)
    with conn.cursor() as cur:
        for code, label, primary in ENGINE_SEED:
            cur.execute(
                "INSERT INTO engines (code, label, is_primary, kind) VALUES (%s,%s,%s,'transcription') "
                "ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, is_primary = EXCLUDED.is_primary",
                (code, label, primary),
            )
        for code, label in FORMAT_ENGINE_SEED:
            cur.execute(
                "INSERT INTO engines (code, label, is_primary, kind) VALUES (%s,%s,false,'formatting') "
                "ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label, kind = EXCLUDED.kind",
                (code, label),
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
    _ensured_modes.add(mode)


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


def check(password_override=None):
    """Liga, garante o schema, devolve nº de transcrições ativas."""
    conn = connect(password_override=password_override)
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


# --------------------------------------------------------------------------
# Isolamento por utilizador (2026-07-19): cada conta vê SÓ o que é dela;
# role=admin (na tabela users do modo ativo) vê tudo, com o dono visível.
# O role NUNCA vem do chamador — é lido da base a partir do user_id da
# sessão (o cliente não consegue "afirmar-se" admin).
# user_id=None (chamadas de dev/CLI direto) mantém o comportamento antigo
# de ver tudo — a app envia SEMPRE o utilizador da sessão.
# --------------------------------------------------------------------------

def _actor(cur, user_id, admin_verified=False):
    """Devolve (filtro_sql, params, is_admin) para o utilizador da sessão."""
    if user_id is None:
        return "", [], True
    cur.execute("SELECT role FROM users WHERE id = %s AND deleted_at IS NULL", (int(user_id),))
    row = cur.fetchone()
    if row and (row[0] or "").lower() == "admin" and admin_verified:
        return "", [], True
    return " AND t.user_id = %s", [int(user_id)], False


def is_admin_user(cur, user_id) -> bool:
    """Guard server-side das operações administrativas: o role vem da BASE."""
    if user_id is None:
        return False
    cur.execute("SELECT role FROM users WHERE id = %s AND deleted_at IS NULL", (int(user_id),))
    row = cur.fetchone()
    return bool(row and (row[0] or "").lower() == "admin")


def audit(conn, actor_user_id, action, table_name, record_id, snapshot):
    """Entrada na auditoria, na MESMA transação do chamador (commit é dele).
    snapshot = dict com o retrato da linha ANTES da operação."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO audit_log (actor_user_id, action, table_name, record_id, snapshot)"
            " VALUES (%s,%s,%s,%s,%s)",
            (int(actor_user_id) if actor_user_id is not None else None, action, table_name,
             int(record_id) if record_id is not None else None,
             json.dumps(snapshot, ensure_ascii=False, default=str)),
        )


def log_event(event, ok=None, email=None, user_id=None, detail=None, app_version=None):
    """Evento de acesso (login/reset/elevação/…) — best-effort, nunca levanta.
    Grava na base do MODO ATIVO (eventos de instalações remotas chegam ao
    central via API na Fase 2)."""
    conn = None
    try:
        conn = connect()
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO access_events (event, ok, email, user_id, detail, app_version, host)"
                " VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (event, ok, (email or "").strip().lower() or None,
                 int(user_id) if user_id is not None else None, detail, app_version,
                 socket.gethostname()),
            )
        conn.commit()
    except Exception:
        pass
    finally:
        close_connection(conn)


def list_access_events(actor_id, since=None, event=None, search=None, limit=500):
    """Painel de Atividade (só admin): eventos recentes + agregados por tipo."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            if not is_admin_user(cur, actor_id):
                return {"ok": False, "error": "forbidden"}
            where, params = "WHERE 1=1", []
            if since:
                where += " AND occurred_at >= %s"
                params.append(since)
            if event:
                where += " AND event = %s"
                params.append(event)
            if search:
                where += " AND email ILIKE %s"
                params.append(f"%{search}%")
            cur.execute(f"""SELECT event, ok, count(*) AS n FROM access_events {where}
                            GROUP BY event, ok ORDER BY event""", params)
            counts = [{"event": r[0], "ok": r[1], "n": int(r[2])} for r in cur.fetchall()]
            cur.execute(f"""SELECT id, occurred_at, event, ok, email, user_id, detail, app_version, host
                            FROM access_events {where}
                            ORDER BY occurred_at DESC, id DESC LIMIT %s""", params + [int(limit)])
            items = _rows_to_dicts(cur)
        for it in items:
            it["occurred_at"] = _iso(it["occurred_at"])
            it["ok"] = bool(it["ok"]) if it["ok"] is not None else None
        return {"ok": True, "counts": counts, "items": items}
    finally:
        close_connection(conn)


def list_audit(actor_id, table=None, record_id=None, since=None, limit=300):
    """Consulta da auditoria (só admin), por tabela/id/data."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            if not is_admin_user(cur, actor_id):
                return {"ok": False, "error": "forbidden"}
            where, params = "WHERE 1=1", []
            if table:
                where += " AND table_name = %s"
                params.append(table)
            if record_id is not None:
                where += " AND record_id = %s"
                params.append(int(record_id))
            if since:
                where += " AND occurred_at >= %s"
                params.append(since)
            cur.execute(f"""SELECT id, occurred_at, actor_user_id, action, table_name, record_id, snapshot
                            FROM audit_log {where}
                            ORDER BY occurred_at DESC, id DESC LIMIT %s""", params + [int(limit)])
            items = _rows_to_dicts(cur)
        for it in items:
            it["occurred_at"] = _iso(it["occurred_at"])
            if isinstance(it.get("snapshot"), str):
                try:
                    it["snapshot"] = json.loads(it["snapshot"])
                except Exception:
                    pass
        return {"ok": True, "items": items}
    finally:
        close_connection(conn)


def library_summary(user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            cur.execute(f"""
                SELECT count(*)                         AS total,
                       COALESCE(sum(m.cost_usd), 0)     AS cost_total,
                       COALESCE(sum(m.duration_s), 0)   AS duration_total,
                       COALESCE(avg(m.processing_s), 0) AS proc_avg,
                       min(t.created_at)                AS first_at,
                       max(t.created_at)                AS last_at
                FROM transcriptions t
                LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
                WHERE t.deleted_at IS NULL{own_sql}
            """, own_params)
            t = _rows_to_dicts(cur)[0]
            cur.execute(f"""
                SELECT e.code AS engine,
                       count(*)                         AS count,
                       COALESCE(sum(m.cost_usd), 0)     AS cost,
                       COALESCE(sum(m.duration_s), 0)   AS duration,
                       COALESCE(avg(m.processing_s), 0) AS proc_avg
                FROM transcriptions t
                LEFT JOIN engines e ON e.id = t.engine_id
                LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
                WHERE t.deleted_at IS NULL{own_sql}
                GROUP BY e.code
                ORDER BY count DESC
            """, own_params)
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


def library_list(limit=200, search=None, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, is_admin = _actor(cur, user_id, admin_verified)
            params = list(own_params)
            where = "WHERE t.deleted_at IS NULL" + own_sql
            if search:
                where += " AND t.source_filename ILIKE %s"
                params.append(f"%{search}%")
            params.append(int(limit))
            # Vista de admin inclui o DONO de cada item (e-mail + username +
            # como entrou) — auditoria pedida pelo produto (2026-07-19).
            owner_cols = (", u.email AS owner_email, u.user_id AS owner_username,"
                          " u.auth_provider AS owner_provider" if is_admin else "")
            owner_join = "LEFT JOIN users u ON u.id = t.user_id" if is_admin else ""
            cur.execute(f"""
                SELECT t.id, t.created_at, e.code AS engine, t.source_filename, t.language,
                       m.duration_s, m.cost_usd, m.processing_s, t.validation_ok, t.warnings_ack,
                       x.clean_path{owner_cols}
                FROM transcriptions t
                LEFT JOIN engines e ON e.id = t.engine_id
                LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
                LEFT JOIN transcript_texts x ON x.transcription_id = t.id
                {owner_join}
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


def library_item(item_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, is_admin = _actor(cur, user_id, admin_verified)
            owner_cols = (", u.email AS owner_email, u.user_id AS owner_username,"
                          " u.auth_provider AS owner_provider" if is_admin else "")
            owner_join = "LEFT JOIN users u ON u.id = t.user_id" if is_admin else ""
            cur.execute(f"""
                SELECT t.id, t.created_at, t.edited_at, e.code AS engine, t.source_filename,
                       t.source_path, t.language, m.duration_s, m.cost_usd, m.processing_s,
                       t.validation_ok, t.warnings_ack, x.clean_text, x.clean_path{owner_cols}
                FROM transcriptions t
                LEFT JOIN engines e ON e.id = t.engine_id
                LEFT JOIN transcription_metrics m ON m.transcription_id = t.id
                LEFT JOIN transcript_texts x ON x.transcription_id = t.id
                {owner_join}
                WHERE t.id = %s AND t.deleted_at IS NULL{own_sql}
            """, [int(item_id)] + own_params)
            rows = _rows_to_dicts(cur)
            if not rows:
                return None
            it = rows[0]
            cur.execute(
                "SELECT detail FROM transcription_problems WHERE transcription_id = %s ORDER BY id",
                (int(item_id),),
            )
            it["problems"] = [r[0] for r in cur.fetchall()]
            # Documentos estruturados ja gerados a partir deste transcript
            # (ADF-01). Pendurado aqui, como os "problems", em vez de um
            # comando proprio: a tela de detalhe ja chama library_item, entao
            # o botao "Formatar" sabe na hora se ha documento para abrir sem
            # pagar uma segunda ida ao worker pelo tunel. Aditivo — quem lia
            # library_item antes continua a funcionar.
            # notebook_note_id (fatia 4, ver secao 4 da arquitetura): a UI
            # decide "Salvar no Caderno" vs "Abrir no Caderno" sem 2a ida ao
            # worker — nota soft-apagada nao conta (deleted_at IS NULL), o
            # dono pode gravar de novo.
            cur.execute(
                "SELECT d.id, d.profile, d.title, d.created_at, e.code AS engine, nn.id AS notebook_note_id "
                "FROM documents.structured_documents d "
                "LEFT JOIN engines e ON e.id = d.engine_id "
                "LEFT JOIN notebooks.note_sources ns ON ns.document_id = d.id "
                "LEFT JOIN notebooks.notes nn ON nn.id = ns.note_id AND nn.deleted_at IS NULL "
                "WHERE d.transcription_id = %s AND d.deleted_at IS NULL "
                "ORDER BY d.id DESC",
                (int(item_id),),
            )
            it["documents"] = _rows_to_dicts(cur)
        it["created_at"] = _iso(it["created_at"])
        it["edited_at"] = _iso(it["edited_at"])
        for d in it.get("documents") or []:
            d["created_at"] = _iso(d["created_at"])
        for k in ("duration_s", "cost_usd", "processing_s"):
            it[k] = float(it[k]) if it[k] is not None else None
        return it
    finally:
        close_connection(conn)


def update_transcription(item_id, new_clean_text, user_id=None, admin_verified=False):
    """Edita a versão CLEAN. A raw NUNCA é tocada. Snapshot no histórico antes;
    reescreve o ficheiro clean no disco (best-effort). Só o dono ou admin."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            cur.execute(
                "SELECT x.clean_path FROM transcriptions t "
                "LEFT JOIN transcript_texts x ON x.transcription_id = t.id "
                f"WHERE t.id = %s AND t.deleted_at IS NULL{own_sql}",
                [int(item_id)] + own_params,
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


def acknowledge_warnings(item_id, ack=True, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            cur.execute(f"SELECT 1 FROM transcriptions t WHERE t.id = %s AND t.deleted_at IS NULL{own_sql}",
                        [int(item_id)] + own_params)
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute("UPDATE transcriptions SET warnings_ack = %s WHERE id = %s", (bool(ack), int(item_id)))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


def delete_transcription(item_id, user_id=None, admin_verified=False):
    """Soft-delete: arquiva no histórico + marca deleted_at. A identidade (id) e
    o conteúdo ficam — recuperável, e nada que aponte para este id se parte.
    Só o dono ou admin."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            cur.execute(f"SELECT 1 FROM transcriptions t WHERE t.id = %s AND t.deleted_at IS NULL{own_sql}",
                        [int(item_id)] + own_params)
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
            owner = record.get("user_id")
            cur.execute(
                "INSERT INTO transcriptions "
                "(engine_id, service_type_id, user_id, language, source_filename, source_path, validation_ok, host) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (eng_id, st_id, int(owner) if owner is not None else None,
                 record.get("language"), record.get("source_filename"),
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


# --------------------------------------------------------------------------
# ADF-01 — documento estruturado (clean -> blocos). Mesmo padrao de dono/
# admin de transcriptions (_actor), soft-delete + snapshot em documents_history.
# --------------------------------------------------------------------------

_DOCUMENT_TABLES = (
    "structured_documents",
    "document_blocks",
    "document_glossary",
    "document_metrics",
    "documents_history",
)


def migrate_documents_schema(log=print):
    """Migração pontual (2026-08-07): as 5 tabelas do ADF-01 nasceram em
    `public` por engano — a decisão de arquitetura de 05/08/2026 pede um
    schema Postgres próprio (`documents`), no mesmo espírito de `support`/
    `data_studio` (ver ARCHITECTURE.md, PROJECT_CONTEXT.md Registro 2026-08-07).
    Idempotente: se já estiverem em `documents`, não faz nada. Preserva todos
    os dados, índices, sequências e FKs — ALTER TABLE ... SET SCHEMA não copia,
    só reclassifica. Só se aplica ao modo VPS (o SQLite local não tem esse
    conceito de schema)."""
    if storage_mode() == "local":
        log("Migração de schema: modo local (SQLite) não usa schemas — nada a migrar.")
        return {"ok": True, "migrated": []}
    conn = connect()
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS documents")
            to_move = []
            for table in _DOCUMENT_TABLES:
                cur.execute(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_schema = 'public' AND table_name = %s",
                    (table,),
                )
                if cur.fetchone():
                    to_move.append(table)
            if not to_move:
                log("Migração de schema: já está tudo em `documents` (nada a mover).")
                conn.commit()
                return {"ok": True, "migrated": []}
            log(f"Migração de schema: movendo {len(to_move)} tabela(s) de public para documents: {', '.join(to_move)}")
            for table in to_move:
                cur.execute(f"ALTER TABLE public.{table} SET SCHEMA documents")
        conn.commit()
        log("Migração de schema: concluída, dados preservados.")
        return {"ok": True, "migrated": to_move}
    except Exception as e:  # noqa: BLE001 - operação sensível: reportar e não mascarar
        conn.rollback()
        log(f"Migração de schema: falhou, nada foi alterado ({e}).")
        return {"ok": False, "error": str(e)}
    finally:
        close_connection(conn)


def get_transcript_raw_clean(transcription_id, user_id=None, admin_verified=False):
    """Fonte para o gate raw<->clean + formatacao: texto raw/clean de uma
    transcricao existente (fluxo de formatacao retroativa, Library/edicao).
    Devolve None se nao existir ou nao pertencer ao utilizador."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            cur.execute(
                "SELECT t.source_filename, t.language, x.raw_text, x.clean_text "
                "FROM transcriptions t LEFT JOIN transcript_texts x ON x.transcription_id = t.id "
                f"WHERE t.id = %s AND t.deleted_at IS NULL{own_sql}",
                [int(transcription_id)] + own_params,
            )
            row = cur.fetchone()
            if not row:
                return None
            return {"source_filename": row[0], "language": row[1], "raw_text": row[2], "clean_text": row[3]}
    finally:
        close_connection(conn)


def insert_document(record, log=print):
    """Persiste um documento estruturado gerado (hub + blocos + glossario +
    metricas). best-effort: devolve o id inserido ou None; nunca levanta.
    record = {transcription_id, user_id, engine, profile, title, objective,
              raw_clean_check_ok, blocks: [...], jargon: [...],
              processing_s, input_tokens, output_tokens}"""
    conn = None
    try:
        conn = connect()
        ensure_schema(conn)
        with conn.cursor() as cur:
            eng_id = _engine_id(cur, record.get("engine"))
            tid = record.get("transcription_id")
            owner = record.get("user_id")
            cur.execute(
                "INSERT INTO documents.structured_documents "
                "(transcription_id, user_id, engine_id, profile, title, objective, raw_clean_check_ok, host) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (int(tid) if tid is not None else None, int(owner) if owner is not None else None,
                 eng_id, record.get("profile") or "detalhado", record.get("title"),
                 record.get("objective"), record.get("raw_clean_check_ok"),
                 record.get("host") or socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
            for i, block in enumerate(record.get("blocks") or []):
                content = block.get("content")
                if isinstance(content, (list, dict)):
                    content = json.dumps(content, ensure_ascii=False)
                cur.execute(
                    "INSERT INTO documents.document_blocks "
                    "(document_id, block_key, position, block_type, heading, content, speaker, block_timestamp) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (new_id, block.get("id") or f"b{i + 1}", i, block.get("type") or "section",
                     block.get("heading"), content, block.get("speaker"), block.get("timestamp")),
                )
            for jg in (record.get("jargon") or []):
                cur.execute(
                    "INSERT INTO documents.document_glossary (document_id, term, meaning) VALUES (%s,%s,%s)",
                    (new_id, jg.get("term"), jg.get("meaning")),
                )
            cur.execute(
                "INSERT INTO documents.document_metrics (document_id, processing_s, input_tokens, output_tokens) "
                "VALUES (%s,%s,%s,%s)",
                (new_id, record.get("processing_s"), record.get("input_tokens"), record.get("output_tokens")),
            )
        conn.commit()
        where = "na base local (SQLite)" if storage_mode() == "local" else "no Postgres da VPS"
        log(f"DB: documento #{new_id} gravado {where}.")
        return new_id
    except Exception as e:  # noqa: BLE001 - best-effort, reportar e seguir
        log(f"DB: não gravou o documento ({e}).")
        return None
    finally:
        close_connection(conn)


def document_item(doc_id, user_id=None, admin_verified=False):
    """Um documento completo (hub + blocos ordenados + glossario + metricas).
    Mesmo isolamento por dono/admin que library_item."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            # _actor filtra por "t.user_id" (pensado p/ transcriptions); aqui a
            # tabela e' "d" — troca o prefixo do filtro pra bater com o alias.
            own_sql_d = own_sql.replace("t.user_id", "d.user_id")
            cur.execute(
                "SELECT d.id, d.created_at, d.edited_at, d.transcription_id, e.code AS engine, "
                "d.profile, d.title, d.objective, d.raw_clean_check_ok, "
                "m.processing_s, m.input_tokens, m.output_tokens "
                "FROM documents.structured_documents d "
                "LEFT JOIN engines e ON e.id = d.engine_id "
                "LEFT JOIN documents.document_metrics m ON m.document_id = d.id "
                f"WHERE d.id = %s AND d.deleted_at IS NULL{own_sql_d}",
                [int(doc_id)] + own_params,
            )
            rows = _rows_to_dicts(cur)
            if not rows:
                return None
            doc = rows[0]
            cur.execute(
                "SELECT block_key, block_type, heading, content, speaker, block_timestamp "
                "FROM documents.document_blocks WHERE document_id = %s ORDER BY position",
                (int(doc_id),),
            )
            doc["blocks"] = _rows_to_dicts(cur)
            cur.execute(
                "SELECT term, meaning FROM documents.document_glossary WHERE document_id = %s ORDER BY id",
                (int(doc_id),),
            )
            doc["jargon"] = _rows_to_dicts(cur)
            # notebook_note_id (fatia 4): ver comentário equivalente em library_item.
            cur.execute(
                "SELECT nn.id FROM notebooks.note_sources ns "
                "JOIN notebooks.notes nn ON nn.id = ns.note_id AND nn.deleted_at IS NULL "
                "WHERE ns.document_id = %s",
                (int(doc_id),),
            )
            note_row = cur.fetchone()
            doc["notebook_note_id"] = note_row[0] if note_row else None
        doc["created_at"] = _iso(doc["created_at"])
        doc["edited_at"] = _iso(doc["edited_at"])
        # numeric do Postgres vem como Decimal (nao serializa em JSON) —
        # mesma coercao que library_item/library_list ja fazem nas metricas.
        if doc.get("processing_s") is not None:
            doc["processing_s"] = float(doc["processing_s"])
        return doc
    finally:
        close_connection(conn)


def delete_document(doc_id, user_id=None, admin_verified=False):
    """Soft-delete: snapshot em documents_history + deleted_at. Só o dono ou admin."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_d = own_sql.replace("t.user_id", "d.user_id")
            cur.execute(f"SELECT 1 FROM documents.structured_documents d WHERE d.id = %s AND d.deleted_at IS NULL{own_sql_d}",
                        [int(doc_id)] + own_params)
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(_doc_snapshot_sql(), ("delete", int(doc_id)))
            cur.execute("UPDATE documents.structured_documents SET deleted_at = now() WHERE id = %s", (int(doc_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


# --------------------------------------------------------------------------
# ADF-02 (fatia 3) — fundacao `notebooks`: colecao padrao, arvore e nota
# vazia (ver docs/NOTEBOOK_ARCHITECTURE.md secoes 6, 7 e 14). Mesmo padrao de
# dono/admin (_actor) e soft-delete + snapshot de transcriptions/documents.
# Fora desta fatia: linhagem (note_sources), versoes, anotacoes, referencias,
# glossario, chat, exportacao — cada uma so' entra na sua propria fatia.
# --------------------------------------------------------------------------

DEFAULT_NOTEBOOK_TITLE = "Caderno padrão"


def notebook_ensure_default_collection(user_id, log=print):
    """Coleção padrão (kind='notebook', raiz) para o utilizador — criada na
    primeira gravação, nunca duplicada (idempotente por utilizador). A UI
    pode renomeá-la depois; o Caderno nunca fica sem destino para a primeira
    nota (secção 6 da arquitetura: "nunca inventa uma hierarquia invisível
    que o utilizador não consiga localizar depois" — esta é sempre visível
    na árvore, não escondida)."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "SELECT id FROM notebooks.collections "
                "WHERE kind = 'notebook' AND parent_id IS NULL AND deleted_at IS NULL "
                "AND (user_id = %s OR (%s IS NULL AND user_id IS NULL)) "
                "ORDER BY id LIMIT 1",
                (owner, owner),
            )
            row = cur.fetchone()
            if row:
                return row[0]
            cur.execute(
                "INSERT INTO notebooks.collections (user_id, parent_id, kind, title, host) "
                "VALUES (%s, NULL, 'notebook', %s, %s) RETURNING id",
                (owner, DEFAULT_NOTEBOOK_TITLE, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        log(f"Notebooks: coleção padrão #{new_id} criada.")
        return new_id
    finally:
        close_connection(conn)


def notebook_tree(user_id=None, admin_verified=False):
    """Árvore completa (coleções + notas, incluindo vazias) do utilizador —
    a UI monta a hierarquia no cliente a partir de parent_id/collection_id."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_c = own_sql.replace("t.user_id", "c.user_id")
            cur.execute(
                "SELECT c.id, c.parent_id, c.kind, c.title, c.position, c.created_at "
                "FROM notebooks.collections c "
                f"WHERE c.deleted_at IS NULL{own_sql_c} "
                "ORDER BY c.parent_id NULLS FIRST, c.position, c.id",
                own_params,
            )
            collections = _rows_to_dicts(cur)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                "SELECT n.id, n.collection_id, n.title, n.created_at, n.edited_at "
                "FROM notebooks.notes n "
                f"WHERE n.deleted_at IS NULL{own_sql_n} "
                "ORDER BY n.edited_at DESC NULLS LAST, n.created_at DESC",
                own_params,
            )
            notes = _rows_to_dicts(cur)
        for c in collections:
            c["created_at"] = _iso(c["created_at"])
        for n in notes:
            n["created_at"] = _iso(n["created_at"])
            n["edited_at"] = _iso(n["edited_at"])
        return {"collections": collections, "notes": notes}
    finally:
        close_connection(conn)


def notebook_collection_create(user_id, title, parent_id=None, kind="notebook", admin_verified=False):
    """Cria pasta/projeto/caderno/secção. parent_id (se houver) tem de
    pertencer ao mesmo dono — evita pendurar uma coleção na árvore de outra
    pessoa por engano de id."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_c = own_sql.replace("t.user_id", "c.user_id")
            if parent_id is not None:
                cur.execute(
                    f"SELECT 1 FROM notebooks.collections c WHERE c.id = %s AND c.deleted_at IS NULL{own_sql_c}",
                    [int(parent_id)] + own_params,
                )
                if not cur.fetchone():
                    return {"ok": False, "error": "parent_not_found"}
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.collections (user_id, parent_id, kind, title, host) "
                "VALUES (%s,%s,%s,%s,%s) RETURNING id",
                (owner, int(parent_id) if parent_id is not None else None,
                 kind, title, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        close_connection(conn)


def _notebook_descendant_ids(cur, root_id):
    """Todos os ids de coleções descendentes de root_id (inclusive), em
    memória — a árvore desta fatia é pequena e o SQLite local não tem
    WITH RECURSIVE garantido em todas as versões empacotadas."""
    ids = [int(root_id)]
    frontier = [int(root_id)]
    while frontier:
        placeholders = ",".join(["%s"] * len(frontier))
        cur.execute(
            f"SELECT id FROM notebooks.collections WHERE parent_id IN ({placeholders}) AND deleted_at IS NULL",
            frontier,
        )
        found = [r[0] for r in cur.fetchall()]
        ids.extend(found)
        frontier = found
    return ids


def notebook_collection_delete(collection_id, user_id=None, admin_verified=False):
    """Soft-delete em cascata: a coleção e todas as suas descendentes (e as
    notas dentro delas) são arquivadas — nunca apaga transcript/documento de
    origem (fora deste domínio). Cada linha apagada ganha snapshot próprio no
    histórico, igual ao resto do produto."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_c = own_sql.replace("t.user_id", "c.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.collections c WHERE c.id = %s AND c.deleted_at IS NULL{own_sql_c}",
                [int(collection_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            coll_ids = _notebook_descendant_ids(cur, collection_id)
            placeholders = ",".join(["%s"] * len(coll_ids))
            cur.execute(
                f"SELECT id FROM notebooks.notes WHERE collection_id IN ({placeholders}) AND deleted_at IS NULL",
                coll_ids,
            )
            note_ids = [r[0] for r in cur.fetchall()]
            for nid in note_ids:
                cur.execute(NOTEBOOK_NOTE_SNAPSHOT_JOIN, ("delete", nid))
                cur.execute("UPDATE notebooks.notes SET deleted_at = now() WHERE id = %s", (nid,))
            # Filhos primeiro, raiz por último (mantém o snapshot legível).
            for cid in reversed(coll_ids):
                cur.execute(NOTEBOOK_COLLECTION_SNAPSHOT_JOIN, ("delete", cid))
                cur.execute("UPDATE notebooks.collections SET deleted_at = now() WHERE id = %s", (cid,))
        conn.commit()
        return {"ok": True, "collections": len(coll_ids), "notes": len(note_ids)}
    finally:
        close_connection(conn)


def notebook_note_create(user_id, collection_id, title=None, body="", admin_verified=False):
    """Nota vazia (fatia 3 — sem estrutura rica ainda: body é texto simples).
    collection_id tem de pertencer ao dono."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_c = own_sql.replace("t.user_id", "c.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.collections c WHERE c.id = %s AND c.deleted_at IS NULL{own_sql_c}",
                [int(collection_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "collection_not_found"}
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.notes (user_id, collection_id, title, host) VALUES (%s,%s,%s,%s) RETURNING id",
                (owner, int(collection_id), title, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO notebooks.note_contents (note_id, body) VALUES (%s,%s)",
                (new_id, body or ""),
            )
        conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        close_connection(conn)


def notebook_note_item(note_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                "SELECT n.id, n.created_at, n.edited_at, n.collection_id, n.title, nc.body "
                "FROM notebooks.notes n "
                "LEFT JOIN notebooks.note_contents nc ON nc.note_id = n.id "
                f"WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            rows = _rows_to_dicts(cur)
            if not rows:
                return None
            note = rows[0]
        note["created_at"] = _iso(note["created_at"])
        note["edited_at"] = _iso(note["edited_at"])
        return note
    finally:
        close_connection(conn)


def notebook_note_open(note_id, user_id=None, admin_verified=False):
    """Análise arquitetural 2026-08-13, fase B: abrir uma nota disparava 6
    processos/handshakes separados (item + anotações + referências + links +
    keywords + glossário) — cada `notebook_*_list()` acima abre e fecha a
    SUA PRÓPRIA ligação. Esta função faz o mesmo trabalho numa única ligação
    e num único round-trip pelo túnel SSH, devolvendo tudo de uma vez.
    Sem side-effects, sem escrita — pode ser chamada com segurança sempre
    que uma nota é aberta, incluindo em cache."""
    conn = connect()
    try:
        ensure_schema(conn)
        note_id = int(note_id)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)

            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                "SELECT n.id, n.created_at, n.edited_at, n.collection_id, n.title, nc.body "
                "FROM notebooks.notes n "
                "LEFT JOIN notebooks.note_contents nc ON nc.note_id = n.id "
                f"WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [note_id] + own_params,
            )
            note_rows = _rows_to_dicts(cur)
            if not note_rows:
                return None
            note = note_rows[0]
            note["created_at"] = _iso(note["created_at"])
            note["edited_at"] = _iso(note["edited_at"])

            own_sql_a = own_sql.replace("t.user_id", "a.user_id")
            cur.execute(
                "SELECT a.id, a.block_id, a.start_offset, a.end_offset, a.selected_text, "
                "a.context_snippet, a.body, a.status, a.resolved_at, a.created_at "
                "FROM notebooks.annotations a "
                f"WHERE a.note_id = %s AND a.deleted_at IS NULL{own_sql_a} "
                "ORDER BY a.created_at",
                [note_id] + own_params,
            )
            annotations = _rows_to_dicts(cur)
            for r in annotations:
                r["created_at"] = _iso(r["created_at"])
                r["resolved_at"] = _iso(r["resolved_at"])

            own_sql_r = own_sql.replace("t.user_id", "r.user_id")
            cur.execute(
                "SELECT r.id, r.title, r.url, r.note_text, r.created_at "
                "FROM notebooks.note_references r "
                f"WHERE r.note_id = %s AND r.deleted_at IS NULL{own_sql_r} "
                "ORDER BY r.created_at",
                [note_id] + own_params,
            )
            references = _rows_to_dicts(cur)
            for r in references:
                r["created_at"] = _iso(r["created_at"])

            own_sql_l = own_sql.replace("t.user_id", "l.user_id")
            cur.execute(
                "SELECT l.id, l.to_note_id AS note_id, n2.title, l.created_at "
                "FROM notebooks.note_links l "
                "JOIN notebooks.notes n2 ON n2.id = l.to_note_id "
                f"WHERE l.from_note_id = %s AND l.deleted_at IS NULL{own_sql_l} "
                "ORDER BY l.created_at",
                [note_id] + own_params,
            )
            outgoing = _rows_to_dicts(cur)
            cur.execute(
                "SELECT l.id, l.from_note_id AS note_id, n2.title, l.created_at "
                "FROM notebooks.note_links l "
                "JOIN notebooks.notes n2 ON n2.id = l.from_note_id "
                f"WHERE l.to_note_id = %s AND l.deleted_at IS NULL{own_sql_l} "
                "ORDER BY l.created_at",
                [note_id] + own_params,
            )
            incoming = _rows_to_dicts(cur)
            for row in outgoing + incoming:
                row["created_at"] = _iso(row["created_at"])

            own_sql_k = own_sql.replace("t.user_id", "k.user_id")
            cur.execute(
                "SELECT k.id, k.term, k.created_at FROM notebooks.keywords k "
                f"WHERE k.note_id = %s AND k.deleted_at IS NULL{own_sql_k} ORDER BY k.created_at",
                [note_id] + own_params,
            )
            keywords = _rows_to_dicts(cur)
            for r in keywords:
                r["created_at"] = _iso(r["created_at"])

            own_sql_g = own_sql.replace("t.user_id", "g.user_id")
            cur.execute(
                "SELECT g.id, g.term, g.definition, g.source, g.language, g.created_at "
                "FROM notebooks.glossary_entries g "
                f"WHERE g.note_id = %s AND g.deleted_at IS NULL{own_sql_g} ORDER BY g.created_at",
                [note_id] + own_params,
            )
            glossary = _rows_to_dicts(cur)
            for r in glossary:
                r["created_at"] = _iso(r["created_at"])

        return {
            "note": note,
            "annotations": annotations,
            "references": references,
            "links": {"outgoing": outgoing, "incoming": incoming},
            "keywords": keywords,
            "glossary": glossary,
        }
    finally:
        close_connection(conn)


def notebook_note_update(note_id, user_id=None, title=None, body=None, admin_verified=False):
    """Edita título/corpo no lugar (padrão do produto — sem versionar ainda;
    note_versions é fatia futura). Snapshot no histórico ANTES de alterar."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(NOTEBOOK_NOTE_SNAPSHOT_JOIN, ("update", int(note_id)))
            if title is not None:
                cur.execute("UPDATE notebooks.notes SET title = %s, edited_at = now() WHERE id = %s",
                            (title, int(note_id)))
            else:
                cur.execute("UPDATE notebooks.notes SET edited_at = now() WHERE id = %s", (int(note_id),))
            if body is not None:
                cur.execute("UPDATE notebooks.note_contents SET body = %s WHERE note_id = %s",
                            (body, int(note_id)))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


def notebook_note_delete(note_id, user_id=None, admin_verified=False):
    """Soft-delete: snapshot em notes_history + deleted_at. Só o dono ou admin."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(NOTEBOOK_NOTE_SNAPSHOT_JOIN, ("delete", int(note_id)))
            cur.execute("UPDATE notebooks.notes SET deleted_at = now() WHERE id = %s", (int(note_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


# --------------------------------------------------------------------------
# ADF-02 (fatia 4, 09/08/2026) — "Passagem controlada": Salvar no Caderno,
# seleção de destino, linhagem e abertura (ver NOTEBOOK_ARCHITECTURE.md
# secção 3, "Regra de passagem"). NUNCA é referência viva: o conteúdo é
# COPIADO para notebooks.note_contents no momento da gravação; regenerar a
# prévia em `documents` depois disto nunca sobrescreve a nota.
# --------------------------------------------------------------------------

def _render_blocks_as_text(blocks):
    """Serialização simples (título + corpo) dos blocos do documento —
    conteúdo inicial da nota nesta fatia. blocks: lista de (heading, content)
    já na ordem de leitura (document_blocks.position)."""
    parts = []
    for heading, content in blocks:
        if heading:
            parts.append(f"## {heading}")
        if content:
            parts.append(content)
    return "\n\n".join(parts)


def notebook_note_for_document(document_id, user_id=None, admin_verified=False):
    """Id da nota já criada a partir deste documento (ou None) — a UI decide
    "Salvar no Caderno" vs "Abrir no Caderno" sem repetir a lógica de
    document_item/library_item (usado quando só se tem o document_id à mão,
    ex.: o painel pós-transcrição)."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                "SELECT n.id FROM notebooks.note_sources ns "
                "JOIN notebooks.notes n ON n.id = ns.note_id "
                f"WHERE ns.document_id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(document_id)] + own_params,
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        close_connection(conn)


def notebook_save_document_as_note(document_id, user_id=None, collection_id=None, admin_verified=False):
    """'Salvar no Caderno': cria uma nota no destino escolhido (ou na coleção
    padrão, se nenhum for indicado), copia o conteúdo ATUAL do documento
    estruturado e regista a linhagem (note_sources). Idempotente: se já
    existir uma nota ativa para este documento (deste dono), devolve-a em vez
    de duplicar — clique repetido no botão nunca cria duas notas."""
    existing = notebook_note_for_document(document_id, user_id=user_id, admin_verified=admin_verified)
    if existing:
        return {"ok": True, "id": existing, "existed": True}

    target_collection_id = collection_id
    if target_collection_id is None:
        target_collection_id = notebook_ensure_default_collection(user_id)

    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_c = own_sql.replace("t.user_id", "c.user_id")
            own_sql_d = own_sql.replace("t.user_id", "d.user_id")

            cur.execute(
                f"SELECT 1 FROM notebooks.collections c WHERE c.id = %s AND c.deleted_at IS NULL{own_sql_c}",
                [int(target_collection_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "collection_not_found"}

            cur.execute(
                "SELECT d.id, d.transcription_id, d.title "
                "FROM documents.structured_documents d "
                f"WHERE d.id = %s AND d.deleted_at IS NULL{own_sql_d}",
                [int(document_id)] + own_params,
            )
            doc_row = cur.fetchone()
            if not doc_row:
                return {"ok": False, "error": "document_not_found"}
            _doc_id, transcription_id, doc_title = doc_row

            cur.execute(
                "SELECT heading, content FROM documents.document_blocks "
                "WHERE document_id = %s ORDER BY position",
                (int(document_id),),
            )
            body = _render_blocks_as_text(cur.fetchall())

            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.notes (user_id, collection_id, title, host) VALUES (%s,%s,%s,%s) RETURNING id",
                (owner, int(target_collection_id), doc_title, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO notebooks.note_contents (note_id, body) VALUES (%s,%s)",
                (new_id, body),
            )
            cur.execute(
                "INSERT INTO notebooks.note_sources (note_id, transcription_id, document_id) VALUES (%s,%s,%s)",
                (new_id, int(transcription_id) if transcription_id is not None else None, int(document_id)),
            )
        conn.commit()
        return {"ok": True, "id": new_id, "existed": False}
    finally:
        close_connection(conn)


# --------------------------------------------------------------------------
# ADF-02 (fatia 5, 11/08/2026) — "Editor rico essencial" (ver NOTEBOOK_
# ARCHITECTURE.md secção 14 item 5): edição contínua, formatação e
# salvamento já existiam desde a fatia 3 (notebook_note_update). O que entra
# aqui é só "versões": um ponto de recuperação explícito, guardado a pedido
# do utilizador (botão "Salvar versão" ou marco natural como fechar a nota),
# nunca a cada autosave — senão a lista de versões vira ruído em minutos.
# --------------------------------------------------------------------------

def notebook_note_version_create(note_id, user_id=None, admin_verified=False):
    """Snapshot manual do estado ATUAL da nota (título + corpo)."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            owner = int(user_id) if user_id is not None else None
            cur.execute(NOTEBOOK_NOTE_VERSION_SNAPSHOT_JOIN, (owner, int(note_id)))
            new_id = cur.fetchone()[0]
        conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        close_connection(conn)


def notebook_note_versions(note_id, user_id=None, admin_verified=False):
    """Lista leve (sem o corpo — só quem vai restaurar precisa dele) para o
    painel de histórico da nota."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return None
            cur.execute(
                "SELECT id, created_at, title FROM notebooks.note_versions "
                "WHERE note_id = %s ORDER BY created_at DESC, id DESC",
                (int(note_id),),
            )
            versions = _rows_to_dicts(cur)
        for v in versions:
            v["created_at"] = _iso(v["created_at"])
        return versions
    finally:
        close_connection(conn)


def notebook_note_version_restore(note_id, version_id, user_id=None, admin_verified=False):
    """Recupera uma versão antiga. O estado atual é versionado ANTES de ser
    substituído — o restauro em si nunca é um beco sem saída."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(
                "SELECT title, body FROM notebooks.note_versions WHERE id = %s AND note_id = %s",
                (int(version_id), int(note_id)),
            )
            row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "version_not_found"}
            old_title, old_body = row
            owner = int(user_id) if user_id is not None else None
            cur.execute(NOTEBOOK_NOTE_VERSION_SNAPSHOT_JOIN, (owner, int(note_id)))
            cur.execute(NOTEBOOK_NOTE_SNAPSHOT_JOIN, ("update", int(note_id)))
            cur.execute("UPDATE notebooks.notes SET title = %s, edited_at = now() WHERE id = %s",
                        (old_title, int(note_id)))
            cur.execute("UPDATE notebooks.note_contents SET body = %s WHERE note_id = %s",
                        (old_body, int(note_id)))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


# --------------------------------------------------------------------------
# ADF-02 (fatia 6, 11/08/2026) — "Anotações e referências" (secção 9 e 14
# item 6): comentário/destaque ancorado a um trecho da nota (âncora híbrida:
# bloco + offsets + texto + contexto), e referência de estudo solta (título/
# URL/nota) associada à nota. Soft-delete + histórico flat, mesmo padrão do
# resto do domínio.
# --------------------------------------------------------------------------

def notebook_annotation_create(note_id, body, user_id=None, block_id=None, start_offset=None,
                                end_offset=None, selected_text=None, context_snippet=None,
                                admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "note_not_found"}
            if not (body or "").strip():
                return {"ok": False, "error": "empty_body"}
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.annotations "
                "(note_id, user_id, block_id, start_offset, end_offset, selected_text, context_snippet, body, host) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (int(note_id), owner, block_id, start_offset, end_offset, selected_text,
                 context_snippet, body, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        close_connection(conn)


def notebook_annotation_list(note_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_a = own_sql.replace("t.user_id", "a.user_id")
            cur.execute(
                "SELECT a.id, a.block_id, a.start_offset, a.end_offset, a.selected_text, "
                "a.context_snippet, a.body, a.status, a.resolved_at, a.created_at "
                "FROM notebooks.annotations a "
                f"WHERE a.note_id = %s AND a.deleted_at IS NULL{own_sql_a} "
                "ORDER BY a.created_at",
                [int(note_id)] + own_params,
            )
            rows = _rows_to_dicts(cur)
        for r in rows:
            r["created_at"] = _iso(r["created_at"])
            r["resolved_at"] = _iso(r["resolved_at"])
        return rows
    finally:
        close_connection(conn)


def notebook_annotation_resolve(annotation_id, user_id=None, resolved=True, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_a = own_sql.replace("t.user_id", "a.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.annotations a WHERE a.id = %s AND a.deleted_at IS NULL{own_sql_a}",
                [int(annotation_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            if resolved:
                cur.execute(
                    "UPDATE notebooks.annotations SET resolved_at = now(), edited_at = now() WHERE id = %s",
                    (int(annotation_id),))
            else:
                cur.execute(
                    "UPDATE notebooks.annotations SET resolved_at = NULL, edited_at = now() WHERE id = %s",
                    (int(annotation_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


def notebook_annotation_delete(annotation_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_a = own_sql.replace("t.user_id", "a.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.annotations a WHERE a.id = %s AND a.deleted_at IS NULL{own_sql_a}",
                [int(annotation_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(NOTEBOOK_ANNOTATION_SNAPSHOT_JOIN, ("delete", int(annotation_id)))
            cur.execute("UPDATE notebooks.annotations SET deleted_at = now() WHERE id = %s", (int(annotation_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


def notebook_reference_create(note_id, title=None, url=None, note_text=None, user_id=None,
                               admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "note_not_found"}
            if not ((title or "").strip() or (url or "").strip()):
                return {"ok": False, "error": "empty_reference"}
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.note_references (note_id, user_id, title, url, note_text, host) "
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (int(note_id), owner, title, url, note_text, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        close_connection(conn)


def notebook_reference_list(note_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_r = own_sql.replace("t.user_id", "r.user_id")
            cur.execute(
                "SELECT r.id, r.title, r.url, r.note_text, r.created_at "
                "FROM notebooks.note_references r "
                f"WHERE r.note_id = %s AND r.deleted_at IS NULL{own_sql_r} "
                "ORDER BY r.created_at",
                [int(note_id)] + own_params,
            )
            rows = _rows_to_dicts(cur)
        for r in rows:
            r["created_at"] = _iso(r["created_at"])
        return rows
    finally:
        close_connection(conn)


def notebook_reference_delete(reference_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_r = own_sql.replace("t.user_id", "r.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.note_references r WHERE r.id = %s AND r.deleted_at IS NULL{own_sql_r}",
                [int(reference_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(NOTEBOOK_NOTE_REFERENCE_SNAPSHOT_JOIN, ("delete", int(reference_id)))
            cur.execute("UPDATE notebooks.note_references SET deleted_at = now() WHERE id = %s",
                        (int(reference_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


# --------------------------------------------------------------------------
# Backlinks (11/08/2026, ver PROJECT_CONTEXT.md secção 12, Registro do mesmo
# dia) — ligação direcionada nota→nota, escolhida explicitamente pelo
# utilizador (sem parsing de texto). `notebook_links` devolve as duas
# direções já resolvidas (título da outra nota incluído) para a UI não
# precisar de uma segunda chamada.
# --------------------------------------------------------------------------
def notebook_link_create(from_note_id, to_note_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(from_note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "note_not_found"}
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(to_note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "target_not_found"}
            if int(from_note_id) == int(to_note_id):
                return {"ok": False, "error": "self_link"}
            own_sql_l = own_sql.replace("t.user_id", "l.user_id")
            cur.execute(
                "SELECT 1 FROM notebooks.note_links l "
                f"WHERE l.from_note_id = %s AND l.to_note_id = %s AND l.deleted_at IS NULL{own_sql_l}",
                [int(from_note_id), int(to_note_id)] + own_params,
            )
            if cur.fetchone():
                return {"ok": False, "error": "already_linked"}
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.note_links (from_note_id, to_note_id, user_id, host) "
                "VALUES (%s,%s,%s,%s) RETURNING id",
                (int(from_note_id), int(to_note_id), owner, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        close_connection(conn)


def notebook_links(note_id, user_id=None, admin_verified=False):
    """Devolve {"outgoing": [...], "incoming": [...]}: outgoing são as notas
    para onde ESTA nota aponta; incoming (os "backlinks") são as notas que
    apontam PARA esta — calculado por leitura inversa, não gravado em dobro."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_l = own_sql.replace("t.user_id", "l.user_id")
            cur.execute(
                "SELECT l.id, l.to_note_id AS note_id, n.title, l.created_at "
                "FROM notebooks.note_links l "
                "JOIN notebooks.notes n ON n.id = l.to_note_id "
                f"WHERE l.from_note_id = %s AND l.deleted_at IS NULL{own_sql_l} "
                "ORDER BY l.created_at",
                [int(note_id)] + own_params,
            )
            outgoing = _rows_to_dicts(cur)
            cur.execute(
                "SELECT l.id, l.from_note_id AS note_id, n.title, l.created_at "
                "FROM notebooks.note_links l "
                "JOIN notebooks.notes n ON n.id = l.from_note_id "
                f"WHERE l.to_note_id = %s AND l.deleted_at IS NULL{own_sql_l} "
                "ORDER BY l.created_at",
                [int(note_id)] + own_params,
            )
            incoming = _rows_to_dicts(cur)
        for row in outgoing + incoming:
            row["created_at"] = _iso(row["created_at"])
        return {"outgoing": outgoing, "incoming": incoming}
    finally:
        close_connection(conn)


def notebook_link_delete(link_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_l = own_sql.replace("t.user_id", "l.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.note_links l WHERE l.id = %s AND l.deleted_at IS NULL{own_sql_l}",
                [int(link_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(NOTEBOOK_NOTE_LINK_SNAPSHOT_JOIN, ("delete", int(link_id)))
            cur.execute("UPDATE notebooks.note_links SET deleted_at = now() WHERE id = %s",
                        (int(link_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


# --------------------------------------------------------------------------
# ADF-02 (fatia 7, 11/08/2026) — "Dicionário e glossário" (secção 10 e 14
# item 7): palavra-chave pessoal (`keywords`) e definição vinculada à nota
# (`glossary_entries`). `source` fica sempre 'manual' nesta passagem — sem
# provedor de dicionário externo ligado ainda.
# --------------------------------------------------------------------------

def notebook_keyword_create(note_id, term, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "note_not_found"}
            term = (term or "").strip()
            if not term:
                return {"ok": False, "error": "empty_term"}
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.keywords (note_id, user_id, term, host) VALUES (%s,%s,%s,%s) RETURNING id",
                (int(note_id), owner, term, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        close_connection(conn)


def notebook_keyword_list(note_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_k = own_sql.replace("t.user_id", "k.user_id")
            cur.execute(
                "SELECT k.id, k.term, k.created_at FROM notebooks.keywords k "
                f"WHERE k.note_id = %s AND k.deleted_at IS NULL{own_sql_k} ORDER BY k.created_at",
                [int(note_id)] + own_params,
            )
            rows = _rows_to_dicts(cur)
        for r in rows:
            r["created_at"] = _iso(r["created_at"])
        return rows
    finally:
        close_connection(conn)


def notebook_keyword_delete(keyword_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_k = own_sql.replace("t.user_id", "k.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.keywords k WHERE k.id = %s AND k.deleted_at IS NULL{own_sql_k}",
                [int(keyword_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(NOTEBOOK_KEYWORD_SNAPSHOT_JOIN, ("delete", int(keyword_id)))
            cur.execute("UPDATE notebooks.keywords SET deleted_at = now() WHERE id = %s", (int(keyword_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


def notebook_glossary_create(note_id, term, definition, source=None, language=None, user_id=None,
                              admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "note_not_found"}
            term = (term or "").strip()
            definition = (definition or "").strip()
            if not term or not definition:
                return {"ok": False, "error": "empty_entry"}
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.glossary_entries (note_id, user_id, term, definition, source, language, host) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (int(note_id), owner, term, definition, source or "manual", language, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
        return {"ok": True, "id": new_id}
    finally:
        close_connection(conn)


def notebook_glossary_list(note_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_g = own_sql.replace("t.user_id", "g.user_id")
            cur.execute(
                "SELECT g.id, g.term, g.definition, g.source, g.language, g.created_at "
                "FROM notebooks.glossary_entries g "
                f"WHERE g.note_id = %s AND g.deleted_at IS NULL{own_sql_g} ORDER BY g.created_at",
                [int(note_id)] + own_params,
            )
            rows = _rows_to_dicts(cur)
        for r in rows:
            r["created_at"] = _iso(r["created_at"])
        return rows
    finally:
        close_connection(conn)


def notebook_glossary_delete(entry_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_g = own_sql.replace("t.user_id", "g.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.glossary_entries g WHERE g.id = %s AND g.deleted_at IS NULL{own_sql_g}",
                [int(entry_id)] + own_params,
            )
            if not cur.fetchone():
                return {"ok": False, "error": "not_found"}
            cur.execute(NOTEBOOK_GLOSSARY_SNAPSHOT_JOIN, ("delete", int(entry_id)))
            cur.execute("UPDATE notebooks.glossary_entries SET deleted_at = now() WHERE id = %s", (int(entry_id),))
        conn.commit()
        return {"ok": True}
    finally:
        close_connection(conn)


# --------------------------------------------------------------------------
# ADF-02 (fatia 8, 11/08/2026) — "Exportação e pacote para IA" (secção 12 e
# 14 item 8). O conteúdo é sempre montado on-the-fly a partir das camadas
# escolhidas — nada de silencioso: só entra o que foi pedido explicitamente.
# --------------------------------------------------------------------------

_HTML_LI_OPEN_RE = re.compile(r"(?i)<li[^>]*>")
_HTML_BR_RE = re.compile(r"(?i)<br\s*/?>")
_HTML_BLOCK_END_RE = re.compile(r"(?i)</(p|h1|h2|h3|li|div)\s*>")
_HTML_TAG_RE = re.compile(r"<[^>]+>")

NOTEBOOK_EXPORT_LAYERS = ("body", "annotations", "references", "glossary", "links", "lineage")


def _notebook_html_to_text(raw_html):
    """Conversão simples de HTML (o conteúdo de UM bloco, ou um blob antigo
    inteiro) para texto simples — suficiente para exportação/portabilidade;
    não tenta preservar formatação, só a leitura linear do conteúdo."""
    if not raw_html:
        return ""
    t = _HTML_LI_OPEN_RE.sub("- ", raw_html)
    t = _HTML_BR_RE.sub("\n", t)
    t = _HTML_BLOCK_END_RE.sub("\n", t)
    t = _HTML_TAG_RE.sub("", t)
    t = _html_unescape(t)
    out, blank = [], 0
    for ln in (ln.strip() for ln in t.splitlines()):
        if ln:
            blank = 0
            out.append(ln)
        else:
            blank += 1
            if blank <= 1:
                out.append(ln)
    return "\n".join(out).strip()


_NOTEBOOK_HEADING_MD = {"H1": "# ", "H2": "## ", "H3": "### "}


def _notebook_body_to_text(body):
    """Corpo da nota → texto simples portátil. Aceita os três formatos que
    `note_contents.body` pode ter (frontend decide qual escrever; o worker só
    precisa saber LER todos, retrocompatibilidade nunca quebra uma nota
    antiga): (1) JSON de blocos com id estável (formato atual, fatia 5+,
    11/08/2026) — cada bloco vira uma secção/parágrafo/lista; (2) blob de
    HTML solto (fatias 5–8 antes desta mudança); (3) texto simples (fatias
    3/4, ou nota vinda de 'Salvar no Caderno')."""
    if not body:
        return ""
    s = body.strip()
    if s.startswith("["):
        try:
            blocks = json.loads(s)
        except (ValueError, TypeError):
            blocks = None
        if isinstance(blocks, list):
            parts = []
            for b in blocks:
                if not isinstance(b, dict):
                    continue
                tag = (b.get("tag") or "P").upper()
                text = _notebook_html_to_text(b.get("html") or "")
                if not text:
                    continue
                prefix = _NOTEBOOK_HEADING_MD.get(tag, "")
                parts.append(f"{prefix}{text}" if prefix else text)
            return "\n\n".join(parts)
    return _notebook_html_to_text(body)


# Pedido do Leonardo (2026-08-14): a exportação (.md/.docx/prompt) tem de
# refletir o idioma da REUNIÃO/TRANSCRIÇÃO de origem — se a transcrição foi
# em inglês, os rótulos de secção e o prompt para IA saem em inglês; se foi
# em espanhol, em espanhol; senão (nota manual sem proveniência, ou idioma
# não coberto) cai no padrão em português, que é o idioma principal da app.
# Cobrimos só pt/en/es porque são os 3 idiomas que a própria interface do
# UpexNote já suporta (`i18n.ts`) — não faz sentido gerar rótulos estruturais
# num idioma que a app nem mostra a si própria.
_NOTEBOOK_EXPORT_LABELS = {
    "pt": {
        "annotations": "Anotações", "references": "Referências", "glossary": "Glossário",
        "keywords": "Palavras-chave", "links": "Notas ligadas", "lineage": "Proveniência",
        "source_transcription": "Transcrição de origem", "source_document": "Documento estruturado de origem",
        "resolved": " (resolvida)",
    },
    "en": {
        "annotations": "Annotations", "references": "References", "glossary": "Glossary",
        "keywords": "Keywords", "links": "Linked notes", "lineage": "Provenance",
        "source_transcription": "Source transcription", "source_document": "Source structured document",
        "resolved": " (resolved)",
    },
    "es": {
        "annotations": "Anotaciones", "references": "Referencias", "glossary": "Glosario",
        "keywords": "Palabras clave", "links": "Notas enlazadas", "lineage": "Procedencia",
        "source_transcription": "Transcripción de origen", "source_document": "Documento estructurado de origen",
        "resolved": " (resuelta)",
    },
}


def _normalize_notebook_lang(raw):
    code = (raw or "").strip().lower()
    if code.startswith("en"):
        return "en"
    if code.startswith("es"):
        return "es"
    return "pt"


def _notebook_note_language(note_id, conn=None):
    """Idioma herdado da transcrição de origem da nota (via note_sources ->
    transcription_id direto, ou -> document_id -> structured_documents ->
    transcription_id). None se a nota não tiver proveniência (ex.: criada
    manualmente, "Salvar no Caderno" sem origem) — quem chama decide o
    padrão nesse caso."""
    owns_conn = conn is None
    if owns_conn:
        conn = connect()
    try:
        if owns_conn:
            ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT transcription_id, document_id FROM notebooks.note_sources WHERE note_id = %s",
                (int(note_id),),
            )
            row = cur.fetchone()
            if not row:
                return None
            transcription_id, document_id = row
            if transcription_id:
                cur.execute("SELECT language FROM transcriptions WHERE id = %s", (transcription_id,))
                r = cur.fetchone()
                if r and r[0]:
                    return r[0]
            if document_id:
                cur.execute(
                    "SELECT t.language FROM documents.structured_documents d "
                    "LEFT JOIN transcriptions t ON t.id = d.transcription_id WHERE d.id = %s",
                    (document_id,),
                )
                r = cur.fetchone()
                if r and r[0]:
                    return r[0]
            return None
    finally:
        if owns_conn:
            close_connection(conn)


def notebook_note_export(note_id, layers=None, fmt="markdown", user_id=None, admin_verified=False):
    """Monta o conteúdo a partir das camadas escolhidas e regista só os
    METADADOS no histórico (notebooks.exports — formato + camadas); o
    conteúdo em si nunca é guardado no banco, é gerado a cada pedido."""
    layers = [l for l in (layers or ["body"]) if l in NOTEBOOK_EXPORT_LAYERS] or ["body"]
    item = notebook_note_item(note_id, user_id=user_id, admin_verified=admin_verified)
    if item is None:
        return {"ok": False, "error": "not_found"}

    lang = _normalize_notebook_lang(_notebook_note_language(note_id))
    L = _NOTEBOOK_EXPORT_LABELS[lang]

    parts = [f"# {item.get('title') or DEFAULT_NOTEBOOK_TITLE}"]
    if "body" in layers:
        parts.append(_notebook_body_to_text(item.get("body")))
    if "annotations" in layers:
        annotations = notebook_annotation_list(note_id, user_id=user_id, admin_verified=admin_verified)
        if annotations:
            lines = [f"## {L['annotations']}"]
            for a in annotations:
                quote = f' — "{a["selected_text"]}"' if a.get("selected_text") else ""
                status = L["resolved"] if a.get("resolved_at") else ""
                lines.append(f"- {a['body']}{quote}{status}")
            parts.append("\n".join(lines))
    if "references" in layers:
        refs = notebook_reference_list(note_id, user_id=user_id, admin_verified=admin_verified)
        if refs:
            lines = [f"## {L['references']}"]
            for r in refs:
                line = r.get("title") or r.get("url") or ""
                if r.get("url") and r.get("title"):
                    line += f" — {r['url']}"
                if r.get("note_text"):
                    line += f" ({r['note_text']})"
                lines.append(f"- {line}")
            parts.append("\n".join(lines))
    if "glossary" in layers:
        gloss = notebook_glossary_list(note_id, user_id=user_id, admin_verified=admin_verified)
        kws = notebook_keyword_list(note_id, user_id=user_id, admin_verified=admin_verified)
        if gloss:
            lines = [f"## {L['glossary']}"] + [f"- {g['term']}: {g['definition']}" for g in gloss]
            parts.append("\n".join(lines))
        if kws:
            parts.append(f"## {L['keywords']}\n" + ", ".join(k["term"] for k in kws))
    if "links" in layers:
        links = notebook_links(note_id, user_id=user_id, admin_verified=admin_verified)
        out, inc = links.get("outgoing") or [], links.get("incoming") or []
        if out or inc:
            lines = [f"## {L['links']}"]
            for l in out:
                lines.append(f"- → {l.get('title') or DEFAULT_NOTEBOOK_TITLE}")
            for l in inc:
                lines.append(f"- ← {l.get('title') or DEFAULT_NOTEBOOK_TITLE}")
            parts.append("\n".join(lines))
    if "lineage" in layers:
        conn = connect()
        try:
            ensure_schema(conn)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT transcription_id, document_id FROM notebooks.note_sources WHERE note_id = %s",
                    (int(note_id),),
                )
                row = cur.fetchone()
        finally:
            close_connection(conn)
        if row and (row[0] or row[1]):
            lines = [f"## {L['lineage']}"]
            if row[0]:
                lines.append(f"{L['source_transcription']}: #{row[0]}")
            if row[1]:
                lines.append(f"{L['source_document']}: #{row[1]}")
            parts.append("\n".join(lines))

    content = "\n\n".join(p for p in parts if p and p.strip())

    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.exports (note_id, user_id, format, layers, host) VALUES (%s,%s,%s,%s,%s)",
                (int(note_id), owner, fmt, ",".join(layers), socket.gethostname()),
            )
        conn.commit()
    finally:
        close_connection(conn)

    return {"ok": True, "content": content, "layers": layers, "language": lang}


def notebook_note_context_package(note_id, layers=None, user_id=None, admin_verified=False):
    """'Pacote para IA': mesmas camadas do export, empacotadas com um
    manifesto legível por máquina e um prompt legível por pessoas. Ao
    contrário de `exports`, manifesto+prompt SÃO persistidos (são texto
    simples pequeno — não é o "binário" que a arquitetura pede para não
    guardar), porque o utilizador pode querer reabrir/reenviar depois."""
    export = notebook_note_export(note_id, layers=layers, fmt="context_package",
                                   user_id=user_id, admin_verified=admin_verified)
    if not export.get("ok"):
        return export
    item = notebook_note_item(note_id, user_id=user_id, admin_verified=admin_verified)
    title = (item or {}).get("title") or DEFAULT_NOTEBOOK_TITLE
    lang = export.get("language") or "pt"
    manifest = json.dumps({
        "note_id": int(note_id),
        "title": title,
        "layers": export["layers"],
        "generated_by": "UpexNote",
    }, ensure_ascii=False)
    # Pedido do Leonardo (2026-08-14): isto não pode ser só um aviso de
    # "não invente" seguido do conteúdo cru — tem de ser um prompt de
    # verdade, com instruções de leitura, uma mensagem de abertura pronta
    # (que a IA deve adaptar, não copiar literalmente) que reconhece o
    # UpexNote pelo nome, e sugestões padrão para o utilizador continuar.
    # Isto vale para QUALQUER IA (ChatGPT, Claude, Gemini, etc.) — por isso
    # são instruções em texto simples, sem depender de formatos
    # proprietários de "system prompt".
    #
    # Pedido do Leonardo (2026-08-14, seguinte): o idioma do prompt (e do
    # documento exportado) tem de refletir o idioma da reunião/transcrição
    # de origem — não pode ficar preso ao português. `lang` já foi
    # calculado acima a partir de `_notebook_note_language()`.
    prompt_templates = {
        "pt": """INSTRUÇÕES PARA A IA — lê isto com atenção, até ao fim, antes de responderes.

Isto é um pacote de contexto gerado pelo UpexNote a partir de uma nota pessoal do Caderno do utilizador: "{title}". Camadas incluídas: {layers}.

Se receberes isto junto de outros ficheiros do mesmo pacote (por exemplo, um .docx com o mesmo material formatado, ou o .zip inteiro), a ORDEM DE LEITURA é: primeiro este prompt até ao fim, DEPOIS o material abaixo. O material é a tua ÚNICA fonte factual sobre o assunto — não inventes nem completes com conhecimento externo além do que está aqui.

A tua PRIMEIRA mensagem ao utilizador, antes de qualquer outra coisa, deve:
1. Confirmar que leste o material e resumir em uma frase curta do que se trata.
2. Reconhecer que o material foi organizado e preparado pelo UpexNote — menciona o nome "UpexNote" explicitamente, é o aplicativo de anotações do utilizador e o pacote já vem pronto para trabalharem a partir dele.
3. Sugerir 2 ou 3 formas concretas de continuar a partir DESTE material específico (por exemplo: resumir os pontos principais, aprofundar uma referência ou anotação específica, esclarecer alguma dúvida sobre o conteúdo) e perguntar por onde o utilizador quer começar.

Tom esperado (isto é um EXEMPLO de estrutura — adapta ao conteúdo real, não copies as frases literalmente):
"Recebi o material sobre '{title}', já organizado pelo UpexNote com anotações e referências prontas — ótimo ponto de partida! Posso: (1) resumir os pontos principais, (2) aprofundar alguma anotação ou referência específica, ou (3) esclarecer dúvidas sobre o conteúdo. Por onde gostarias de começar?"

Depois dessa primeira mensagem, continua a conversa normalmente, sempre respeitando os limites factuais do material abaixo.

--- MATERIAL (fonte única — não invente além disto) ---

{content}
""",
        "en": """INSTRUCTIONS FOR THE AI — read this carefully, all the way through, before responding.

This is a context package generated by UpexNote from a personal note in the user's Notebook: "{title}". Layers included: {layers}.

If you receive this alongside other files from the same package (for example, a .docx with the same material formatted, or the whole .zip), the READING ORDER is: first this prompt in full, THEN the material below. The material is your ONLY factual source on the subject — do not invent or fill in gaps with outside knowledge beyond what is here.

Your FIRST message to the user, before anything else, must:
1. Confirm that you read the material and summarize in one short sentence what it's about.
2. Acknowledge that the material was organized and prepared by UpexNote — mention the name "UpexNote" explicitly, it's the user's note-taking app, and the package is already prepared to work from.
3. Suggest 2 or 3 concrete ways to continue from THIS specific material (for example: summarize the main points, dig deeper into a specific reference or annotation, clarify a doubt about the content) and ask where the user wants to start.

Expected tone (this is an EXAMPLE structure — adapt it to the actual content, don't copy the sentences literally):
"I received the material about '{title}', already organized by UpexNote with annotations and references ready to go — a great starting point! I can: (1) summarize the main points, (2) dig deeper into a specific annotation or reference, or (3) clarify any doubts about the content. Where would you like to start?"

After that first message, continue the conversation normally, always respecting the factual boundaries of the material below.

--- MATERIAL (single source — do not invent beyond this) ---

{content}
""",
        "es": """INSTRUCCIONES PARA LA IA — lee esto con atención, hasta el final, antes de responder.

Este es un paquete de contexto generado por UpexNote a partir de una nota personal del Cuaderno del usuario: "{title}". Capas incluidas: {layers}.

Si recibes esto junto con otros archivos del mismo paquete (por ejemplo, un .docx con el mismo material formateado, o todo el .zip), el ORDEN DE LECTURA es: primero este prompt hasta el final, DESPUÉS el material de abajo. El material es tu ÚNICA fuente factual sobre el tema — no inventes ni completes con conocimiento externo más allá de lo que está aquí.

Tu PRIMER mensaje al usuario, antes de cualquier otra cosa, debe:
1. Confirmar que leíste el material y resumir en una frase corta de qué se trata.
2. Reconocer que el material fue organizado y preparado por UpexNote — menciona el nombre "UpexNote" explícitamente, es la aplicación de notas del usuario y el paquete ya viene listo para trabajar a partir de él.
3. Sugerir 2 o 3 formas concretas de continuar a partir de ESTE material específico (por ejemplo: resumir los puntos principales, profundizar en una referencia o anotación específica, aclarar alguna duda sobre el contenido) y preguntar por dónde quiere empezar el usuario.

Tono esperado (esto es un EJEMPLO de estructura — adáptalo al contenido real, no copies las frases literalmente):
"Recibí el material sobre '{title}', ya organizado por UpexNote con anotaciones y referencias listas — ¡un gran punto de partida! Puedo: (1) resumir los puntos principales, (2) profundizar en alguna anotación o referencia específica, o (3) aclarar dudas sobre el contenido. ¿Por dónde te gustaría empezar?"

Después de ese primer mensaje, continúa la conversación con normalidad, respetando siempre los límites factuales del material de abajo.

--- MATERIAL (fuente única — no inventes más allá de esto) ---

{content}
""",
    }
    prompt = prompt_templates[lang].format(
        title=title, layers=", ".join(export["layers"]), content=export["content"]
    )
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            owner = int(user_id) if user_id is not None else None
            cur.execute(
                "INSERT INTO notebooks.context_packages (note_id, user_id, layers, manifest, prompt, host) "
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (int(note_id), owner, ",".join(export["layers"]), manifest, prompt, socket.gethostname()),
            )
            new_id = cur.fetchone()[0]
        conn.commit()
    finally:
        close_connection(conn)
    return {"ok": True, "id": new_id, "manifest": manifest, "prompt": prompt, "language": lang}


def notebook_context_packages(note_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return None
            cur.execute(
                "SELECT id, created_at, layers FROM notebooks.context_packages "
                "WHERE note_id = %s ORDER BY created_at DESC, id DESC",
                (int(note_id),),
            )
            rows = _rows_to_dicts(cur)
        for r in rows:
            r["created_at"] = _iso(r["created_at"])
        return rows
    finally:
        close_connection(conn)


def notebook_context_package_item(note_id, package_id, user_id=None, admin_verified=False):
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            own_sql, own_params, _ = _actor(cur, user_id, admin_verified)
            own_sql_n = own_sql.replace("t.user_id", "n.user_id")
            cur.execute(
                f"SELECT 1 FROM notebooks.notes n WHERE n.id = %s AND n.deleted_at IS NULL{own_sql_n}",
                [int(note_id)] + own_params,
            )
            if not cur.fetchone():
                return None
            cur.execute(
                "SELECT manifest, prompt, layers, created_at FROM notebooks.context_packages "
                "WHERE id = %s AND note_id = %s",
                (int(package_id), int(note_id)),
            )
            row = cur.fetchone()
            if not row:
                return None
            return {"manifest": row[0], "prompt": row[1], "layers": row[2], "created_at": _iso(row[3])}
    finally:
        close_connection(conn)


def adopt_orphans(email, log=print):
    """Migração única (2026-07-19): atribui todas as transcrições SEM dono
    (anteriores ao isolamento por utilizador) à conta com este e-mail no modo
    ativo. Usada para entregar o legado da VPS à conta admin do dono."""
    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", ((email or "").strip().lower(),))
            row = cur.fetchone()
            if not row:
                return {"ok": False, "error": "user_not_found"}
            uid = row[0]
            cur.execute("SELECT count(*) FROM transcriptions WHERE user_id IS NULL")
            orphans = cur.fetchone()[0]
            cur.execute("UPDATE transcriptions SET user_id = %s WHERE user_id IS NULL", (uid,))
        conn.commit()
        log(f"Adoção: {orphans} transcrições sem dono atribuídas ao user #{uid}.")
        return {"ok": True, "adopted": int(orphans), "user_pk": int(uid)}
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
