r"""
Caminhos partilhados - garante que todos os motores escrevem os resultados
sempre no mesmo sitio (storage\transcripts\<motor>\), independentemente de
onde o worker for invocado.

O video/audio de origem NUNCA e copiado para dentro do projeto - o
utilizador escolhe um caminho qualquer do Windows e so esse caminho e lido.
"""
import sys
from datetime import date
from pathlib import Path

if getattr(sys, "frozen", False):
    # Executavel empacotado (sidecar): os transcripts vao para uma pasta
    # estavel e visivel do utilizador — Documentos\UpexNote — que sobrevive
    # a reinstalacoes/atualizacoes da app (decisao 2026-07-13; a pasta do
    # exe seria apagada junto com a app e Program Files nem e gravavel).
    PROJECT_DIR = Path.home() / "Documents" / "UpexNote"
else:
    # .../services/worker/transcription/paths.py -> raiz do projeto e 3 niveis acima.
    PROJECT_DIR = Path(__file__).resolve().parents[3]

STORAGE_DIR = PROJECT_DIR / "storage"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"


def stem_for(source_path):
    """Nome base seguro derivado do ficheiro de origem (sem espacos), para
    nomear outputs sem colisao entre transcricoes de ficheiros diferentes."""
    return Path(source_path).stem.replace(" ", "_")


def transcript_path(engine, source_path, kind):
    r"""
    Caminho de um transcript, arrumado por DIA e depois por MOTOR:
        storage\transcripts\<AAAA-MM-DD>\<motor>\<origem>__<data>__<motor>__<kind>.txt

    - Pasta por dia (topo) e por motor (dentro) - facil de encontrar pelo dia,
      motores nunca se misturam.
    - O nome do ficheiro carrega origem + data + motor + tipo, para se
      identificar sozinho mesmo fora da pasta.
    - kind: "clean" (vista de leitura) ou "raw" (referencia imutavel).
    O texto e minusculo (~20 KB/transcript), por isso isto e so organizacao,
    nao ha preocupacao de espaco.
    """
    today = date.today().isoformat()  # AAAA-MM-DD
    d = TRANSCRIPTS_DIR / today / engine
    d.mkdir(parents=True, exist_ok=True)
    stem = stem_for(source_path)
    return d / f"{stem}__{today}__{engine}__{kind}.txt"
