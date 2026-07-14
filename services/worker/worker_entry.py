"""
Ponto de entrada para o PyInstaller (sidecar da app desktop).

O PyInstaller precisa de um script (nao de um pacote com `-m`), por isso
este ficheiro so delega na CLI real. O executavel resultante aceita os
mesmos argumentos que `python -m transcription.cli`:

    upexnote-worker.exe engines
    upexnote-worker.exe transcribe --engine assemblyai --file "..."

Build: ver build_worker.ps1 nesta pasta.
"""
import sys

from transcription.cli import main

if __name__ == "__main__":
    sys.exit(main())
