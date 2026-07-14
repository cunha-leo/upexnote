r"""
Caminhos partilhados - decide ONDE os transcripts sao gravados.

O video/audio de origem NUNCA e copiado para dentro do projeto - o
utilizador escolhe um caminho qualquer do Windows e so esse caminho e lido.

Resolucao da pasta de destino (decisao 2026-07-13, ver PROJECT_CONTEXT):
  1. Override pontual "--dest" da CLI (o utilizador escolheu "guardar em..."
     so para esta transcricao) - os ficheiros vao DIRETOS para essa pasta.
  2. Pasta padrao definida pelo utilizador em settings.json
     (%APPDATA%\UpexNote\settings.json, campo "storage_dir").
  3. Padrao de fabrica: Documentos\UpexNote\storage\transcripts (app
     empacotada) ou storage\transcripts do repo (desenvolvimento).

A organizacao em subpastas <AAAA-MM-DD>\<motor>\ e OPCIONAL
("organize_by_day_engine" em settings.json, ligada por defeito) - o
utilizador pode preferir a estrutura de pastas dele, sem imposicoes.
O nome do ficheiro carrega sempre origem+data+motor+tipo, por isso
identifica-se sozinho mesmo numa pasta plana.
"""
import json
import os
import sys
from datetime import date
from pathlib import Path

if getattr(sys, "frozen", False):
    # Executavel empacotado (sidecar): padrao de fabrica numa pasta estavel
    # e visivel do utilizador, que sobrevive a atualizacoes da app.
    PROJECT_DIR = Path.home() / "Documents" / "UpexNote"
else:
    # .../services/worker/transcription/paths.py -> raiz do projeto e 3 niveis acima.
    PROJECT_DIR = Path(__file__).resolve().parents[3]

STORAGE_DIR = PROJECT_DIR / "storage"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"

SETTINGS_PATH = Path(os.environ.get("APPDATA", str(Path.home()))) / "UpexNote" / "settings.json"

# Override pontual (comando `transcribe --dest`): vale so para este processo.
_dest_override = None


def set_dest_override(path):
    """Ativa o destino pontual desta execucao (ou desativa com None)."""
    global _dest_override
    _dest_override = Path(path) if path else None


def load_settings():
    """Le settings.json; devolve {} se nao existir ou estiver invalido."""
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_settings(settings):
    """Grava settings.json (cria a pasta se preciso)."""
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def effective_storage_dir():
    """Pasta padrao em vigor (a do utilizador, ou a de fabrica)."""
    custom = load_settings().get("storage_dir")
    return Path(custom) if custom else TRANSCRIPTS_DIR


def organize_by_day_engine():
    """True (defeito) = subpastas <dia>\\<motor> dentro da pasta padrao."""
    return bool(load_settings().get("organize_by_day_engine", True))


def stem_for(source_path):
    """Nome base seguro derivado do ficheiro de origem (sem espacos), para
    nomear outputs sem colisao entre transcricoes de ficheiros diferentes."""
    return Path(source_path).stem.replace(" ", "_")


def transcript_path(engine, source_path, kind):
    r"""
    Caminho de um transcript.

    - Com override pontual (--dest): direto na pasta escolhida, sem subpastas
      ("guardar em..." significa exatamente ali).
    - Sem override: pasta padrao em vigor; subpastas <dia>\<motor> apenas se
      a opcao "organizar por dia/motor" estiver ligada.
    - kind: "clean" (vista de leitura) ou "raw" (referencia imutavel).
    """
    today = date.today().isoformat()  # AAAA-MM-DD
    if _dest_override is not None:
        d = _dest_override
    elif organize_by_day_engine():
        d = effective_storage_dir() / today / engine
    else:
        d = effective_storage_dir()
    d.mkdir(parents=True, exist_ok=True)
    stem = stem_for(source_path)
    return d / f"{stem}__{today}__{engine}__{kind}.txt"
