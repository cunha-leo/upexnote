r"""
Caminhos partilhados - garante que todos os motores escrevem os resultados
sempre no mesmo sitio (storage\transcripts\<motor>\), independentemente de
onde o worker for invocado.

O video/audio de origem NUNCA e copiado para dentro do projeto - o
utilizador escolhe um caminho qualquer do Windows e so esse caminho e lido.
"""
import sys
from pathlib import Path

if getattr(sys, "frozen", False):
    # Executavel empacotado: usa a pasta onde o executavel esta como raiz.
    PROJECT_DIR = Path(sys.executable).resolve().parent
else:
    # .../services/worker/transcription/paths.py -> raiz do projeto e 3 niveis acima.
    PROJECT_DIR = Path(__file__).resolve().parents[3]

STORAGE_DIR = PROJECT_DIR / "storage"
TRANSCRIPTS_DIR = STORAGE_DIR / "transcripts"


def output_path(engine, filename):
    r"""Devolve o caminho para storage\transcripts\<engine>\<filename>, criando a pasta se preciso."""
    d = TRANSCRIPTS_DIR / engine
    d.mkdir(parents=True, exist_ok=True)
    return d / filename


def stem_for(source_path):
    """Nome base seguro derivado do ficheiro de origem (sem espacos), para
    nomear outputs sem colisao entre transcricoes de ficheiros diferentes."""
    return Path(source_path).stem.replace(" ", "_")
