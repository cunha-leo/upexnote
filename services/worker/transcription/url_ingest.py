"""Local-first YouTube URL ingestion. No shell, cookies, credentials or remote proxy."""
from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

_ALLOWED_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be", "www.youtu.be"}
_LANG_RE = re.compile(r"^[A-Za-z0-9_-]{1,24}$")
_TAG_RE = re.compile(r"<[^>]+>")
_CUE_RE = re.compile(r"^(?:\d{2}:)?\d{2}:\d{2}[.,]\d{3}\s*-->")
_VIDEO_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class IngestError(ValueError):
    pass


def validate_url(value: str) -> str:
    value = (value or "").strip()
    if len(value) > 2048 or any(ord(c) < 32 for c in value):
        raise IngestError("URL inválida ou demasiado longa.")
    parsed = urlsplit(value)
    if parsed.scheme not in ("http", "https") or parsed.username or parsed.password or parsed.port:
        raise IngestError("Utilize um link HTTP(S) normal do YouTube.")
    host = (parsed.hostname or "").lower().rstrip(".")
    if host not in _ALLOWED_HOSTS:
        raise IngestError("Por enquanto, a importação aceita apenas URLs do YouTube.")
    if host.endswith("youtu.be"):
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    elif parsed.path.startswith(("/live/", "/shorts/", "/embed/")):
        video_id = parsed.path.strip("/").split("/")[1]
    else:
        raise IngestError("Cole uma URL de vídeo, live ou Shorts do YouTube.")
    if not _VIDEO_RE.fullmatch(video_id):
        raise IngestError("Não foi possível reconhecer o identificador do vídeo.")
    # Canonicalize to prevent playlist, redirects and unrelated query parameters.
    return f"https://www.youtube.com/watch?v={video_id}"


def _executable() -> str:
    # Na distribuição, o yt-dlp acompanha o sidecar; na instalação de dev
    # pode ser encontrado no PATH. Nenhum comando é executado via shell.
    if getattr(sys, "frozen", False):
        bundled = Path(sys.executable).resolve().parent / "yt-dlp.exe"
        if bundled.is_file():
            return str(bundled)
    result = shutil.which("yt-dlp")
    if not result:
        raise IngestError("yt-dlp indisponível. Reinstale o UpexNote ou instale yt-dlp no computador.")
    return result


def _run(arguments: list[str], *, timeout: int = 90) -> str:
    command = [_executable(), "--ignore-config", "--no-playlist", "--no-warnings",
               "--no-progress", "--socket-timeout", "12", "--retries", "1"] + arguments
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout,
                              shell=False, stdin=subprocess.DEVNULL)
    except subprocess.TimeoutExpired as exc:
        raise IngestError("A análise demorou demasiado. Tente novamente.") from exc
    if proc.returncode:
        # Do not leak potentially sensitive error text or local paths to the UI.
        error = (proc.stderr or "").lower()
        if "unavailable" in error or "private" in error or "login" in error:
            raise IngestError("Vídeo indisponível ou com acesso restrito. Experimente outro link.")
        raise IngestError("Não foi possível obter o conteúdo deste link. Tente outro vídeo.")
    return proc.stdout


def analyze(url: str) -> dict:
    canonical = validate_url(url)
    payload = _run(["--dump-single-json", "--skip-download", canonical])
    try:
        info = json.loads(payload.strip().splitlines()[-1])
    except (ValueError, IndexError) as exc:
        raise IngestError("O YouTube não devolveu informações válidas para este vídeo.") from exc
    def tracks(field):
        tracks_found = info.get(field) or {}
        return sorted(k for k, v in tracks_found.items() if _LANG_RE.fullmatch(k) and k != "live_chat" and v)
    manual = tracks("subtitles")
    automatic = tracks("automatic_captions")
    duration = info.get("duration")
    return {"type": "url_analysis", "ok": True, "url": canonical,
            "id": str(info.get("id") or ""), "title": str(info.get("title") or "Vídeo do YouTube")[:240],
            "duration_s": int(duration) if isinstance(duration, (int, float)) and duration >= 0 else None,
            "channel": str(info.get("channel") or "")[:140],
            "manual_languages": manual, "automatic_languages": automatic,
            "has_captions": bool(manual or automatic)}


def _safe_filename(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._-]+", "_", value)[:70].strip("._")
    return value or "youtube"


def fetch_audio(url: str, progress=None) -> tuple[Path, Path, dict]:
    if not shutil.which("ffmpeg"):
        raise IngestError("FFmpeg não encontrado no computador. Instale FFmpeg para extrair áudio do YouTube.")
    info = analyze(url)
    directory = Path(tempfile.mkdtemp(prefix="upexnote-url-"))
    try:
        if progress:
            progress("A obter somente o áudio do YouTube...")
        # Keep best source codec; FFmpeg converts it for the existing engines.
        target = str(directory / (_safe_filename(info["title"]) + "_%(id)s.%(ext)s"))
        _run(["-x", "--audio-format", "mp3", "--audio-quality", "0",
              "-o", target, info["url"]], timeout=3600)
        candidates = list(directory.glob("*.mp3"))
        if not candidates:
            raise IngestError("O vídeo foi analisado, mas não foi possível preparar o áudio.")
        return candidates[0], directory, info
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise


def _vtt_text(raw: str) -> str:
    """Extrai só texto visível do VTT; o RAW preserva os tempos originais."""
    blocks = re.split(r"\n\s*\n", raw.replace("\r\n", "\n"))
    lines: list[str] = []
    for block in blocks:
        pieces = block.splitlines()
        if not any(_CUE_RE.match(p.strip()) for p in pieces):
            continue
        for part in pieces:
            s = part.strip()
            if not s or _CUE_RE.match(s) or s.isdigit():
                continue
            # Extrair texto visível mantendo ordem, pausas e repetições
            # exatamente como aparecem nas legendas. Sem deduplicação,
            # heurísticas de falantes ou timestamps inventados no CLEAN.
            s = html.unescape(_TAG_RE.sub("", s)).strip()
            if s:
                lines.append(s)
    return "\n".join(lines).strip()


def fetch_captions(url: str, lang: str, kind: str) -> tuple[str, str, dict]:
    info = analyze(url)
    if not _LANG_RE.fullmatch(lang or "") or kind not in ("manual", "automatic"):
        raise IngestError("Idioma ou origem da legenda inválidos.")
    allowed = info["manual_languages"] if kind == "manual" else info["automatic_languages"]
    if lang not in allowed:
        raise IngestError("Essa legenda já não está disponível. Analise o link novamente.")
    directory = Path(tempfile.mkdtemp(prefix="upexnote-sub-"))
    try:
        args = ["--skip-download", "--sub-langs", lang, "--sub-format", "vtt",
                "--write-subs" if kind == "manual" else "--write-auto-subs",
                "-o", str(directory / "%(id)s.%(ext)s"), info["url"]]
        _run(args, timeout=150)
        matches = list(directory.glob("*.vtt"))
        if not matches:
            raise IngestError("Não foi possível recuperar a legenda selecionada.")
        raw = matches[0].read_text(encoding="utf-8-sig")
        clean = _vtt_text(raw)
        if not clean:
            raise IngestError("A legenda não contém texto utilizável.")
        return raw, clean, info
    finally:
        shutil.rmtree(directory, ignore_errors=True)
