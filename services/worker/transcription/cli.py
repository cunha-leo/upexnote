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

  transcribe --engine <id> --file "<caminho>"
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

  set-key --name <NOME_DA_CHAVE>
      Le o valor por stdin sem eco e guarda-o no Windows Credential
      Manager. Corre isto tu mesmo no teu terminal.

  check-key --name <NOME_DA_CHAVE>
      Diz se a chave esta configurada (JSON), sem nunca revelar o valor.

Exemplos:
    python -m transcription.cli engines
    python -m transcription.cli transcribe --engine assemblyai --file "C:/gravacoes/reuniao.mp4"
    python -m transcription.cli set-key --name ASSEMBLYAI_API_KEY
"""
import argparse
import json
import sys
import time
import uuid
from pathlib import Path

from . import paths
from .registry import ENGINES
from .credentials import get_key, set_key, clear_key, KNOWN_KEYS


def _emit(stream, event):
    stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    stream.flush()


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
    try:
        from . import db
        raw_text = None
        rp = result.get("raw_path")
        if rp and Path(rp).exists():
            raw_text = Path(rp).read_text(encoding="utf-8")
        db.insert_transcription({
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

    return 0 if result["ok"] else 2


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
    from . import accounts, db
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
    # em vez de lancar o Python uma vez por chave).
    keys = [{"name": k, "key_set": bool(get_key(k))} for k in KNOWN_KEYS]
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

    sub.add_parser("get-settings", help="Definicoes de armazenamento em vigor (JSON).")

    p_ss = sub.add_parser("set-settings", help="Altera as definicoes de armazenamento.")
    p_ss.add_argument("--storage-mode", choices=["local", "vps"], help="Modo de armazenamento: SQLite local ou Postgres/VPS.")
    p_ss.add_argument("--storage-dir", help="Pasta padrao dos transcripts.")
    p_ss.add_argument("--clear-storage-dir", action="store_true", help="Volta a pasta padrao de fabrica.")
    p_ss.add_argument("--organize", choices=["on", "off"], help="Organizar em subpastas dia/motor.")
    p_ss.add_argument("--telemetry-consent", choices=["on", "off"], help="Consentimento explícito para telemetria técnica privada.")

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
                 "account-update", "account-elevate"):
        p_acc = sub.add_parser(name, help="Identidade (dados por stdin, JSON).")
        p_acc.add_argument("--mode", choices=["local", "vps"],
                           help="Base alvo (contas admin vivem na vps). Sem gravar.")
    p_asg = sub.add_parser("account-suggest", help="Disponibilidade de user_id + sugestoes.")
    p_asg.add_argument("--user-id", required=True)
    p_asg.add_argument("--mode", choices=["local", "vps"], help="Base alvo. Sem gravar.")

    for name in ("admin-overview", "admin-users", "admin-create-user", "admin-update-user",
                 "admin-delete-user", "admin-events", "admin-audit"):
        p_adm = sub.add_parser(name, help="Administracao (payload por stdin; ator revalidado na base).")
        p_adm.add_argument("--mode", choices=["local", "vps"], help="Base alvo. Sem gravar.")
    p_oa = sub.add_parser("oauth", help="Login social (Google loopback+PKCE / GitHub device flow).")
    p_oa.add_argument("--provider", choices=["google", "github"], required=True)

    for name in ("api-reset-request", "api-reset-verify", "api-reset-complete"):
        sub.add_parser(name, help="Recuperacao de senha via API HTTPS (payload JSON por stdin).")

    for name in ("api-admin-challenge", "api-admin-verify", "api-admin-validate",
                 "api-admin-revoke", "api-admin-totp-enroll", "api-admin-totp-confirm"):
        sub.add_parser(name, help="MFA administrativo via API HTTPS (payload JSON por stdin).")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "engines": cmd_engines,
        "transcribe": cmd_transcribe,
        "set-key": cmd_set_key,
        "clear-key": cmd_clear_key,
        "check-key": cmd_check_key,
        "list-keys": cmd_list_keys,
        "db-check": cmd_db_check,
        "db-migrate": cmd_db_migrate,
        "get-settings": cmd_get_settings,
        "set-settings": cmd_set_settings,
        "library": cmd_library,
        "library-item": cmd_library_item,
        "library-update": cmd_library_update,
        "library-delete": cmd_library_delete,
        "library-ack": cmd_library_ack,
        "tunnel-keep": cmd_tunnel_keep,
        "db-adopt-orphans": cmd_db_adopt_orphans,
        "account-register": cmd_account,
        "account-login": cmd_account,
        "account-oauth-login": cmd_account,
        "account-update": cmd_account,
        "account-elevate": cmd_account,
        "account-suggest": cmd_account,
        "admin-overview": cmd_admin,
        "admin-users": cmd_admin,
        "admin-create-user": cmd_admin,
        "admin-update-user": cmd_admin,
        "admin-delete-user": cmd_admin,
        "admin-events": cmd_admin,
        "admin-audit": cmd_admin,
        "oauth": cmd_oauth,
        "api-reset-request": cmd_api_reset,
        "api-reset-verify": cmd_api_reset,
        "api-reset-complete": cmd_api_reset,
        "api-admin-challenge": cmd_api_admin_factor,
        "api-admin-verify": cmd_api_admin_factor,
        "api-admin-validate": cmd_api_admin_factor,
        "api-admin-revoke": cmd_api_admin_factor,
        "api-admin-totp-enroll": cmd_api_admin_factor,
        "api-admin-totp-confirm": cmd_api_admin_factor,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
