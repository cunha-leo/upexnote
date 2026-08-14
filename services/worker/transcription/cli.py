"""
Ponto de entrada do worker de transcricao do UpexNote.

Desenhado para ser lancado como processo/sidecar por qualquer interface
(o shell Tauri, um script, testes). Comunica por NDJSON: cada linha do
stdout e um objeto JSON completo (um "evento"). Assim a interface consegue
mostrar progresso em tempo real, lendo o stdout linha a linha, sem precisar
de servidor HTTP, portas ou CORS.

--------------------------------------------------------------------------
SEGURANCA DAS CHAVES
--------------------------------------------------------------------------
As chaves API NUNCA sao passadas por argumentos de linha de comando (argv
e visivel na lista de processos do sistema). O comando `transcribe` le a
chave do Windows Credential Manager por conta propria. Para GRAVAR uma
chave, o comando `set-key` le o valor por stdin sem eco (getpass) — deve
ser corrido pelo proprio utilizador no seu terminal, nunca com a chave
embutida no comando.

--------------------------------------------------------------------------
COMANDOS
--------------------------------------------------------------------------
  engines
      Lista os motores disponiveis (JSON unico), incluindo se a respetiva
      chave ja esta configurada.

  transcribe --engine <id> --file "<caminho>" [--format-engine <id>] [--format-profile <perfil>]
      Transcreve o ficheiro com o motor escolhido. Emite eventos NDJSON:
        {"type": "start",    "engine": ..., "file": ...}
        {"type": "progress", "message": "..."}      (0..N vezes)
        {"type": "result",   "ok": bool, "clean_text": ..., "clean_path": ...,
                             "raw_path": ..., "cost": ..., "duration_s": ...,
                             "problems": [...]}
      ou, em caso de falha:
        {"type": "error", "message": "..."}
      Prints soltos internos do pipeline vao para stderr, para nao
      contaminarem o fluxo NDJSON do stdout.

      Com --format-engine (ADF-01, fluxo decidido 06/08/2026): roda a
      formatacao logo em seguida, na MESMA chamada (transcricao -> validacao
      raw<->clean -> formatacao), emitindo mais eventos depois do "result":
        {"type": "validation",   "ok": bool, "ratio": float|null, "problems": [...]}
        {"type": "format_result","ok": true, "document": {...}, "document_id": int, ...}
      ou, se a formatacao (nao a transcricao) falhar:
        {"type": "format_error", "message": "..."}
      format_error NUNCA significa que a transcricao falhou — ela ja foi
      gravada antes desta etapa. Sem --format-engine (ou com "none"), o
      comportamento e' identico a antes (= toggle "Formatar depois").

  document-generate --transcription-id <id> --engine <id> [--profile <perfil>]
      Formatacao RETROATIVA: mesma etapa acima, mas a partir de uma
      transcricao ja existente (fluxo da Biblioteca/edicao, nao do Transcribe).

  set-key --name <NOME_DA_CHAVE>
      Le o valor por stdin sem eco e guarda-o no Windows Credential
      Manager. Corre isto tu mesmo no teu terminal.

  check-key --name <NOME_DA_CHAVE>
      Diz se a chave esta configurada (JSON), sem nunca revelar o valor.

Exemplos:
    python -m transcription.cli engines
    python -m transcription.cli transcribe --engine assemblyai --file "C:/gravacoes/reuniao.mp4"
    python -m transcription.cli transcribe --engine assemblyai --file "C:/gravacoes/reuniao.mp4" --format-engine claude_haiku
    python -m transcription.cli document-generate --transcription-id 21 --engine gemini
    python -m transcription.cli set-key --name ASSEMBLYAI_API_KEY
"""
import argparse
import json
import sys
import time
import uuid
import secrets
from pathlib import Path

from . import paths
from .protocol import emit as _emit
from .registry import ENGINES, FORMAT_ENGINES
from .credentials import get_key, set_key, clear_key, KNOWN_KEYS, key_purposes


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    return value


# Normaliza o idioma para código curto e consistente (para os dashboards):
# whisper-1 devolve "portuguese", AssemblyAI devolve "pt" — uniformizamos.
_LANG_MAP = {
    "portuguese": "pt", "english": "en", "spanish": "es", "french": "fr",
    "german": "de", "italian": "it", "dutch": "nl", "galician": "gl",
}


def _normalize_lang(lang):
    if not lang:
        return None
    low = str(lang).strip().lower()
    return _LANG_MAP.get(low, low)


def cmd_engines(args):
    out = []
    for engine_id, cfg in ENGINES.items():
        out.append({
            "id": engine_id,
            "label": cfg["label"],
            "info": cfg["info"],
            "primary": cfg.get("primary", False),
            "key_name": cfg["key_name"],
            "key_set": bool(get_key(cfg["key_name"])),
        })
    _emit(sys.stdout, {"type": "engines", "engines": out})
    return 0


def cmd_format_engines(args):
    # Motores de FORMATACAO (clean -> documento estruturado, ADF-01) —
    # separado de `engines` (transcricao). Sem motor padrao: os seis ficam
    # disponiveis e a UI mostra modelo + custo/hora lado a lado.
    out = []
    for engine_id, cfg in FORMAT_ENGINES.items():
        out.append({
            "id": engine_id,
            "label": cfg["label"],
            "info": cfg["info"],
            "key_name": cfg["key_name"],
            "key_set": bool(get_key(cfg["key_name"])),
            "cost_hora_brl": cfg.get("cost_hora_brl"),
        })
    _emit(sys.stdout, {"type": "format_engines", "engines": out})
    return 0


def cmd_format(args):
    from .formatting import PROFILES

    real_stdout = sys.stdout
    engine = FORMAT_ENGINES.get(args.engine)
    if engine is None:
        _emit(real_stdout, {
            "type": "error",
            "message": f"Motor de formatacao desconhecido: {args.engine!r}. Opcoes: {', '.join(FORMAT_ENGINES)}",
        })
        return 1

    profile = getattr(args, "profile", None) or "detalhado"
    if profile not in PROFILES:
        _emit(real_stdout, {"type": "error", "message": f"Perfil desconhecido: {profile!r}. Opcoes: {', '.join(PROFILES)}"})
        return 1

    data = _stdin_json()
    clean_text = (data or {}).get("text", "").strip()
    if not clean_text:
        _emit(real_stdout, {"type": "error", "message": "Nenhum texto recebido por stdin (esperado JSON {\"text\": \"...\"})."})
        return 1

    api_key = get_key(engine["key_name"])
    if not api_key:
        _emit(real_stdout, {
            "type": "error",
            "message": f"Chave {engine['key_name']} nao configurada. Corre: "
                       f"python -m transcription.cli set-key --name {engine['key_name']}",
        })
        return 1

    _emit(real_stdout, {"type": "start", "engine": args.engine, "profile": profile})

    def progress(m):
        _emit(real_stdout, {"type": "progress", "message": str(m)})

    sys.stdout = sys.stderr
    try:
        result = engine["run"](clean_text, api_key, profile=profile, log=progress)
    except Exception as e:  # noqa: BLE001
        sys.stdout = real_stdout
        _emit(real_stdout, {"type": "error", "message": str(e)})
        return 1
    finally:
        sys.stdout = real_stdout

    if not result.get("ok"):
        _emit(real_stdout, {"type": "error", "message": "; ".join(result.get("problems") or ["Falha desconhecida na formatacao."])})
        return 1

    _emit(real_stdout, {
        "type": "format_result",
        "ok": True,
        "engine": args.engine,
        "profile": profile,
        "document": result["document"],
        "processing_s": result.get("processing_s"),
        "usage": result.get("usage", {}),
    })
    return 0


def cmd_document_generate(args):
    """Formatacao retroativa (ADF-01): parte de uma transcricao JA existente
    (Library/edicao — nao a tela de Transcribe), roda o gate raw<->clean, chama
    o motor de formatacao escolhido e persiste o documento estruturado.

    Eventos NDJSON: start -> progress* -> validation (sempre) -> format_result
    (se ok) ou error (se o gate ou a formatacao falharem).
    """
    from . import db
    from .formatting import PROFILES
    from .doc_validation import validate_raw_clean

    real_stdout = sys.stdout
    engine = FORMAT_ENGINES.get(args.engine)
    if engine is None:
        _emit(real_stdout, {
            "type": "error",
            "message": f"Motor de formatacao desconhecido: {args.engine!r}. Opcoes: {', '.join(FORMAT_ENGINES)}",
        })
        return 1

    profile = getattr(args, "profile", None) or "detalhado"
    if profile not in PROFILES:
        _emit(real_stdout, {"type": "error", "message": f"Perfil desconhecido: {profile!r}. Opcoes: {', '.join(PROFILES)}"})
        return 1

    err = _require_db()
    if err:
        _emit(real_stdout, {"type": "error", "message": err})
        return 1

    uid = getattr(args, "user", None)
    source = db.get_transcript_raw_clean(args.transcription_id, user_id=uid)
    if source is None:
        _emit(real_stdout, {"type": "error", "message": f"Transcrição #{args.transcription_id} não encontrada."})
        return 1

    _emit(real_stdout, {"type": "start", "engine": args.engine, "profile": profile,
                        "transcription_id": args.transcription_id})

    validation = validate_raw_clean(source.get("raw_text") or "", source.get("clean_text") or "")
    _emit(real_stdout, {"type": "validation", "ok": validation["ok"], "ratio": validation["ratio"],
                        "problems": validation["problems"]})
    if not validation["ok"]:
        _emit(real_stdout, {"type": "error", "message": "Validação raw↔clean falhou — "
                            + " ".join(validation["problems"])})
        return 1

    api_key = get_key(engine["key_name"])
    if not api_key:
        _emit(real_stdout, {
            "type": "error",
            "message": f"Chave {engine['key_name']} nao configurada. Corre: "
                       f"python -m transcription.cli set-key --name {engine['key_name']}",
        })
        return 1

    def progress(m):
        _emit(real_stdout, {"type": "progress", "message": str(m)})

    sys.stdout = sys.stderr
    try:
        result = engine["run"](source["clean_text"], api_key, profile=profile, log=progress)
    except Exception as e:  # noqa: BLE001
        sys.stdout = real_stdout
        _emit(real_stdout, {"type": "error", "message": str(e)})
        return 1
    finally:
        sys.stdout = real_stdout

    if not result.get("ok"):
        _emit(real_stdout, {"type": "error", "message": "; ".join(result.get("problems") or ["Falha desconhecida na formatacao."])})
        return 1

    document = result["document"]
    usage = result.get("usage", {})
    doc_id = db.insert_document({
        "transcription_id": args.transcription_id,
        "user_id": uid,
        "engine": args.engine,
        "profile": profile,
        "title": document.get("title"),
        "objective": document.get("objective"),
        "raw_clean_check_ok": validation["ok"],
        "blocks": document.get("blocks") or [],
        "jargon": document.get("jargon") or [],
        "processing_s": result.get("processing_s"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
    }, log=progress)

    _emit(real_stdout, {
        "type": "format_result",
        "ok": True,
        "engine": args.engine,
        "profile": profile,
        "document": document,
        "document_id": doc_id,
        "saved": doc_id is not None,
        "processing_s": result.get("processing_s"),
        "usage": usage,
    })
    return 0


# Registro — 2026-08-11 ("documento gerado mas não gravado"): `insert_document`
# é best-effort ("nunca levanta") e `format_result` já respondia `saved` sem a
# UI ler esse campo — uma falha de gravação (transitória: túnel a cair, VPS a
# reiniciar) fazia o utilizador achar que perdeu a formatação já paga à API,
# sem forma de recuperar sem gastar de novo. Este comando recebe o `document`
# JÁ GERADO (guardado em memória no cliente) e só faz o INSERT — nunca chama
# o motor de IA outra vez.
def cmd_document_save(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    payload = _stdin_json()
    if not isinstance(payload, dict) or not isinstance(payload.get("document"), dict):
        _emit(sys.stdout, {"type": "error", "message": "Payload inválido para guardar o documento."})
        return 1
    document = payload["document"]
    usage = payload.get("usage") or {}
    try:
        doc_id = db.insert_document({
            "transcription_id": args.transcription_id,
            "user_id": getattr(args, "user", None),
            "engine": args.engine,
            "profile": args.profile,
            "title": document.get("title"),
            "objective": document.get("objective"),
            "raw_clean_check_ok": payload.get("raw_clean_check_ok"),
            "blocks": document.get("blocks") or [],
            "jargon": document.get("jargon") or [],
            "processing_s": payload.get("processing_s"),
            "input_tokens": usage.get("input_tokens"),
            "output_tokens": usage.get("output_tokens"),
        })
        if doc_id is None:
            _emit(sys.stdout, {"type": "error", "message": "Ainda não foi possível guardar o documento — verifique a ligação e tente novamente."})
            return 1
        _emit(sys.stdout, {"type": "ok", "document_id": doc_id})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao guardar o documento: {e}"})
        return 1


def cmd_transcribe(args):
    real_stdout = sys.stdout

    engine = ENGINES.get(args.engine)
    if engine is None:
        _emit(real_stdout, {
            "type": "error",
            "message": f"Motor desconhecido: {args.engine!r}. Opcoes: {', '.join(ENGINES)}",
        })
        return 1

    file_path = args.file
    if not Path(file_path).exists():
        _emit(real_stdout, {"type": "error", "message": f"Ficheiro nao encontrado: {file_path}"})
        return 1

    # Destino pontual ("guardar em..." so desta vez): os ficheiros vao
    # DIRETOS para a pasta indicada, ignorando pasta padrao e organizacao.
    if getattr(args, "dest", None):
        dest = Path(args.dest)
        try:
            dest.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            _emit(real_stdout, {"type": "error", "message": f"Pasta de destino invalida: {args.dest} ({e})"})
            return 1
        paths.set_dest_override(dest)

    api_key = get_key(engine["key_name"])
    if not api_key:
        _emit(real_stdout, {
            "type": "error",
            "message": f"Chave {engine['key_name']} nao configurada. Corre: "
                       f"python -m transcription.cli set-key --name {engine['key_name']}",
        })
        return 1

    _emit(real_stdout, {"type": "start", "engine": args.engine, "file": file_path})

    def progress(m):
        _emit(real_stdout, {"type": "progress", "message": str(m)})

    # Prints soltos dentro do pipeline (ex.: audio_chunks) vao para stderr,
    # para o stdout ficar so com NDJSON limpo. Os nossos eventos de progresso
    # sao emitidos pela referencia guardada ao stdout real.
    sys.stdout = sys.stderr
    started = time.time()
    try:
        result = engine["run"](file_path, api_key, log=progress)
    except Exception as e:  # noqa: BLE001 - queremos reportar qualquer falha como evento
        sys.stdout = real_stdout
        _emit(real_stdout, {"type": "error", "message": str(e)})
        return 1
    finally:
        sys.stdout = real_stdout
    processing_s = round(time.time() - started, 1)
    language = _normalize_lang(result.get("language"))

    _emit(real_stdout, {
        "type": "result",
        "ok": result["ok"],
        "clean_text": result["clean_text"],
        "clean_path": _jsonable(result["clean_path"]),
        "raw_path": _jsonable(result["raw_path"]),
        "cost": result["cost"],
        "duration_s": result["duration_s"],
        "problems": result.get("problems", []),
        "language": language,
    })

    # Escrita best-effort no Postgres da VPS (cópia fora da máquina + histórico).
    # O ficheiro local já está gravado; se isto falhar, não afeta o resultado.
    new_transcription_id = None
    raw_text = None
    try:
        from . import db
        rp = result.get("raw_path")
        if rp and Path(rp).exists():
            raw_text = Path(rp).read_text(encoding="utf-8")
        new_transcription_id = db.insert_transcription({
            "engine": args.engine,
            "user_id": getattr(args, "user", None),
            "source_filename": Path(file_path).name,
            "source_path": file_path,
            "language": language,
            "duration_s": result.get("duration_s"),
            "cost_usd": result.get("cost"),
            "processing_s": processing_s,
            "validation_ok": result.get("ok"),
            "problems": result.get("problems"),
            "clean_text": result.get("clean_text"),
            "raw_text": raw_text,
            "clean_path": _jsonable(result.get("clean_path")),
        }, log=progress)
    except Exception as e:  # noqa: BLE001 - best-effort, nunca bloquear
        progress(f"DB: passo ignorado ({e})")

    # Evento aditivo para a UI pós-transcrição: o `result` continua a chegar
    # assim que o ficheiro local está pronto, e este segundo evento informa se
    # já existe um ID persistido que possa ser aberto diretamente na Library.
    # Falha best-effort na base não invalida o transcript local.
    _emit(real_stdout, {
        "type": "transcription_saved",
        "saved": new_transcription_id is not None,
        "transcription_id": new_transcription_id,
    })

    # Formatacao encadeada (ADF-01, decisao 06/08/2026): "a escolha do motor
    # de formatacao acontece no mesmo momento em que o usuario escolhe o
    # motor de transcricao... ao executar, o sistema ja roda as duas etapas
    # em sequencia". Sem --format-engine (ou "none"/"nenhum"), comportamento
    # idêntico a antes — equivale ao toggle "Formatar depois"/motor "Nenhum".
    # Falha aqui NUNCA reabre a transcricao como erro: ela ja foi gravada.
    format_engine_id = getattr(args, "format_engine", None)
    if result["ok"] and format_engine_id and format_engine_id not in ("none", "nenhum"):
        _run_chained_formatting(real_stdout, format_engine_id,
                                getattr(args, "format_profile", None) or "detalhado",
                                new_transcription_id, getattr(args, "user", None),
                                raw_text or "", result.get("clean_text") or "")

    return 0 if result["ok"] else 2


def _run_chained_formatting(real_stdout, format_engine_id, profile, transcription_id, user_id, raw_text, clean_text):
    """Etapa 2 do fluxo de Transcribe: valida raw<->clean e formata, reaproveitando
    o texto que acabou de ser gerado (sem reconsultar a base). Emite os mesmos
    tipos de evento do document-generate, mais "format_error" (falha aqui NAO
    e' "error" — a transcricao em si ja terminou bem)."""
    from .formatting import PROFILES
    from .doc_validation import validate_raw_clean

    def progress(m):
        _emit(real_stdout, {"type": "progress", "message": str(m)})

    engine = FORMAT_ENGINES.get(format_engine_id)
    if engine is None:
        _emit(real_stdout, {"type": "format_error", "message": f"Motor de formatacao desconhecido: {format_engine_id!r}."})
        return
    if profile not in PROFILES:
        profile = "detalhado"
    if transcription_id is None:
        _emit(real_stdout, {"type": "format_error", "message": "Transcrição não foi gravada na base — formatação encadeada precisa do ID; use document-generate depois."})
        return

    validation = validate_raw_clean(raw_text, clean_text)
    _emit(real_stdout, {"type": "validation", "ok": validation["ok"], "ratio": validation["ratio"],
                        "problems": validation["problems"]})
    if not validation["ok"]:
        _emit(real_stdout, {"type": "format_error", "message": "Validação raw↔clean falhou — "
                            + " ".join(validation["problems"])})
        return

    api_key = get_key(engine["key_name"])
    if not api_key:
        _emit(real_stdout, {"type": "format_error",
                            "message": f"Chave {engine['key_name']} nao configurada. Corre: "
                                       f"python -m transcription.cli set-key --name {engine['key_name']}"})
        return

    real_out = sys.stdout
    sys.stdout = sys.stderr
    try:
        result = engine["run"](clean_text, api_key, profile=profile, log=progress)
    except Exception as e:  # noqa: BLE001
        sys.stdout = real_out
        _emit(real_stdout, {"type": "format_error", "message": str(e)})
        return
    finally:
        sys.stdout = real_out

    if not result.get("ok"):
        _emit(real_stdout, {"type": "format_error", "message": "; ".join(result.get("problems") or ["Falha desconhecida na formatacao."])})
        return

    from . import db
    document = result["document"]
    usage = result.get("usage", {})
    doc_id = db.insert_document({
        "transcription_id": transcription_id,
        "user_id": user_id,
        "engine": format_engine_id,
        "profile": profile,
        "title": document.get("title"),
        "objective": document.get("objective"),
        "raw_clean_check_ok": validation["ok"],
        "blocks": document.get("blocks") or [],
        "jargon": document.get("jargon") or [],
        "processing_s": result.get("processing_s"),
        "input_tokens": usage.get("input_tokens"),
        "output_tokens": usage.get("output_tokens"),
    }, log=progress)

    _emit(real_stdout, {
        "type": "format_result",
        "ok": True,
        "engine": format_engine_id,
        "profile": profile,
        "document": document,
        "document_id": doc_id,
        "saved": doc_id is not None,
        "processing_s": result.get("processing_s"),
        "usage": usage,
    })


def cmd_tunnel_keep(args):
    from . import db
    return db.run_tunnel_keeper()


def _stdin_json():
    try:
        return json.loads(sys.stdin.read())
    except Exception:
        return None


def cmd_account(args):
    # Identidade (item 13-C). Dados SEMPRE por stdin (nunca argv — visível na
    # lista de processos). Um comando por operação; resposta JSON única.
    # --mode: as contas de ADMINISTRADOR vivem na base central (vps) mesmo que
    # a sessão atual seja local — o override vale só para este processo.
    from . import accounts, db
    op = args.command
    if getattr(args, "mode", None):
        db.set_mode_override(args.mode)
    try:
        if op == "account-suggest":
            _emit(sys.stdout, {"type": "account", **accounts.suggest_user_id(args.user_id)})
            return 0
        data = _stdin_json()
        if data is None:
            _emit(sys.stdout, {"type": "error", "message": "JSON invalido no stdin."})
            return 1
        if op == "account-register":
            res = accounts.register(data)
        elif op == "account-login":
            res = accounts.login(data.get("email"), data.get("password"))
        elif op == "account-oauth-login":
            res = accounts.oauth_login(data)
        elif op == "account-update":
            res = accounts.update_profile(data)
        elif op == "account-profile":
            res = accounts.profile(data)
        elif op == "account-elevate":
            res = accounts.elevate(data.get("email"), data.get("admin_secret"))
        else:
            res = {"ok": False, "error": "unsupported_operation"}
        # Fluxo de administrador NUM SÓ processo (2026-07-19: dois spawns
        # sequenciais duplicavam o custo do ensure/túnel): se o payload traz
        # admin_secret, a identidade validada é elevada aqui mesmo.
        if (op in ("account-login", "account-oauth-login", "account-register")
                and res.get("ok") and res.get("user") and data.get("admin_secret")):
            res = accounts.elevate(res["user"]["email"], data.get("admin_secret"))
        _emit(sys.stdout, {"type": "account", **res})
        return 0 if res.get("ok") else 1
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha de conta: {e}"})
        return 1


def cmd_api_reset(args):
    """Password reset through the central HTTPS API; payload is stdin-only."""
    from .api_client import ApiConfigurationError, UpexNoteApiClient

    data = _stdin_json()
    if data is None:
        _emit(sys.stdout, {"type": "api-reset", "ok": False, "error": "invalid_payload"})
        return 1
    try:
        client = UpexNoteApiClient()
        if args.command == "api-reset-request":
            result = client.request_reset(data.get("email", ""))
        elif args.command == "api-reset-verify":
            result = client.verify_reset(data.get("email", ""), data.get("code", ""))
        else:
            result = client.complete_reset(
                data.get("email", ""),
                data.get("reset_token", ""),
                data.get("new_password", ""),
            )
        _emit(sys.stdout, {"type": "api-reset", **result})
        return 0 if result.get("ok") else 1
    except ApiConfigurationError as exc:
        _emit(sys.stdout, {"type": "api-reset", "ok": False, "error": str(exc)})
        return 1
    except Exception:  # never serialize exception details from a sensitive flow
        _emit(sys.stdout, {"type": "api-reset", "ok": False, "error": "service_unavailable"})
        return 1


def cmd_support(args):
    """Support API bridge. The opaque per-installation secret stays in the OS vault."""
    from .api_client import ApiConfigurationError, UpexNoteApiClient
    from .credentials import get_key, set_key
    data = _stdin_json()
    if data is None:
        _emit(sys.stdout, {"type": "support", "ok": False, "error": "invalid_payload"}); return 1
    operation = args.command.removeprefix("support-")
    secret = get_key("UPEXNOTE_SUPPORT_CLIENT_SECRET")
    if not secret:
        secret = secrets.token_urlsafe(32)
        set_key("UPEXNOTE_SUPPORT_CLIENT_SECRET", secret)
    if operation.startswith("admin-"):
        payload = data
    else:
        payload = {**data, "client_secret": secret}
    try:
        client = UpexNoteApiClient()
        result = client.support_attachment(payload, data.get("file_path", "")) if operation == "attachment" else client.support(operation, payload)
        _emit(sys.stdout, {"type": "support", **result})
        return 0 if result.get("ok") else 1
    except ApiConfigurationError as exc:
        _emit(sys.stdout, {"type": "support", "ok": False, "error": str(exc)}); return 1
    except Exception:
        _emit(sys.stdout, {"type": "support", "ok": False, "error": "service_unavailable"}); return 1


def cmd_telemetry(args):
    """Send one strictly allow-listed, consented technical event.

    There is no generic JSON payload: a path, transcript, exception text or
    credential cannot accidentally reach the central API.
    """
    from .api_client import ApiConfigurationError, UpexNoteApiClient

    settings = paths.load_settings()
    installation_id = settings.get("telemetry_installation_id")
    if not settings.get("telemetry_consent") or not installation_id:
        _emit(sys.stdout, {"type": "telemetry", "ok": True, "skipped": "no_consent"})
        return 0
    event = {
        "installation_id": installation_id,
        "consent": True,
        "event": args.event,
        "app_version": args.app_version,
    }
    for name in ("engine", "duration_seconds", "estimated_cost_micros", "error_code"):
        value = getattr(args, name, None)
        if value is not None:
            event[name] = value
    try:
        client = UpexNoteApiClient()
        # Token is held only in this worker process; a fresh capability token
        # is exchanged per event instead of persisting a bearer credential.
        token = client.exchange_installation_token(installation_id, args.app_version)["access_token"]
        client.send_telemetry(event, token)
        _emit(sys.stdout, {"type": "telemetry", "ok": True})
        return 0
    except (ApiConfigurationError, KeyError):
        _emit(sys.stdout, {"type": "telemetry", "ok": False, "error": "service_unavailable"})
        return 1


def cmd_telemetry_overview(args):
    from .api_client import UpexNoteApiClient
    data = _stdin_json() or {}
    try:
        result = UpexNoteApiClient().telemetry_overview(data.get("email", ""), data.get("elevation_token", ""), int(data.get("days", 7)))
        _emit(sys.stdout, {"type": "telemetry-overview", **result})
        return 0 if result.get("error") is None else 1
    except Exception:
        _emit(sys.stdout, {"type": "telemetry-overview", "ok": False, "error": "service_unavailable"})
        return 1
    except Exception:
        _emit(sys.stdout, {"type": "telemetry", "ok": False, "error": "service_unavailable"})
        return 1


def cmd_api_admin_factor(args):
    """Administrative MFA via HTTPS; every sensitive value is stdin-only."""
    from .api_client import ApiConfigurationError, UpexNoteApiClient

    data = _stdin_json()
    if data is None:
        _emit(sys.stdout, {"type": "api-admin", "ok": False, "error": "invalid_payload"})
        return 1
    try:
        client = UpexNoteApiClient()
        op = args.command
        if op == "api-admin-challenge":
            result = client.request_admin_challenge(
                data.get("email", ""),
                data.get("admin_secret", ""),
                bool(data.get("prefer_email")),
            )
        elif op == "api-admin-verify":
            result = client.verify_admin_factor(data.get("email", ""), data.get("code", ""))
        elif op == "api-admin-validate":
            result = client.validate_admin_session(
                data.get("email", ""), data.get("elevation_token", "")
            )
        elif op == "api-admin-revoke":
            result = client.revoke_admin_session(
                data.get("email", ""), data.get("elevation_token", "")
            )
        elif op == "api-admin-totp-enroll":
            result = client.begin_totp_enrollment(
                data.get("email", ""), data.get("elevation_token", "")
            )
        else:
            result = client.confirm_totp_enrollment(
                data.get("email", ""),
                data.get("elevation_token", ""),
                data.get("code", ""),
            )
        _emit(sys.stdout, {"type": "api-admin", **result})
        return 0 if result.get("ok") else 1
    except ApiConfigurationError as exc:
        _emit(sys.stdout, {"type": "api-admin", "ok": False, "error": str(exc)})
        return 1
    except Exception:
        _emit(sys.stdout, {"type": "api-admin", "ok": False, "error": "service_unavailable"})
        return 1


def _valid_admin_session(data: dict, actor=None) -> bool:
    """Online proof checked by the central API; no server secret is packaged."""
    from .api_client import UpexNoteApiClient

    email = (data.get("admin_email") or "").strip().lower()
    token = data.get("admin_token") or ""
    if not email or not token:
        return False
    result = UpexNoteApiClient().validate_admin_session(email, token)
    if not result.get("ok") or not result.get("valid"):
        return False
    return actor is None or int(result.get("user_id") or -1) == int(actor)


def cmd_oauth(args):
    from . import oauth
    return oauth.run_oauth(args.provider)


def cmd_admin(args):
    # Aba de Administração (2026-07-19). Payload por stdin; o ator (users.id da
    # sessão) vai no payload e é REVALIDADO na base (role=admin) pelo worker.
    from . import accounts, data_studio, db
    if getattr(args, "mode", None):
        db.set_mode_override(args.mode)
    data = _stdin_json()
    if data is None:
        _emit(sys.stdout, {"type": "error", "message": "JSON invalido no stdin."})
        return 1
    actor = data.get("actor")
    op = args.command
    try:
        if not _valid_admin_session(data, actor):
            _emit(sys.stdout, {"type": "admin", "ok": False, "error": "mfa_required"})
            return 1
        if op == "admin-overview":
            res = accounts.admin_overview(actor)
        elif op == "admin-users":
            res = accounts.admin_list_users(actor, search=data.get("search"),
                                            include_deleted=bool(data.get("include_deleted")))
        elif op == "admin-create-user":
            res = accounts.admin_list_users(actor)  # guard barato antes do register
            if res.get("ok"):
                res = accounts.register(data.get("user") or {})
        elif op == "admin-update-user":
            res = accounts.admin_update_user(actor, data.get("id"), data.get("fields"))
        elif op == "admin-delete-user":
            res = accounts.admin_delete_user(actor, data.get("id"), purge=bool(data.get("purge")))
        elif op == "admin-events":
            res = db.list_access_events(actor, since=data.get("since"), event=data.get("event"),
                                        search=data.get("search"))
        elif op == "admin-data-catalog":
            res = data_studio.catalog(actor)
        elif op == "admin-data-table":
            res = data_studio.table_data(actor, data)
        elif op == "admin-data-query":
            res = data_studio.visual_query(actor, data)
        elif op == "admin-data-sql":
            res = data_studio.sql_editor(actor, data)
        elif op == "admin-data-saved-queries":
            res = data_studio.saved_queries(actor, data)
        else:  # admin-audit
            res = db.list_audit(actor, table=data.get("table"), record_id=data.get("record_id"),
                                since=data.get("since"))
        _emit(sys.stdout, {"type": "admin", **res})
        return 0 if res.get("ok") else 1
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha de administracao: {e}"})
        return 1


def cmd_db_check(args):
    # --mode permite testar um modo ESPECÍFICO sem o gravar (o ecrã de perfis
    # usa --mode vps para validar a config de administrador antes de trocar).
    from . import db
    mode = getattr(args, "mode", None) or db.storage_mode()
    if mode == "vps":
        if not db.load_config():
            _emit(sys.stdout, {"type": "error", "message": "db_config.json não encontrado — copia db_config.example.json para db_config.json."})
            return 1
        if not getattr(args, "stdin_password", False) and not get_key(db.PG_PASSWORD_KEY):
            _emit(sys.stdout, {"type": "error", "message": f"Password não configurada. Corre: set-key --name {db.PG_PASSWORD_KEY}"})
            return 1
    try:
        # Gate do administrador: credencial DIGITADA chega por stdin e é
        # validada por ligação REAL (prova de conhecimento, nunca a guardada).
        pw_override = sys.stdin.read().strip() if getattr(args, "stdin_password", False) else None
        if getattr(args, "mode", None):
            # força o modo pedido só durante este teste
            original = db.storage_mode
            db.storage_mode = lambda: args.mode
            try:
                res = db.check(password_override=pw_override)
            finally:
                db.storage_mode = original
        else:
            res = db.check(password_override=pw_override)
        _emit(sys.stdout, {"type": "db", "ok": True, "rows": res["rows"], "mode": mode,
                           "message": f"Ligação OK ({mode}). Linhas atuais: {res['rows']}."})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha na ligação/tabela: {e}"})
        return 1


def cmd_set_key(args):
    if args.name not in KNOWN_KEYS:
        _emit(sys.stdout, {
            "type": "error",
            "message": f"Nome de chave desconhecido: {args.name!r}. Opcoes: {', '.join(KNOWN_KEYS)}",
        })
        return 1
    if getattr(args, "stdin", False):
        # Valor recebido por stdin (usado pela interface via Rust — a chave
        # nunca passa por argumentos/linha de comando).
        value = sys.stdin.readline()
    else:
        import getpass
        try:
            value = getpass.getpass(f"Cola a {args.name} (nao aparece no ecra) e Enter: ")
        except (EOFError, KeyboardInterrupt):
            _emit(sys.stdout, {"type": "error", "message": "Cancelado."})
            return 1
    value = (value or "").strip()
    if not value:
        _emit(sys.stdout, {"type": "error", "message": "Nenhum valor introduzido; nada foi guardado."})
        return 1
    set_key(args.name, value)
    _emit(sys.stdout, {"type": "ok", "message": f"{args.name} guardada no Windows Credential Manager."})
    return 0


def cmd_clear_key(args):
    if args.name not in KNOWN_KEYS:
        _emit(sys.stdout, {
            "type": "error",
            "message": f"Nome de chave desconhecido: {args.name!r}. Opcoes: {', '.join(KNOWN_KEYS)}",
        })
        return 1
    clear_key(args.name)
    _emit(sys.stdout, {"type": "ok", "message": f"{args.name} removida."})
    return 0


def cmd_check_key(args):
    if args.name not in KNOWN_KEYS:
        _emit(sys.stdout, {
            "type": "error",
            "message": f"Nome de chave desconhecido: {args.name!r}. Opcoes: {', '.join(KNOWN_KEYS)}",
        })
        return 1
    _emit(sys.stdout, {"type": "key", "name": args.name, "key_set": bool(get_key(args.name))})
    return 0


def _require_db():
    """Valida config+password da DB; devolve mensagem de erro ou None.
    Em modo local (SQLite) não há nada a validar — a base cria-se sozinha."""
    from . import db
    if db.storage_mode() == "local":
        return None
    if not db.load_config():
        return "db_config.json não encontrado — copia db_config.example.json para db_config.json."
    if not get_key(db.PG_PASSWORD_KEY):
        return f"Password do Postgres não configurada. Corre: set-key --name {db.PG_PASSWORD_KEY}"
    return None


def _library_payload(args):
    """Reads MFA proof through stdin for app calls; direct CLI stays compatible."""
    from . import db

    if not getattr(args, "json_stdin", False):
        return {}, False
    data = _stdin_json()
    if data is None:
        raise ValueError("invalid_payload")
    uid = getattr(args, "user", None)
    if db.storage_mode() == "vps" and uid is not None:
        if not _valid_admin_session(data, uid):
            raise PermissionError("mfa_required")
        return data, True
    return data, False


def cmd_library(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        uid = getattr(args, "user", None)
        _, admin_verified = _library_payload(args)
        summary = db.library_summary(user_id=uid, admin_verified=admin_verified)
        items = db.library_list(limit=getattr(args, "limit", 200) or 200,
                                search=getattr(args, "search", None), user_id=uid,
                                admin_verified=admin_verified)
        _emit(sys.stdout, {"type": "library", "summary": summary, "items": items})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a consultar a Biblioteca: {e}"})
        return 1


def cmd_library_item(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        _, admin_verified = _library_payload(args)
        item = db.library_item(args.id, user_id=getattr(args, "user", None),
                               admin_verified=admin_verified)
        if item is None:
            _emit(sys.stdout, {"type": "error", "message": f"Transcrição #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "library_item", "item": item})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter a transcrição: {e}"})
        return 1


def cmd_library_update(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        if getattr(args, "json_stdin", False):
            data, admin_verified = _library_payload(args)
            new_text = data.get("text", "")
        else:
            data, admin_verified = {}, False
            new_text = sys.stdin.read()
        res = db.update_transcription(args.id, new_text, user_id=getattr(args, "user", None),
                                      admin_verified=admin_verified)
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Transcrição #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "message": "Transcrição atualizada.",
                           "file_updated": res.get("file_updated", False)})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao atualizar: {e}"})
        return 1


def cmd_db_migrate(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    res = db.migrate_v1_to_v2(log=lambda m: _emit(sys.stderr, {"type": "progress", "message": m}))
    if res.get("ok"):
        _emit(sys.stdout, {"type": "ok", **res})
        return 0
    _emit(sys.stdout, {"type": "error", "message": f"Migração falhou: {res}"})
    return 1


def cmd_db_migrate_documents_schema(args):
    from . import db
    if getattr(args, "mode", None):
        db.set_mode_override(args.mode)
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    res = db.migrate_documents_schema(log=lambda m: _emit(sys.stderr, {"type": "progress", "message": m}))
    if res.get("ok"):
        _emit(sys.stdout, {"type": "ok", **res})
        return 0
    _emit(sys.stdout, {"type": "error", "message": f"Migração de schema falhou: {res}"})
    return 1


def cmd_db_adopt_orphans(args):
    from . import db
    if getattr(args, "mode", None):
        db.set_mode_override(args.mode)
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.adopt_orphans(args.email, log=lambda m: _emit(sys.stderr, {"type": "progress", "message": m}))
        if res.get("ok"):
            _emit(sys.stdout, {"type": "ok", **res})
            return 0
        _emit(sys.stdout, {"type": "error", "message": f"Adoção falhou: {res.get('error')}"})
        return 1
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha na adoção: {e}"})
        return 1


def cmd_library_ack(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        _, admin_verified = _library_payload(args)
        res = db.acknowledge_warnings(args.id, ack=not args.reopen,
                                      user_id=getattr(args, "user", None),
                                      admin_verified=admin_verified)
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Transcrição #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "message": "Reaberto." if args.reopen else "Avisos marcados como revistos."})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha: {e}"})
        return 1


def cmd_library_delete(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        _, admin_verified = _library_payload(args)
        res = db.delete_transcription(args.id, user_id=getattr(args, "user", None),
                                      admin_verified=admin_verified)
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Transcrição #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "message": "Transcrição apagada (arquivada no histórico)."})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao apagar: {e}"})
        return 1


def cmd_document_item(args):
    """Um documento estruturado completo (hub + blocos + glossario + metricas).
    Espelha library-item, para a Biblioteca/editor abrirem um documento ja
    gerado sem o reformatar."""
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        _, admin_verified = _library_payload(args)
        item = db.document_item(args.id, user_id=getattr(args, "user", None),
                                admin_verified=admin_verified)
        if item is None:
            _emit(sys.stdout, {"type": "error", "message": f"Documento #{args.id} não encontrado."})
            return 1
        _emit(sys.stdout, {"type": "document_item", "item": item})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter o documento: {e}"})
        return 1


def cmd_document_delete(args):
    """Soft-delete de um documento (snapshot em documents_history). Espelha
    library-delete — o transcript de origem fica intacto."""
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        _, admin_verified = _library_payload(args)
        res = db.delete_document(args.id, user_id=getattr(args, "user", None),
                                 admin_verified=admin_verified)
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Documento #{args.id} não encontrado."})
            return 1
        _emit(sys.stdout, {"type": "ok", "message": "Documento apagado (arquivado no histórico)."})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao apagar o documento: {e}"})
        return 1


def cmd_notebook_ensure_default(args):
    """Coleção padrão do utilizador (cria na primeira vez, idempotente)."""
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        cid = db.notebook_ensure_default_collection(getattr(args, "user", None))
        _emit(sys.stdout, {"type": "ok", "id": cid})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a garantir a coleção padrão: {e}"})
        return 1


def cmd_notebook_tree(args):
    """Árvore completa (coleções + notas) do utilizador."""
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        tree = db.notebook_tree(user_id=getattr(args, "user", None))
        _emit(sys.stdout, {"type": "notebook_tree", **tree})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter a árvore do Caderno: {e}"})
        return 1


def cmd_notebook_collection_create(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_collection_create(getattr(args, "user", None), args.title,
                                            parent_id=args.parent_id, kind=args.kind)
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": "Coleção-pai não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "id": res["id"]})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao criar a coleção: {e}"})
        return 1


def cmd_notebook_collection_delete(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_collection_delete(args.id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Coleção #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "message": "Coleção apagada (arquivada no histórico).", **res})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao apagar a coleção: {e}"})
        return 1


def cmd_notebook_note_create(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_note_create(getattr(args, "user", None), args.collection_id, title=args.title)
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": "Coleção de destino não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "id": res["id"]})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao criar a nota: {e}"})
        return 1


def cmd_notebook_note_item(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        item = db.notebook_note_item(args.id, user_id=getattr(args, "user", None))
        if item is None:
            _emit(sys.stdout, {"type": "error", "message": f"Nota #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "notebook_note_item", "item": item})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter a nota: {e}"})
        return 1


def cmd_notebook_note_open(args):
    """Analise arquitetural 2026-08-13, fase B: abrir uma nota disparava 6
    processos separados (item, anotacoes, referencias, links, keywords,
    glossario) — cada um e um spawn de processo + handshake SSH/Postgres a
    parte. Este comando devolve tudo numa unica resposta/ligacao."""
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        bundle = db.notebook_note_open(args.id, user_id=getattr(args, "user", None))
        if bundle is None:
            _emit(sys.stdout, {"type": "error", "message": f"Nota #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "notebook_note_open", **bundle})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a abrir a nota: {e}"})
        return 1


def cmd_notebook_note_update(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        body = sys.stdin.read() if getattr(args, "stdin_body", False) else None
        res = db.notebook_note_update(args.id, user_id=getattr(args, "user", None),
                                      title=args.title, body=body)
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Nota #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "message": "Nota atualizada."})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao atualizar a nota: {e}"})
        return 1


def cmd_notebook_note_delete(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_note_delete(args.id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Nota #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "message": "Nota apagada (arquivada no histórico)."})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao apagar a nota: {e}"})
        return 1


def cmd_notebook_save_document(args):
    """'Salvar no Caderno' (fatia 4): copia a previa (documento estruturado)
    para uma nota nova, com linhagem. Idempotente — devolve a nota existente
    se ja tiver sido salva antes."""
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_save_document_as_note(
            args.document_id, user_id=getattr(args, "user", None), collection_id=args.collection_id,
        )
        if not res.get("ok"):
            messages = {
                "document_not_found": "Documento não encontrado.",
                "collection_not_found": "Coleção de destino não encontrada.",
            }
            _emit(sys.stdout, {"type": "error", "message": messages.get(res.get("error"), "Falha ao salvar no Caderno.")})
            return 1
        # devolve já a nota completa (não só o id) — sem isto, o frontend tinha
        # de fazer uma segunda viagem pelo túnel (notebook-note-item) só para
        # mostrar o que acabou de gravar, e essa nota nunca tinha cache local
        # ainda (é a primeira vez que existe): o utilizador via sempre um
        # "Loading..." logo a seguir a "guardar com sucesso", mesmo sendo
        # conteúdo que o próprio cliente já tinha visto na prévia da Biblioteca.
        note = db.notebook_note_item(res["id"], user_id=getattr(args, "user", None))
        _emit(sys.stdout, {"type": "ok", "id": res["id"], "existed": res.get("existed", False), "note": note})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao salvar no Caderno: {e}"})
        return 1


def cmd_notebook_note_version_create(args):
    """Snapshot manual do estado atual da nota (fatia 5 — "versões")."""
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_note_version_create(args.note_id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Nota #{args.note_id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "id": res["id"]})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao guardar a versão: {e}"})
        return 1


def cmd_notebook_note_versions(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        versions = db.notebook_note_versions(args.note_id, user_id=getattr(args, "user", None))
        if versions is None:
            _emit(sys.stdout, {"type": "error", "message": f"Nota #{args.note_id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "notebook_note_versions", "versions": versions})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter as versões: {e}"})
        return 1


def cmd_notebook_note_version_restore(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_note_version_restore(args.note_id, args.version_id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            messages = {
                "not_found": f"Nota #{args.note_id} não encontrada.",
                "version_not_found": "Versão não encontrada.",
            }
            _emit(sys.stdout, {"type": "error", "message": messages.get(res.get("error"), "Falha ao recuperar a versão.")})
            return 1
        _emit(sys.stdout, {"type": "ok", "message": "Versão recuperada."})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao recuperar a versão: {e}"})
        return 1


def cmd_notebook_annotation_create(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        body = sys.stdin.read()
        res = db.notebook_annotation_create(
            args.note_id, body, user_id=getattr(args, "user", None), block_id=args.block_id,
            start_offset=args.start_offset, end_offset=args.end_offset,
            selected_text=args.selected_text, context_snippet=args.context_snippet,
        )
        if not res.get("ok"):
            messages = {"note_not_found": f"Nota #{args.note_id} não encontrada.", "empty_body": "Comentário vazio."}
            _emit(sys.stdout, {"type": "error", "message": messages.get(res.get("error"), "Falha ao criar a anotação.")})
            return 1
        _emit(sys.stdout, {"type": "ok", "id": res["id"]})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao criar a anotação: {e}"})
        return 1


def cmd_notebook_annotation_list(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        items = db.notebook_annotation_list(args.note_id, user_id=getattr(args, "user", None))
        _emit(sys.stdout, {"type": "notebook_annotation_list", "items": items})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter as anotações: {e}"})
        return 1


def cmd_notebook_annotation_resolve(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_annotation_resolve(args.id, user_id=getattr(args, "user", None), resolved=not args.reopen)
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Anotação #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok"})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao atualizar a anotação: {e}"})
        return 1


def cmd_notebook_annotation_delete(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_annotation_delete(args.id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Anotação #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok"})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao apagar a anotação: {e}"})
        return 1


def cmd_notebook_reference_create(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_reference_create(
            args.note_id, title=args.title, url=args.url, note_text=args.note_text,
            user_id=getattr(args, "user", None),
        )
        if not res.get("ok"):
            messages = {"note_not_found": f"Nota #{args.note_id} não encontrada.", "empty_reference": "Referência vazia (título ou URL)."}
            _emit(sys.stdout, {"type": "error", "message": messages.get(res.get("error"), "Falha ao criar a referência.")})
            return 1
        _emit(sys.stdout, {"type": "ok", "id": res["id"]})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao criar a referência: {e}"})
        return 1


def cmd_notebook_reference_list(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        items = db.notebook_reference_list(args.note_id, user_id=getattr(args, "user", None))
        _emit(sys.stdout, {"type": "notebook_reference_list", "items": items})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter as referências: {e}"})
        return 1


def cmd_notebook_reference_delete(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_reference_delete(args.id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Referência #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok"})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao apagar a referência: {e}"})
        return 1


def cmd_notebook_link_create(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_link_create(args.from_note_id, args.to_note_id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            messages = {
                "note_not_found": f"Nota #{args.from_note_id} não encontrada.",
                "target_not_found": f"Nota #{args.to_note_id} não encontrada.",
                "self_link": "Uma nota não pode ligar a si própria.",
                "already_linked": "Essa ligação já existe.",
            }
            _emit(sys.stdout, {"type": "error", "message": messages.get(res.get("error"), "Falha ao criar a ligação.")})
            return 1
        _emit(sys.stdout, {"type": "ok", "id": res["id"]})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao criar a ligação: {e}"})
        return 1


def cmd_notebook_links(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        links = db.notebook_links(args.note_id, user_id=getattr(args, "user", None))
        _emit(sys.stdout, {"type": "notebook_links", **links})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter as ligações: {e}"})
        return 1


def cmd_notebook_link_delete(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_link_delete(args.id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Ligação #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok"})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao apagar a ligação: {e}"})
        return 1


def cmd_notebook_keyword_create(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_keyword_create(args.note_id, args.term, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            messages = {"note_not_found": f"Nota #{args.note_id} não encontrada.", "empty_term": "Palavra-chave vazia."}
            _emit(sys.stdout, {"type": "error", "message": messages.get(res.get("error"), "Falha ao criar a palavra-chave.")})
            return 1
        _emit(sys.stdout, {"type": "ok", "id": res["id"]})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao criar a palavra-chave: {e}"})
        return 1


def cmd_notebook_keyword_list(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        items = db.notebook_keyword_list(args.note_id, user_id=getattr(args, "user", None))
        _emit(sys.stdout, {"type": "notebook_keyword_list", "items": items})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter as palavras-chave: {e}"})
        return 1


def cmd_notebook_keyword_delete(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_keyword_delete(args.id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Palavra-chave #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok"})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao apagar a palavra-chave: {e}"})
        return 1


def cmd_notebook_glossary_create(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_glossary_create(
            args.note_id, args.term, args.definition, source=args.source, language=args.language,
            user_id=getattr(args, "user", None),
        )
        if not res.get("ok"):
            messages = {"note_not_found": f"Nota #{args.note_id} não encontrada.", "empty_entry": "Termo/definição vazios."}
            _emit(sys.stdout, {"type": "error", "message": messages.get(res.get("error"), "Falha ao criar a entrada do glossário.")})
            return 1
        _emit(sys.stdout, {"type": "ok", "id": res["id"]})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao criar a entrada do glossário: {e}"})
        return 1


def cmd_notebook_glossary_list(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        items = db.notebook_glossary_list(args.note_id, user_id=getattr(args, "user", None))
        _emit(sys.stdout, {"type": "notebook_glossary_list", "items": items})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter o glossário: {e}"})
        return 1


def cmd_notebook_glossary_delete(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        res = db.notebook_glossary_delete(args.id, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Entrada #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok"})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao apagar a entrada do glossário: {e}"})
        return 1


def cmd_notebook_export(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        layers = [l for l in (args.layers or "").split(",") if l.strip()] or None
        res = db.notebook_note_export(args.note_id, layers=layers, fmt=args.format or "markdown",
                                       user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Nota #{args.note_id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "notebook_export", "content": res["content"], "layers": res["layers"],
                            "language": res.get("language") or "pt"})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao exportar: {e}"})
        return 1


def cmd_notebook_context_package_create(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        layers = [l for l in (args.layers or "").split(",") if l.strip()] or None
        res = db.notebook_note_context_package(args.note_id, layers=layers, user_id=getattr(args, "user", None))
        if not res.get("ok"):
            _emit(sys.stdout, {"type": "error", "message": f"Nota #{args.note_id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "ok", "id": res["id"], "manifest": res["manifest"], "prompt": res["prompt"],
                            "language": res.get("language") or "pt"})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha ao gerar o pacote para IA: {e}"})
        return 1


def cmd_notebook_context_packages(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        items = db.notebook_context_packages(args.note_id, user_id=getattr(args, "user", None))
        if items is None:
            _emit(sys.stdout, {"type": "error", "message": f"Nota #{args.note_id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "notebook_context_packages", "items": items})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter os pacotes: {e}"})
        return 1


def cmd_notebook_context_package_item(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        item = db.notebook_context_package_item(args.note_id, args.id, user_id=getattr(args, "user", None))
        if item is None:
            _emit(sys.stdout, {"type": "error", "message": "Pacote não encontrado."})
            return 1
        _emit(sys.stdout, {"type": "notebook_context_package_item", "item": item})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter o pacote: {e}"})
        return 1


def cmd_get_settings(args):
    # Definicoes de armazenamento (para o ecra de Definicoes): pasta padrao
    # em vigor, se e personalizada, e a organizacao por dia/motor.
    from . import db
    s = paths.load_settings()
    _emit(sys.stdout, {
        "type": "settings",
        "storage_dir": str(paths.effective_storage_dir()),
        "storage_dir_custom": bool(s.get("storage_dir")),
        "default_storage_dir": str(paths.TRANSCRIPTS_DIR),
        "organize_by_day_engine": paths.organize_by_day_engine(),
        "storage_mode": db.storage_mode(),
        "vps_configured": db.is_configured(),
        "telemetry_consent": bool(s.get("telemetry_consent", False)),
        # Distingue a recusa explícita da primeira utilização, quando ainda
        # não houve decisão. A UI só mostra o pedido de consentimento neste
        # segundo caso; uma recusa não volta a incomodar a pessoa.
        "telemetry_consent_set": "telemetry_consent" in s,
    })
    return 0


def cmd_set_settings(args):
    s = paths.load_settings()
    if getattr(args, "clear_storage_dir", False):
        s.pop("storage_dir", None)
    elif getattr(args, "storage_dir", None):
        d = Path(args.storage_dir)
        try:
            d.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            _emit(sys.stdout, {"type": "error", "message": f"Pasta invalida: {args.storage_dir} ({e})"})
            return 1
        s["storage_dir"] = str(d)
    if getattr(args, "organize", None) in ("on", "off"):
        s["organize_by_day_engine"] = args.organize == "on"
    if getattr(args, "storage_mode", None) in ("local", "vps"):
        s["storage_mode"] = args.storage_mode
    if getattr(args, "telemetry_consent", None) in ("on", "off"):
        s["telemetry_consent"] = args.telemetry_consent == "on"
        if s["telemetry_consent"]:
            s.setdefault("telemetry_installation_id", str(uuid.uuid4()))
    paths.save_settings(s)
    return cmd_get_settings(args)


def cmd_list_keys(args):
    # Estado de TODAS as chaves numa so chamada (o ecra de Definicoes usa isto
    # em vez de lancar o Python uma vez por chave). "purpose" categoriza por
    # finalidade (transcription/formatting) — decisao de arquitetura
    # 06/08/2026, campo aditivo e retrocompativel para quem ja consome isto.
    keys = [{"name": k, "key_set": bool(get_key(k)), "purpose": key_purposes(k)} for k in KNOWN_KEYS]
    _emit(sys.stdout, {"type": "keys", "keys": keys})
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog="transcription.cli", description="Worker de transcricao do UpexNote")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("engines", help="Lista os motores disponiveis (JSON).")

    p_tr = sub.add_parser("transcribe", help="Transcreve um ficheiro (eventos NDJSON).")
    p_tr.add_argument("--engine", required=True, help=f"ID do motor: {', '.join(ENGINES)}")
    p_tr.add_argument("--file", required=True, help="Caminho do video/audio a transcrever.")
    p_tr.add_argument("--dest", help="Pasta de destino SO desta transcricao (ficheiros gravados diretamente nela).")
    p_tr.add_argument("--user", type=int, help="ID (pk) da conta da sessao — dono da transcricao.")
    p_tr.add_argument("--format-engine", dest="format_engine",
                       help=f"Formata em seguida com este motor: {', '.join(FORMAT_ENGINES)}, ou 'none' pra so transcrever (= 'Formatar depois').")
    p_tr.add_argument("--format-profile", dest="format_profile", choices=["detalhado", "resumo_tecnico", "estudo"],
                       help="Perfil de transformacao (so aplica com --format-engine).")

    sub.add_parser("format-engines", help="Lista os motores de formatacao disponiveis (JSON).")

    p_fmt = sub.add_parser("format", help="Formata um transcript clean em documento estruturado (texto por stdin JSON, eventos NDJSON).")
    p_fmt.add_argument("--engine", required=True, help=f"ID do motor de formatacao: {', '.join(FORMAT_ENGINES)}")
    p_fmt.add_argument("--profile", choices=["detalhado", "resumo_tecnico", "estudo"], default="detalhado", help="Perfil de transformacao.")

    p_dg = sub.add_parser("document-generate", help="Formatacao retroativa: gera e SALVA um documento estruturado a partir de uma transcricao existente.")
    p_dg.add_argument("--transcription-id", type=int, required=True, dest="transcription_id", help="ID da transcricao de origem.")
    p_dg.add_argument("--engine", required=True, help=f"ID do motor de formatacao: {', '.join(FORMAT_ENGINES)}")
    p_dg.add_argument("--profile", choices=["detalhado", "resumo_tecnico", "estudo"], default="detalhado", help="Perfil de transformacao.")
    p_dg.add_argument("--user", type=int, help="ID (pk) da conta da sessao — dono da transcricao.")

    p_ds = sub.add_parser("document-save", help="Guarda (retry) um documento estruturado JA GERADO, sem chamar a IA de novo.")
    p_ds.add_argument("--transcription-id", type=int, required=True, dest="transcription_id")
    p_ds.add_argument("--engine", required=True)
    p_ds.add_argument("--profile", required=True)
    p_ds.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    sub.add_parser("get-settings", help="Definicoes de armazenamento em vigor (JSON).")

    p_ss = sub.add_parser("set-settings", help="Altera as definicoes de armazenamento.")
    p_ss.add_argument("--storage-mode", choices=["local", "vps"], help="Modo de armazenamento: SQLite local ou Postgres/VPS.")
    p_ss.add_argument("--storage-dir", help="Pasta padrao dos transcripts.")
    p_ss.add_argument("--clear-storage-dir", action="store_true", help="Volta a pasta padrao de fabrica.")
    p_ss.add_argument("--organize", choices=["on", "off"], help="Organizar em subpastas dia/motor.")
    p_ss.add_argument("--telemetry-consent", choices=["on", "off"], help="Consentimento explícito para telemetria técnica privada.")

    p_tel = sub.add_parser("telemetry", help="Envia um evento técnico permitido após consentimento.")
    p_tel.add_argument("--event", choices=["app_started", "transcription_completed", "transcription_failed", "login_succeeded", "login_failed"], required=True)
    p_tel.add_argument("--app-version", required=True)
    p_tel.add_argument("--engine")
    p_tel.add_argument("--duration-seconds", type=int)
    p_tel.add_argument("--estimated-cost-micros", type=int)
    p_tel.add_argument("--error-code")
    sub.add_parser("telemetry-overview", help="Resumo administrativo de telemetria (MFA por stdin).")

    p_sk = sub.add_parser("set-key", help="Guarda uma chave (getpass no terminal, ou --stdin para a interface).")
    p_sk.add_argument("--name", required=True, help=f"Nome da chave: {', '.join(KNOWN_KEYS)}")
    p_sk.add_argument("--stdin", action="store_true", help="Le o valor por stdin (uso pela interface).")

    p_clk = sub.add_parser("clear-key", help="Remove uma chave do Windows Credential Manager.")
    p_clk.add_argument("--name", required=True, help=f"Nome da chave: {', '.join(KNOWN_KEYS)}")

    p_ck = sub.add_parser("check-key", help="Diz se uma chave esta configurada (nao revela o valor).")
    p_ck.add_argument("--name", required=True, help=f"Nome da chave: {', '.join(KNOWN_KEYS)}")

    sub.add_parser("list-keys", help="Estado de todas as chaves numa so chamada (JSON).")

    p_dbc = sub.add_parser("db-check", help="Testa a ligacao a base (modo em vigor, ou --mode especifico) e garante o schema.")
    p_dbc.add_argument("--mode", choices=["local", "vps"], help="Testa um modo especifico SEM o gravar.")
    p_dbc.add_argument("--stdin-password", action="store_true", help="Valida uma credencial digitada (via stdin) em vez da guardada.")

    sub.add_parser("db-migrate", help="Migra o schema flat (v1) para hub-and-spoke (v2). Uma vez.")

    p_dbms = sub.add_parser("db-migrate-documents-schema", help="Move as tabelas do ADF-01 (documentos estruturados) de public para o schema Postgres 'documents'. Idempotente, sem perda de dados (VPS apenas).")
    p_dbms.add_argument("--mode", choices=["local", "vps"], help="Forca o modo (sem gravar).")

    p_lib = sub.add_parser("library", help="Historico + agregados da Biblioteca (JSON).")
    p_lib.add_argument("--limit", type=int, default=200, help="Maximo de itens na lista.")
    p_lib.add_argument("--search", help="Filtra por nome do ficheiro (case-insensitive).")
    p_lib.add_argument("--user", type=int, help="ID (pk) da conta da sessao — admin ve tudo, user so o seu.")
    p_lib.add_argument("--json-stdin", action="store_true", help="Prova MFA por stdin (uso da app).")

    p_libi = sub.add_parser("library-item", help="Uma transcricao completa, com texto (JSON).")
    p_libi.add_argument("--id", type=int, required=True, help="ID da transcricao.")
    p_libi.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")
    p_libi.add_argument("--json-stdin", action="store_true", help="Prova MFA por stdin (uso da app).")

    p_libu = sub.add_parser("library-update", help="Edita o texto clean (le stdin); a raw fica intacta.")
    p_libu.add_argument("--id", type=int, required=True, help="ID da transcricao.")
    p_libu.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")
    p_libu.add_argument("--json-stdin", action="store_true", help="Texto + prova MFA em JSON por stdin.")

    p_libd = sub.add_parser("library-delete", help="Apaga uma transcricao (arquiva no historico).")
    p_libd.add_argument("--id", type=int, required=True, help="ID da transcricao.")
    p_libd.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")
    p_libd.add_argument("--json-stdin", action="store_true", help="Prova MFA por stdin (uso da app).")

    p_doci = sub.add_parser("document-item", help="Um documento estruturado completo: blocos, glossario e metricas (JSON).")
    p_doci.add_argument("--id", type=int, required=True, help="ID do documento.")
    p_doci.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")
    p_doci.add_argument("--json-stdin", action="store_true", help="Prova MFA por stdin (uso da app).")

    p_docd = sub.add_parser("document-delete", help="Apaga um documento estruturado (arquiva no historico); o transcript fica intacto.")
    p_docd.add_argument("--id", type=int, required=True, help="ID do documento.")
    p_docd.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")
    p_docd.add_argument("--json-stdin", action="store_true", help="Prova MFA por stdin (uso da app).")

    p_nbed = sub.add_parser("notebook-ensure-default", help="Garante (cria se preciso) a colecao padrao do Caderno do utilizador.")
    p_nbed.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbt = sub.add_parser("notebook-tree", help="Arvore completa (colecoes + notas) do Caderno do utilizador (JSON).")
    p_nbt.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbcc = sub.add_parser("notebook-collection-create", help="Cria pasta/projeto/caderno/seccao.")
    p_nbcc.add_argument("--title", required=True, help="Titulo da colecao.")
    p_nbcc.add_argument("--kind", choices=["folder", "project", "notebook", "section"], default="notebook")
    p_nbcc.add_argument("--parent-id", type=int, dest="parent_id", help="Colecao-mae (omitir = raiz).")
    p_nbcc.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbcd = sub.add_parser("notebook-collection-delete", help="Apaga uma colecao e as suas descendentes/notas (arquiva no historico).")
    p_nbcd.add_argument("--id", type=int, required=True, help="ID da colecao.")
    p_nbcd.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbnc = sub.add_parser("notebook-note-create", help="Cria uma nota vazia numa colecao.")
    p_nbnc.add_argument("--collection-id", type=int, required=True, dest="collection_id", help="Colecao de destino.")
    p_nbnc.add_argument("--title", help="Titulo da nota (opcional).")
    p_nbnc.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbni = sub.add_parser("notebook-note-item", help="Uma nota completa: titulo + corpo (JSON).")
    p_nbni.add_argument("--id", type=int, required=True, help="ID da nota.")
    p_nbni.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbno = sub.add_parser("notebook-note-open", help="Abrir nota: item + anotacoes + referencias + links + keywords + glossario numa so chamada (analise arquitetural 2026-08-13, fase B).")
    p_nbno.add_argument("--id", type=int, required=True, help="ID da nota.")
    p_nbno.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbnu = sub.add_parser("notebook-note-update", help="Edita titulo e/ou corpo de uma nota (corpo por stdin).")
    p_nbnu.add_argument("--id", type=int, required=True, help="ID da nota.")
    p_nbnu.add_argument("--title", help="Novo titulo (omitir = mantem).")
    p_nbnu.add_argument("--stdin-body", action="store_true", help="Le o novo corpo por stdin (omitir = mantem o corpo).")
    p_nbnu.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbnd = sub.add_parser("notebook-note-delete", help="Apaga uma nota (arquiva no historico).")
    p_nbnd.add_argument("--id", type=int, required=True, help="ID da nota.")
    p_nbnd.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbsd = sub.add_parser("notebook-save-document", help="'Salvar no Caderno': copia a previa (documento estruturado) para uma nota nova, com linhagem. Idempotente.")
    p_nbsd.add_argument("--document-id", type=int, required=True, dest="document_id", help="ID do documento estruturado (previa) de origem.")
    p_nbsd.add_argument("--collection-id", type=int, dest="collection_id", help="Colecao de destino (omitir = colecao padrao).")
    p_nbsd.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbvc = sub.add_parser("notebook-note-version-create", help="Snapshot manual do estado atual da nota (fatia 5, versoes).")
    p_nbvc.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbvc.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbvl = sub.add_parser("notebook-note-versions", help="Lista as versoes guardadas de uma nota (fatia 5).")
    p_nbvl.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbvl.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbvr = sub.add_parser("notebook-note-version-restore", help="Recupera uma versao antiga da nota (fatia 5).")
    p_nbvr.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbvr.add_argument("--version-id", type=int, required=True, dest="version_id")
    p_nbvr.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbac = sub.add_parser("notebook-annotation-create", help="Cria uma anotacao ancorada num trecho da nota (fatia 6). Corpo por stdin.")
    p_nbac.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbac.add_argument("--block-id", dest="block_id", help="ID estavel do bloco onde a selecao comeca.")
    p_nbac.add_argument("--start-offset", type=int, dest="start_offset")
    p_nbac.add_argument("--end-offset", type=int, dest="end_offset")
    p_nbac.add_argument("--selected-text", dest="selected_text")
    p_nbac.add_argument("--context-snippet", dest="context_snippet")
    p_nbac.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbal = sub.add_parser("notebook-annotation-list", help="Lista as anotacoes de uma nota (fatia 6).")
    p_nbal.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbal.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbar = sub.add_parser("notebook-annotation-resolve", help="Marca/desmarca uma anotacao como resolvida (fatia 6).")
    p_nbar.add_argument("--id", type=int, required=True)
    p_nbar.add_argument("--reopen", action="store_true", help="Desmarca como resolvida (reabre).")
    p_nbar.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbad = sub.add_parser("notebook-annotation-delete", help="Apaga uma anotacao (arquiva no historico) (fatia 6).")
    p_nbad.add_argument("--id", type=int, required=True)
    p_nbad.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbrc = sub.add_parser("notebook-reference-create", help="Cria uma referencia de estudo associada a nota (fatia 6).")
    p_nbrc.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbrc.add_argument("--title")
    p_nbrc.add_argument("--url")
    p_nbrc.add_argument("--note-text", dest="note_text")
    p_nbrc.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbrl = sub.add_parser("notebook-reference-list", help="Lista as referencias de uma nota (fatia 6).")
    p_nbrl.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbrl.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbrd = sub.add_parser("notebook-reference-delete", help="Apaga uma referencia (arquiva no historico) (fatia 6).")
    p_nbrd.add_argument("--id", type=int, required=True)
    p_nbrd.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nblc = sub.add_parser("notebook-link-create", help="Liga uma nota a outra nota do Caderno (backlinks).")
    p_nblc.add_argument("--from-note-id", type=int, required=True, dest="from_note_id")
    p_nblc.add_argument("--to-note-id", type=int, required=True, dest="to_note_id")
    p_nblc.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbls = sub.add_parser("notebook-links", help="Lista as ligacoes de saida e os backlinks de uma nota.")
    p_nbls.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbls.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbld = sub.add_parser("notebook-link-delete", help="Apaga uma ligacao entre notas (arquiva no historico).")
    p_nbld.add_argument("--id", type=int, required=True)
    p_nbld.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbkc = sub.add_parser("notebook-keyword-create", help="Cria uma palavra-chave associada a nota (fatia 7).")
    p_nbkc.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbkc.add_argument("--term", required=True)
    p_nbkc.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbkl = sub.add_parser("notebook-keyword-list", help="Lista as palavras-chave de uma nota (fatia 7).")
    p_nbkl.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbkl.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbkd = sub.add_parser("notebook-keyword-delete", help="Apaga uma palavra-chave (fatia 7).")
    p_nbkd.add_argument("--id", type=int, required=True)
    p_nbkd.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbgc = sub.add_parser("notebook-glossary-create", help="Cria uma entrada de glossario associada a nota (fatia 7).")
    p_nbgc.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbgc.add_argument("--term", required=True)
    p_nbgc.add_argument("--definition", required=True)
    p_nbgc.add_argument("--source")
    p_nbgc.add_argument("--language")
    p_nbgc.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbgl = sub.add_parser("notebook-glossary-list", help="Lista o glossario de uma nota (fatia 7).")
    p_nbgl.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbgl.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbgd = sub.add_parser("notebook-glossary-delete", help="Apaga uma entrada de glossario (fatia 7).")
    p_nbgd.add_argument("--id", type=int, required=True)
    p_nbgd.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbex = sub.add_parser("notebook-export", help="Monta o conteudo exportavel da nota a partir das camadas escolhidas (fatia 8).")
    p_nbex.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbex.add_argument("--layers", help="Lista separada por virgulas: body,annotations,references,glossary,lineage.")
    p_nbex.add_argument("--format", default="markdown")
    p_nbex.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbcp = sub.add_parser("notebook-context-package-create", help="Gera o pacote de contexto para IA (manifesto + prompt) (fatia 8).")
    p_nbcp.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbcp.add_argument("--layers", help="Lista separada por virgulas: body,annotations,references,glossary,lineage.")
    p_nbcp.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbcpl = sub.add_parser("notebook-context-packages", help="Lista os pacotes de contexto ja gerados para uma nota (fatia 8).")
    p_nbcpl.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbcpl.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_nbcpi = sub.add_parser("notebook-context-package-item", help="Devolve manifesto+prompt de um pacote de contexto ja gerado (fatia 8).")
    p_nbcpi.add_argument("--note-id", type=int, required=True, dest="note_id")
    p_nbcpi.add_argument("--id", type=int, required=True)
    p_nbcpi.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")

    p_lack = sub.add_parser("library-ack", help="Marca/desmarca os avisos de validacao como revistos.")
    p_lack.add_argument("--id", type=int, required=True, help="ID da transcricao.")
    p_lack.add_argument("--reopen", action="store_true", help="Reabre o aviso (em vez de marcar como revisto).")
    p_lack.add_argument("--user", type=int, help="ID (pk) da conta da sessao.")
    p_lack.add_argument("--json-stdin", action="store_true", help="Prova MFA por stdin (uso da app).")

    p_adopt = sub.add_parser("db-adopt-orphans", help="Atribui transcricoes sem dono a conta com este e-mail (migracao unica).")
    p_adopt.add_argument("--email", required=True, help="E-mail da conta que herda o legado.")
    p_adopt.add_argument("--mode", choices=["local", "vps"], help="Forca o modo (sem gravar).")

    sub.add_parser("tunnel-keep", help="(interno) Guardiao do tunel SSH persistente; termina no EOF do stdin.")

    for name in ("account-register", "account-login", "account-oauth-login",
                 "account-update", "account-profile", "account-elevate"):
        p_acc = sub.add_parser(name, help="Identidade (dados por stdin, JSON).")
        p_acc.add_argument("--mode", choices=["local", "vps"],
                           help="Base alvo (contas admin vivem na vps). Sem gravar.")
    p_asg = sub.add_parser("account-suggest", help="Disponibilidade de user_id + sugestoes.")
    p_asg.add_argument("--user-id", required=True)
    p_asg.add_argument("--mode", choices=["local", "vps"], help="Base alvo. Sem gravar.")

    for name in ("admin-overview", "admin-users", "admin-create-user", "admin-update-user",
                 "admin-delete-user", "admin-events", "admin-audit",
                 "admin-data-catalog", "admin-data-table", "admin-data-query", "admin-data-sql",
                 "admin-data-saved-queries"):
        p_adm = sub.add_parser(name, help="Administracao (payload por stdin; ator revalidado na base).")
        p_adm.add_argument("--mode", choices=["local", "vps"], help="Base alvo. Sem gravar.")
    p_oa = sub.add_parser("oauth", help="Login social (Google loopback+PKCE / GitHub device flow).")
    p_oa.add_argument("--provider", choices=["google", "github"], required=True)

    for name in ("api-reset-request", "api-reset-verify", "api-reset-complete"):
        sub.add_parser(name, help="Recuperacao de senha via API HTTPS (payload JSON por stdin).")

    for name in ("support-identity", "support-create", "support-list", "support-detail", "support-comment", "support-attachment",
                 "support-admin-list", "support-admin-detail", "support-admin-comment", "support-admin-status", "support-admin-assignment"):
        sub.add_parser(name, help="Chamados de suporte via API HTTPS (payload JSON por stdin).")

    for name in ("api-admin-challenge", "api-admin-verify", "api-admin-validate",
                 "api-admin-revoke", "api-admin-totp-enroll", "api-admin-totp-confirm"):
        sub.add_parser(name, help="MFA administrativo via API HTTPS (payload JSON por stdin).")

    sub.add_parser(
        "serve",
        help=(
            "Fase A da analise arquitetural (2026-08-13): worker persistente. "
            "Fica vivo a espera de pedidos por stdin (uma linha JSON por pedido: "
            "{id, argv, stdin}) e responde por stdout (linhas {id, line} seguidas "
            "de {id, done: true}) — em vez de um processo novo por comando."
        ),
    )

    return parser


def _build_handlers():
    """Extraido de main() (2026-08-13, Fase A) para ser reutilizado por
    cmd_serve() sem duplicar esta tabela inteira."""
    return {
        "engines": cmd_engines,
        "transcribe": cmd_transcribe,
        "format-engines": cmd_format_engines,
        "format": cmd_format,
        "document-generate": cmd_document_generate,
        "document-save": cmd_document_save,
        "set-key": cmd_set_key,
        "clear-key": cmd_clear_key,
        "check-key": cmd_check_key,
        "list-keys": cmd_list_keys,
        "db-check": cmd_db_check,
        "db-migrate": cmd_db_migrate,
        "db-migrate-documents-schema": cmd_db_migrate_documents_schema,
        "get-settings": cmd_get_settings,
        "set-settings": cmd_set_settings,
        "telemetry": cmd_telemetry,
        "telemetry-overview": cmd_telemetry_overview,
        "library": cmd_library,
        "library-item": cmd_library_item,
        "library-update": cmd_library_update,
        "library-delete": cmd_library_delete,
        "document-item": cmd_document_item,
        "document-delete": cmd_document_delete,
        "notebook-ensure-default": cmd_notebook_ensure_default,
        "notebook-tree": cmd_notebook_tree,
        "notebook-collection-create": cmd_notebook_collection_create,
        "notebook-collection-delete": cmd_notebook_collection_delete,
        "notebook-note-create": cmd_notebook_note_create,
        "notebook-note-item": cmd_notebook_note_item,
        "notebook-note-open": cmd_notebook_note_open,
        "notebook-note-update": cmd_notebook_note_update,
        "notebook-note-delete": cmd_notebook_note_delete,
        "notebook-save-document": cmd_notebook_save_document,
        "notebook-note-version-create": cmd_notebook_note_version_create,
        "notebook-note-versions": cmd_notebook_note_versions,
        "notebook-note-version-restore": cmd_notebook_note_version_restore,
        "notebook-annotation-create": cmd_notebook_annotation_create,
        "notebook-annotation-list": cmd_notebook_annotation_list,
        "notebook-annotation-resolve": cmd_notebook_annotation_resolve,
        "notebook-annotation-delete": cmd_notebook_annotation_delete,
        "notebook-reference-create": cmd_notebook_reference_create,
        "notebook-reference-list": cmd_notebook_reference_list,
        "notebook-reference-delete": cmd_notebook_reference_delete,
        "notebook-link-create": cmd_notebook_link_create,
        "notebook-links": cmd_notebook_links,
        "notebook-link-delete": cmd_notebook_link_delete,
        "notebook-keyword-create": cmd_notebook_keyword_create,
        "notebook-keyword-list": cmd_notebook_keyword_list,
        "notebook-keyword-delete": cmd_notebook_keyword_delete,
        "notebook-glossary-create": cmd_notebook_glossary_create,
        "notebook-glossary-list": cmd_notebook_glossary_list,
        "notebook-glossary-delete": cmd_notebook_glossary_delete,
        "notebook-export": cmd_notebook_export,
        "notebook-context-package-create": cmd_notebook_context_package_create,
        "notebook-context-packages": cmd_notebook_context_packages,
        "notebook-context-package-item": cmd_notebook_context_package_item,
        "library-ack": cmd_library_ack,
        "tunnel-keep": cmd_tunnel_keep,
        "db-adopt-orphans": cmd_db_adopt_orphans,
        "account-register": cmd_account,
        "account-login": cmd_account,
        "account-oauth-login": cmd_account,
        "account-update": cmd_account,
        "account-profile": cmd_account,
        "account-elevate": cmd_account,
        "account-suggest": cmd_account,
        "admin-overview": cmd_admin,
        "admin-users": cmd_admin,
        "admin-create-user": cmd_admin,
        "admin-update-user": cmd_admin,
        "admin-delete-user": cmd_admin,
        "admin-events": cmd_admin,
        "admin-audit": cmd_admin,
        "admin-data-catalog": cmd_admin,
        "admin-data-table": cmd_admin,
        "admin-data-query": cmd_admin,
        "admin-data-sql": cmd_admin,
        "admin-data-saved-queries": cmd_admin,
        "oauth": cmd_oauth,
        "api-reset-request": cmd_api_reset,
        "api-reset-verify": cmd_api_reset,
        "api-reset-complete": cmd_api_reset,
        "support-identity": cmd_support,
        "support-create": cmd_support,
        "support-list": cmd_support,
        "support-detail": cmd_support,
        "support-comment": cmd_support,
        "support-attachment": cmd_support,
        "support-admin-list": cmd_support,
        "support-admin-detail": cmd_support,
        "support-admin-comment": cmd_support,
        "support-admin-status": cmd_support,
        "support-admin-assignment": cmd_support,
        "api-admin-challenge": cmd_api_admin_factor,
        "api-admin-verify": cmd_api_admin_factor,
        "api-admin-validate": cmd_api_admin_factor,
        "api-admin-revoke": cmd_api_admin_factor,
        "api-admin-totp-enroll": cmd_api_admin_factor,
        "api-admin-totp-confirm": cmd_api_admin_factor,
        "serve": cmd_serve,
    }


def cmd_serve(args):
    """Fase A da analise arquitetural (2026-08-13): worker persistente.

    Em vez de um processo do SO novo por comando (o padrao ate aqui — caro
    sobretudo em modo desenvolvimento, onde cada arranque reimporta tudo do
    zero), este comando fica vivo a ler pedidos de stdin, um por linha JSON:
        {"id": "<qualquer string>", "argv": ["notebook-note-open", "--id", "5"],
         "stdin": "<opcional — substitui o stdin real para este pedido>"}
    e responde por stdout, tambem por linha:
        {"id": "<mesmo id>", "line": "<uma linha NDJSON original do comando>"}
        ... (zero ou mais)
        {"id": "<mesmo id>", "done": true}

    Os handlers `cmd_*` nao mudam nada — continuam a escrever em sys.stdout e
    a ler de sys.stdin exatamente como sempre fizeram. Este loop troca
    temporariamente os dois (por StringIO) a volta de cada pedido, captura o
    que foi escrito, e devolve-o envelopado com o id do pedido — e' assim que
    um handler que le `sys.stdin.read()` para o corpo de uma nota continua a
    funcionar sem alteracoes, mesmo com o stdin REAL do processo ocupado a
    servir de canal de pedidos do loop.
    """
    import io

    parser = build_parser()
    handlers = _build_handlers()
    real_stdout = sys.stdout
    real_stdin = sys.stdin

    for raw_line in real_stdin:
        raw_line = raw_line.strip()
        if not raw_line:
            continue
        try:
            req = json.loads(raw_line)
        except Exception:  # noqa: BLE001 — linha corrompida: ignora, nao ha id para responder
            continue

        req_id = req.get("id")
        argv = req.get("argv") or []
        stdin_data = req.get("stdin") or ""

        out_buf = io.StringIO()
        in_buf = io.StringIO(stdin_data)
        sys.stdout = out_buf
        sys.stdin = in_buf
        try:
            ns = parser.parse_args(argv)
            handler = handlers.get(ns.command)
            if handler is None:
                _emit(out_buf, {"type": "error", "message": f"comando desconhecido: {ns.command}"})
            else:
                handler(ns)
        except SystemExit:
            # argparse chama sys.exit em erro de parsing dos argumentos —
            # apanha-se aqui para o loop nao morrer por causa de UM pedido mal formado.
            _emit(out_buf, {"type": "error", "message": "argumentos invalidos para este comando"})
        except Exception as e:  # noqa: BLE001 — qualquer falha de um handler fica isolada a este pedido
            _emit(out_buf, {"type": "error", "message": str(e)})
        finally:
            sys.stdout = real_stdout
            sys.stdin = real_stdin

        for out_line in out_buf.getvalue().splitlines():
            if not out_line.strip():
                continue
            real_stdout.write(json.dumps({"id": req_id, "line": out_line}) + "\n")
        real_stdout.write(json.dumps({"id": req_id, "done": True}) + "\n")
        real_stdout.flush()

    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = _build_handlers()
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
