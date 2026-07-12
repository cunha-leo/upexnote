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
from pathlib import Path

from .registry import ENGINES
from .credentials import get_key, set_key, KNOWN_KEYS


def _emit(stream, event):
    stream.write(json.dumps(event, ensure_ascii=False) + "\n")
    stream.flush()


def _jsonable(value):
    if isinstance(value, Path):
        return str(value)
    return value


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

    api_key = get_key(engine["key_name"])
    if not api_key:
        _emit(real_stdout, {
            "type": "error",
            "message": f"Chave {engine['key_name']} nao configurada. Corre: "
                       f"python -m transcription.cli set-key --name {engine['key_name']}",
        })
        return 1

    _emit(real_stdout, {"type": "start", "engine": args.engine, "file": file_path})

    # Prints soltos dentro do pipeline (ex.: audio_chunks) vao para stderr,
    # para o stdout ficar so com NDJSON limpo. Os nossos eventos de progresso
    # sao emitidos pela referencia guardada ao stdout real.
    sys.stdout = sys.stderr
    try:
        result = engine["run"](
            file_path, api_key,
            log=lambda m: _emit(real_stdout, {"type": "progress", "message": str(m)}),
        )
    except Exception as e:  # noqa: BLE001 - queremos reportar qualquer falha como evento
        sys.stdout = real_stdout
        _emit(real_stdout, {"type": "error", "message": str(e)})
        return 1
    finally:
        sys.stdout = real_stdout

    _emit(real_stdout, {
        "type": "result",
        "ok": result["ok"],
        "clean_text": result["clean_text"],
        "clean_path": _jsonable(result["clean_path"]),
        "raw_path": _jsonable(result["raw_path"]),
        "cost": result["cost"],
        "duration_s": result["duration_s"],
        "problems": result.get("problems", []),
        "language": result.get("language"),
    })
    return 0 if result["ok"] else 2


def cmd_set_key(args):
    import getpass
    if args.name not in KNOWN_KEYS:
        _emit(sys.stdout, {
            "type": "error",
            "message": f"Nome de chave desconhecido: {args.name!r}. Opcoes: {', '.join(KNOWN_KEYS)}",
        })
        return 1
    try:
        value = getpass.getpass(f"Cola a {args.name} (nao aparece no ecra) e Enter: ")
    except (EOFError, KeyboardInterrupt):
        _emit(sys.stdout, {"type": "error", "message": "Cancelado."})
        return 1
    value = value.strip()
    if not value:
        _emit(sys.stdout, {"type": "error", "message": "Nenhum valor introduzido; nada foi guardado."})
        return 1
    set_key(args.name, value)
    _emit(sys.stdout, {"type": "ok", "message": f"{args.name} guardada no Windows Credential Manager."})
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


def build_parser():
    parser = argparse.ArgumentParser(prog="transcription.cli", description="Worker de transcricao do UpexNote")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("engines", help="Lista os motores disponiveis (JSON).")

    p_tr = sub.add_parser("transcribe", help="Transcreve um ficheiro (eventos NDJSON).")
    p_tr.add_argument("--engine", required=True, help=f"ID do motor: {', '.join(ENGINES)}")
    p_tr.add_argument("--file", required=True, help="Caminho do video/audio a transcrever.")

    p_sk = sub.add_parser("set-key", help="Guarda uma chave API (le por stdin, sem eco).")
    p_sk.add_argument("--name", required=True, help=f"Nome da chave: {', '.join(KNOWN_KEYS)}")

    p_ck = sub.add_parser("check-key", help="Diz se uma chave esta configurada (nao revela o valor).")
    p_ck.add_argument("--name", required=True, help=f"Nome da chave: {', '.join(KNOWN_KEYS)}")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "engines": cmd_engines,
        "transcribe": cmd_transcribe,
        "set-key": cmd_set_key,
        "check-key": cmd_check_key,
    }
    return handlers[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
