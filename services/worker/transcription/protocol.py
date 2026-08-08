"""Primitivas do protocolo NDJSON entre o worker e os clientes."""

from __future__ import annotations

import json


def emit(stream, event):
    """Escreve um evento JSON sem depender do code page da consola.

    O executável PyInstaller no Windows pode herdar uma stream ``charmap``.
    Escapes ASCII mantêm o fio compatível com qualquer code page; o parser
    JSON do cliente reconstrói os valores Unicode originais sem perda.
    """
    stream.write(json.dumps(event, ensure_ascii=True) + "\n")
    stream.flush()
