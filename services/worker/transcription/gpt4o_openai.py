"""
Motor OpenAI gpt-4o-transcribe — NAO usar como motor principal. Mantido no
codebase apenas como referencia/possivel revisor de trechos curtos no
futuro (ver docs/PROJECT_CONTEXT.md secao 5).

Disqualificado em 2026-07-11 apos 3 rondas de afinacao (copia ingenua da
config do whisper-1, depois temperature=0.2 + prompt diretivo, depois
chunks de 150s): continuou a produzir loops de alucinacao graves (170x,
486x, 404x repeticoes em testes), perdendo mais de metade do audio em
texto repetido nalguns casos. Ver documentacao oficial e threads da
comunidade citadas abaixo para o raciocinio completo por tras de cada
tentativa de correcao.

https://developers.openai.com/api/docs/guides/speech-to-text
https://community.openai.com/t/gpt-4o-transcribe-why-does-the-final-output-sometimes-exactly-replicate-the-configured-prompt/1226877
https://community.openai.com/t/persistent-truncation-issues-with-gpt-4o-transcribe-has-anyone-fully-solved-this/1266942

DIFERENCA IMPORTANTE face ao whisper-1: gpt-4o-transcribe NAO suporta
timestamp_granularities nem response_format "verbose_json" - so aceita
"json"/"text", sem timestamps internos. Os timestamps aqui sao aproximados
por comprimento de frase (transcript_utils.split_into_pseudo_segments).

Uso:
    from transcription.credentials import get_key
    from transcription import gpt4o_openai
    result = gpt4o_openai.run("caminho/para/audio.mp4", get_key("OPENAI_API_KEY"))
"""
import io
import os
import sys
import time
from openai import OpenAI
from .audio_chunks import iter_wav_chunks_skip_silence
from .paths import output_path, stem_for
from .transcript_utils import (
    enforce_monotonic_segments, validate_segments, mark_repetition_loops,
    split_into_pseudo_segments,
)

PRICE_PER_MINUTE = 0.006  # gpt-4o-transcribe, USD (2026)

DIRECTIVE_PROMPT = (
    "Transcreve exatamente o que e dito nesta reuniao de trabalho em portugues, "
    "com termos tecnicos e frases pontuais em ingles. Nao omitas, nao resumas e "
    "nao repitas nenhuma frase desnecessariamente. Se um trecho estiver pouco "
    "claro ou em silencio, nao inventes nem repitas a ultima frase - passa "
    "adiante."
)


def run(audio_path, api_key, log=print, chunk_seconds=150):
    """
    Transcreve audio_path com o gpt-4o-transcribe. Devolve um dict:
      {ok, raw_path, clean_path, clean_text, cost, duration_s, problems}
    chunk_seconds=150: menor que os 300s do whisper-1 porque blocos maiores
    alucinaram mais mesmo com temperature=0.2 + prompt diretivo.
    """
    client = OpenAI(api_key=api_key)

    all_segments = []  # (start, end, text) aproximados, em tempo do audio ORIGINAL
    total_covered_compact = 0.0
    warnings = []

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
                model="gpt-4o-transcribe",
                file=buf,
                response_format="json",
                temperature=0.2,
                prompt=DIRECTIVE_PROMPT,
            )
        except Exception as e:
            log(f"  ERRO no bloco {i}: {e}")
            warnings.append(f"bloco {i}: excecao {e}")
            continue

        chunk_text = (result.text or "").strip()
        if not chunk_text:
            log(f"  AVISO: bloco {i} devolveu texto vazio")
            warnings.append(f"bloco {i}: texto vazio")
            continue

        pseudo_segments = split_into_pseudo_segments(chunk_text, chunk_start, chunk_end)
        for seg_start, seg_end, seg_text in pseudo_segments:
            all_segments.append((to_original(seg_start), to_original(seg_end), seg_text))

        total_covered_compact += chunk_duration

    elapsed = time.time() - start_time

    all_segments, monotonic_corrections = enforce_monotonic_segments(all_segments)
    annotated, loop_events = mark_repetition_loops(all_segments)

    stem = stem_for(audio_path)
    raw_path = output_path("openai_gpt4o", f"{stem}__gpt4o_raw.txt")
    raw_lines = [f"[{s:6.1f}s -> {e:6.1f}s]  {t}" for s, e, t, _ in annotated]
    raw_path.write_text("\n".join(raw_lines), encoding="utf-8")

    clean_path = output_path("openai_gpt4o", f"{stem}__gpt4o_clean.txt")
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
    log(f"Custo estimado: ~${cost:.4f} (${PRICE_PER_MINUTE}/min, gpt-4o-transcribe)")
    log("NOTA: timestamps sao APROXIMADOS (gpt-4o-transcribe nao devolve timestamps internos ao bloco).")
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
        "problems": problems,
    }


if __name__ == "__main__":
    from .credentials import get_key
    _api_key = get_key("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not _api_key:
        raise SystemExit("Define a chave OPENAI_API_KEY (Credential Manager ou variavel de ambiente) primeiro")
    _audio_path = sys.argv[1] if len(sys.argv) > 1 else "reuniao_teste.wav"
    _chunk_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 150
    _result = run(_audio_path, _api_key, chunk_seconds=_chunk_seconds)
    print(_result["clean_text"])
    if not _result["ok"]:
        sys.exit(1)
