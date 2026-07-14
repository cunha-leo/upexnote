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


def cmd_db_check(args):
    from . import db
    if not db.load_config():
        _emit(sys.stdout, {"type": "error", "message": "db_config.json não encontrado — copia db_config.example.json para db_config.json."})
        return 1
    if not get_key(db.PG_PASSWORD_KEY):
        _emit(sys.stdout, {"type": "error", "message": f"Password não configurada. Corre: set-key --name {db.PG_PASSWORD_KEY}"})
        return 1
    try:
        res = db.check()
        _emit(sys.stdout, {"type": "db", "ok": True, "rows": res["rows"],
                           "message": f"Ligação OK. Tabela 'transcriptions' pronta. Linhas atuais: {res['rows']}."})
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
    """Valida config+password da DB; devolve mensagem de erro ou None."""
    from . import db
    if not db.load_config():
        return "db_config.json não encontrado — copia db_config.example.json para db_config.json."
    if not get_key(db.PG_PASSWORD_KEY):
        return f"Password do Postgres não configurada. Corre: set-key --name {db.PG_PASSWORD_KEY}"
    return None


def cmd_library(args):
    from . import db
    err = _require_db()
    if err:
        _emit(sys.stdout, {"type": "error", "message": err})
        return 1
    try:
        summary = db.library_summary()
        items = db.library_list(limit=getattr(args, "limit", 200) or 200,
                                search=getattr(args, "search", None))
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
        item = db.library_item(args.id)
        if item is None:
            _emit(sys.stdout, {"type": "error", "message": f"Transcrição #{args.id} não encontrada."})
            return 1
        _emit(sys.stdout, {"type": "library_item", "item": item})
        return 0
    except Exception as e:  # noqa: BLE001
        _emit(sys.stdout, {"type": "error", "message": f"Falha a obter a transcrição: {e}"})
        return 1


def cmd_get_settings(args):
    # Definicoes de armazenamento (para o ecra de Definicoes): pasta padrao
    # em vigor, se e personalizada, e a organizacao por dia/motor.
    s = paths.load_settings()
    _emit(sys.stdout, {
        "type": "settings",
        "storage_dir": str(paths.effective_storage_dir()),
        "storage_dir_custom": bool(s.get("storage_dir")),
        "default_storage_dir": str(paths.TRANSCRIPTS_DIR),
        "organize_by_day_engine": paths.organize_by_day_engine(),
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

    sub.add_parser("get-settings", help="Definicoes de armazenamento em vigor (JSON).")

    p_ss = sub.add_parser("set-settings", help="Altera as definicoes de armazenamento.")
    p_ss.add_argument("--storage-dir", help="Pasta padrao dos transcripts.")
    p_ss.add_argument("--clear-storage-dir", action="store_true", help="Volta a pasta padrao de fabrica.")
    p_ss.add_argument("--organize", choices=["on", "off"], help="Organizar em subpastas dia/motor.")

    p_sk = sub.add_parser("set-key", help="Guarda uma chave (getpass no terminal, ou --stdin para a interface).")
    p_sk.add_argument("--name", required=True, help=f"Nome da chave: {', '.join(KNOWN_KEYS)}")
    p_sk.add_argument("--stdin", action="store_true", help="Le o valor por stdin (uso pela interface).")

    p_clk = sub.add_parser("clear-key", help="Remove uma chave do Windows Credential Manager.")
    p_clk.add_argument("--name", required=True, help=f"Nome da chave: {', '.join(KNOWN_KEYS)}")

    p_ck = sub.add_parser("check-key", help="Diz se uma chave esta configurada (nao revela o valor).")
    p_ck.add_argument("--name", required=True, help=f"Nome da chave: {', '.join(KNOWN_KEYS)}")

    sub.add_parser("list-keys", help="Estado de todas as chaves numa so chamada (JSON).")

    sub.add_parser("db-check", help="Testa a ligacao ao Postgres da VPS e garante a tabela.")

    p_lib = sub.add_parser("library", help="Historico + agregados da Biblioteca (JSON).")
    p_lib.add_argument("--limit", type=int, default=200, help="Maximo de itens na lista.")
    p_lib.add_argument("--search", help="Filtra por nome do ficheiro (case-insensitive).")

    p_libi = sub.add_parser("library-item", help="Uma transcricao completa, com texto (JSON).")
    p_libi.add_argument("--id", type=int, required=True, help="ID da transcricao.")

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
        "get-settings": cmd_get_settings,
        "set-settings": cmd_set_settings,
        "library": cmd_library,
        "library-item": cmd_library_item,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
