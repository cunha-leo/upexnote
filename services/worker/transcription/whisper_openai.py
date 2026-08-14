"""
Motor OpenAI whisper-1 — alternativa economica/monolingue do UpexNote,
seguindo as recomendacoes oficiais:
https://developers.openai.com/cookbook/examples/whisper_prompting_guide
https://developers.openai.com/api/docs/guides/speech-to-text

- Usa "whisper-1" (nao "gpt-4o-transcribe"): bug conhecido de corte de
  transcricao em audios longos no gpt-4o-transcribe; whisper-1 nao tem esse
  problema e ainda suporta timestamps por segmento.
- Cortes de bloco escolhidos em pontos de silencio (nao a meio de frases).
- Silencios longos (>=2s) sao salvos ao modelo (evita alucinacao em loop),
  mas os timestamps finais sao convertidos de volta para o audio ORIGINAL
  via mapa (audio_chunks.iter_wav_chunks_skip_silence) - nao ficam desalinhados.
- Continuidade entre blocos via parametro "prompt" (ultimas ~200 palavras do
  bloco anterior). No 1o bloco, usa um prompt "estilo" (ficticio) a avisar que
  e uma reuniao PT com termos tecnicos em ingles - nao forca idioma (language
  fica None / deteção automatica), para nao "aportuguesar" o ingles genuino.
- temperature=0 (reduz alucinacoes/variabilidade).
- Deteta loops de repeticao/paragrafos repetidos (ver transcript_utils) mas
  NAO apaga o original: gera *_raw.txt (intacto) e *_clean.txt (marcado).
- LIMITACAO CONHECIDA: o idioma e detetado uma vez por bloco (~30s iniciais)
  e fica "trancado" para o resto do bloco - uma frase curta em ingles dentro
  de um bloco predominantemente PT pode ser mal-transcrita foneticamente
  como se fosse portugues. Blocos de 300s (5min) sao o ponto otimo empirico;
  reduzir o tamanho do bloco NAO corrige isto (piora a estabilidade de loop).

Uso:
    from transcription.credentials import get_key
    from transcription import whisper_openai
    result = whisper_openai.run("caminho/para/audio.mp4", get_key("OPENAI_API_KEY"))
"""
import io
import os
import sys
import time
from openai import OpenAI
from .audio_chunks import iter_wav_chunks_skip_silence
from .paths import transcript_path
from .transcript_utils import enforce_monotonic_segments, validate_segments, mark_repetition_loops

PRICE_PER_MINUTE = 0.006  # whisper-1, USD


def run(audio_path, api_key, log=print, chunk_seconds=300):
    """
    Transcreve audio_path com o whisper-1. Devolve um dict:
      {ok, raw_path, clean_path, clean_text, cost, duration_s, problems}
    log(msg) e chamado com linhas de progresso.
    chunk_seconds=300 (5 min) e o ponto otimo validado empiricamente.
    """
    client = OpenAI(api_key=api_key)

    all_segments = []  # (start, end, text) em tempo do audio ORIGINAL
    total_covered_compact = 0.0
    warnings = []
    prev_tail_prompt = ""
    detected_language = None

    start_time = time.time()
    chunks, to_original, original_duration = iter_wav_chunks_skip_silence(
        audio_path, chunk_seconds=chunk_seconds, sample_rate=8000
    )

    for i, (chunk_start, chunk_end, wav_bytes) in enumerate(chunks):
        chunk_duration = chunk_end - chunk_start
        log(f"Bloco {i}: {chunk_start:.1f}s -> {chunk_end:.1f}s ({chunk_duration:.1f}s)...")

        buf = io.BytesIO(wav_bytes)
        buf.name = f"chunk_{i}.wav"

        try:
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=buf,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
                temperature=0,
                prompt=prev_tail_prompt or "Reuniao de trabalho em portugues, com alguns trechos e termos tecnicos em ingles (ex: middleware, backlog, release, deploy).",
            )
        except Exception as e:
            log(f"  ERRO no bloco {i}: {e}")
            warnings.append(f"bloco {i}: excecao {e}")
            continue

        if detected_language is None:
            detected_language = getattr(result, "language", None)

        segments = list(getattr(result, "segments", None) or [])
        if not segments and (result.text or "").strip():
            segments = [type("S", (), {"start": 0, "end": chunk_duration, "text": result.text})()]

        if not segments:
            log(f"  AVISO: bloco {i} devolveu texto vazio")
            warnings.append(f"bloco {i}: texto vazio")
            continue

        chunk_text_parts = []
        last_seg_end = 0.0
        for seg in segments:
            seg_start_orig = to_original(chunk_start + seg.start)
            seg_end_orig = to_original(chunk_start + seg.end)
            seg_text = seg.text.strip()
            all_segments.append((seg_start_orig, seg_end_orig, seg_text))
            chunk_text_parts.append(seg_text)
            last_seg_end = seg.end

        coverage_ratio = last_seg_end / chunk_duration if chunk_duration > 0 else 1.0
        if coverage_ratio < 0.9:
            msg = f"bloco {i}: so cobriu {last_seg_end:.1f}s de {chunk_duration:.1f}s ({coverage_ratio:.0%}) - possivel corte"
            log(f"  AVISO: {msg}")
            warnings.append(msg)

        total_covered_compact += last_seg_end
        prev_tail_prompt = " ".join(" ".join(chunk_text_parts).split()[-200:])

    elapsed = time.time() - start_time

    all_segments, monotonic_corrections = enforce_monotonic_segments(all_segments)
    annotated, loop_events = mark_repetition_loops(all_segments)

    raw_path = transcript_path("whisper_openai", audio_path, "raw")
    raw_lines = [f"[{s:6.1f}s -> {e:6.1f}s]  {t}" for s, e, t, _ in annotated]
    raw_path.write_text("\n".join(raw_lines), encoding="utf-8")

    clean_path = transcript_path("whisper_openai", audio_path, "clean")
    clean_lines = []
    seen_loop_ids = set()
    for s, e, t, loop_id in annotated:
        if loop_id is not None:
            if loop_id in seen_loop_ids:
                continue
            seen_loop_ids.add(loop_id)
            ev = next(x for x in loop_events if x["id"] == loop_id)
            reason = ev.get("reason", f"repetido {ev['count']}x")
            clean_lines.append(f"[{ev['start']:6.1f}s -> {ev['end']:6.1f}s]  {ev['text']}  [POSSIVEL ALUCINACAO: {reason}, ver {raw_path.name}]")
        else:
            clean_lines.append(f"[{s:6.1f}s -> {e:6.1f}s]  {t}")
    clean_text = "\n".join(clean_lines)
    clean_path.write_text(clean_text, encoding="utf-8")

    minutes_processed = total_covered_compact / 60
    cost = minutes_processed * PRICE_PER_MINUTE

    log("-" * 70)
    log(f"Tempo total de processamento: {elapsed:.1f}s")
    log(f"Duracao original do audio: {original_duration:.1f}s")
    log(f"Custo estimado: ~${cost:.4f} (${PRICE_PER_MINUTE}/min, whisper-1)")
    if loop_events:
        log(f"Alucinacoes detetadas: {len(loop_events)}")
    if warnings:
        log(f"AVISOS: {len(warnings)}")

    ok, problems = validate_segments(all_segments, original_duration, loop_events=loop_events)
    log("VALIDACAO: OK" if ok else f"VALIDACAO: FALHOU ({len(problems)} problema(s))")
    log(f"Guardado em {raw_path} e {clean_path}")

    return {
        "ok": ok,
        "raw_path": raw_path,
        "clean_path": clean_path,
        "clean_text": clean_text,
        "cost": cost,
        "duration_s": original_duration,
        "language": detected_language,
        "problems": problems,
    }


if __name__ == "__main__":
    from .credentials import get_key
    _api_key = get_key("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not _api_key:
        raise SystemExit("Define a chave OPENAI_API_KEY (Credential Manager ou variavel de ambiente) primeiro")
    _audio_path = sys.argv[1] if len(sys.argv) > 1 else "reuniao_teste.wav"
    _chunk_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    _result = run(_audio_path, _api_key, chunk_seconds=_chunk_seconds)
    print(_result["clean_text"])
    if not _result["ok"]:
        sys.exit(1)
