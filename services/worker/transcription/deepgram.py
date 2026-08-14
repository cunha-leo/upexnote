"""
Motor Deepgram Nova-3 — candidato a baixa latencia/futuro modo ao vivo do
UpexNote, seguindo a documentacao oficial:
https://developers.deepgram.com/docs/multilingual-code-switching
https://developers.deepgram.com/reference/speech-to-text/listen-pre-recorded

- language=multi (obrigatorio para code-switching PT/EN, so suportado em
  nova-2, nova-3 e flux-general-multi).
- keyterm: reforca reconhecimento de nomes/termos especificos do dominio
  (parametro exclusivo do nova-3). Boas praticas oficiais: usar so PALAVRAS
  INDIVIDUAIS pouco comuns (nomes proprios, jargao), nunca frases nem
  numeros - https://developers.deepgram.com/docs/keyterm
- numerals=true: numeros por extenso -> digitos.
- paragraphs=true + utterances=true: estrutura melhor a saida com timestamps.
- diarize=true: rotula cada utterance com o numero do interlocutor.
- Corte em blocos de silencio (nao a meio de frases) so entra em jogo se o
  audio for mais longo que chunk_seconds (default 30 min).
- Nao e o motor principal (diarizacao/qualidade geral menos consistente que
  a AssemblyAI nos dois testes de 2026-07-12), mas fica disponivel como
  alternativa e candidato a modo ao vivo (streaming) no futuro.

Uso:
    from transcription.credentials import get_key
    from transcription import deepgram
    result = deepgram.run("caminho/para/audio.mp4", get_key("DEEPGRAM_API_KEY"))
"""
import os
import sys
import time
import requests
from .audio_chunks import iter_wav_chunks
from .paths import transcript_path
from .transcript_utils import enforce_monotonic_segments, validate_segments, mark_repetition_loops

PRICE_PER_MINUTE = 0.0077  # Nova-3 pay-as-you-go, USD/min

KEYTERMS = [
    "Leonardo", "Sérgio", "Mónica", "Carla", "Diego", "Feliciano",
    "Morato", "Andreia", "Ana", "TCS", "Apex", "voada", "XPTO",
]

URL = "https://api.deepgram.com/v1/listen"
BASE_PARAMS = [
    ("model", "nova-3"),
    ("language", "multi"),
    ("smart_format", "true"),
    ("punctuate", "true"),
    ("utterances", "true"),
    ("paragraphs", "true"),
    ("numerals", "true"),
    ("diarize", "true"),
] + [("keyterm", term) for term in KEYTERMS]


def run(audio_path, api_key, log=print, chunk_seconds=1800):
    """
    Transcreve audio_path com o Deepgram Nova-3. Devolve um dict:
      {ok, raw_path, clean_path, clean_text, cost, duration_s, problems}
    log(msg) e chamado com linhas de progresso.
    """
    headers = {
        "Authorization": f"Token {api_key}",
        "Content-Type": "audio/wav",
    }

    all_segments = []  # (start, end, text)
    total_covered = 0.0
    warnings = []
    detected_language = None

    start_time = time.time()
    for i, (chunk_start, chunk_end, wav_bytes) in enumerate(iter_wav_chunks(audio_path, chunk_seconds=chunk_seconds)):
        duration = chunk_end - chunk_start
        log(f"Bloco {i}: {chunk_start:.1f}s -> {chunk_end:.1f}s ({duration:.1f}s)...")

        try:
            resp = requests.post(URL, params=BASE_PARAMS, headers=headers, data=wav_bytes, timeout=600)
        except Exception as e:
            raise RuntimeError(f"Deepgram: falha de rede ao contactar a API ({e})")
        if not resp.ok:
            # Falha alto (ex.: 401 chave invalida) em vez de produzir output vazio.
            raise RuntimeError(f"Deepgram: ERRO {resp.status_code} da API - {resp.text[:300]}")
        result = resp.json()

        channel = result.get("results", {}).get("channels", [{}])[0]
        if detected_language is None:
            detected_language = channel.get("detected_language")
            # No modo multilingue nao ha um idioma unico ao nivel do canal;
            # best-effort: idioma dominante ao nivel da palavra, se existir.
            if not detected_language:
                words = (channel.get("alternatives", [{}])[0] or {}).get("words", []) or []
                langs = [w.get("language") for w in words if w.get("language")]
                if langs:
                    detected_language = max(set(langs), key=langs.count)

        utterances = result.get("results", {}).get("utterances", [])
        if not utterances:
            transcript = channel.get("alternatives", [{}])[0].get("transcript", "")
            if transcript.strip():
                utterances = [{"start": 0, "end": duration, "transcript": transcript}]

        if not utterances:
            log(f"  AVISO: bloco {i} devolveu texto vazio")
            warnings.append(f"bloco {i}: texto vazio")
            continue

        last_end = 0.0
        for utt in utterances:
            text = (utt.get("transcript") or "").strip()
            if not text:
                continue
            speaker = utt.get("speaker")
            label = f"[Speaker {speaker}] " if speaker is not None else ""
            all_segments.append((chunk_start + utt["start"], chunk_start + utt["end"], f"{label}{text}"))
            last_end = max(last_end, utt["end"])

        coverage_ratio = last_end / duration if duration > 0 else 1.0
        if coverage_ratio < 0.9:
            msg = f"bloco {i}: so cobriu {last_end:.1f}s de {duration:.1f}s ({coverage_ratio:.0%}) - possivel corte"
            log(f"  AVISO: {msg}")
            warnings.append(msg)

        total_covered += last_end

    elapsed = time.time() - start_time

    if not all_segments:
        # Nunca gravar ficheiros/linha vazios: falha alto com mensagem clara.
        raise RuntimeError(
            "Deepgram nao devolveu texto (0 segmentos). Verifica a chave DEEPGRAM_API_KEY "
            "e o ficheiro de audio."
        )

    original_duration = all_segments[-1][1] if all_segments else total_covered

    all_segments, monotonic_corrections = enforce_monotonic_segments(all_segments)
    annotated, loop_events = mark_repetition_loops(all_segments)

    raw_path = transcript_path("deepgram", audio_path, "raw")
    raw_lines = [f"[{s:6.1f}s -> {e:6.1f}s]  {t}" for s, e, t, _ in annotated]
    raw_path.write_text("\n".join(raw_lines), encoding="utf-8")

    clean_path = transcript_path("deepgram", audio_path, "clean")
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

    minutes_processed = total_covered / 60
    cost = minutes_processed * PRICE_PER_MINUTE

    log("-" * 70)
    log(f"Tempo total de processamento: {elapsed:.1f}s")
    log(f"Duracao total coberta: {total_covered:.1f}s (~{minutes_processed:.1f} min)")
    log(f"Custo estimado: ~${cost:.4f} (${PRICE_PER_MINUTE}/min, nova-3)")
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
    _api_key = get_key("DEEPGRAM_API_KEY") or os.environ.get("DEEPGRAM_API_KEY")
    if not _api_key:
        raise SystemExit("Define a chave DEEPGRAM_API_KEY (Credential Manager ou variavel de ambiente) primeiro")
    _audio_path = sys.argv[1] if len(sys.argv) > 1 else "reuniao_teste.wav"
    _chunk_seconds = int(sys.argv[2]) if len(sys.argv) > 2 else 1800
    _result = run(_audio_path, _api_key, chunk_seconds=_chunk_seconds)
    print(_result["clean_text"])
    if not _result["ok"]:
        sys.exit(1)
