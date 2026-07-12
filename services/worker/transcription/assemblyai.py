"""
Motor AssemblyAI Universal-3.5 Pro — motor principal do UpexNote, seguindo a
documentacao oficial:
https://www.assemblyai.com/docs/pre-recorded-audio/code-switching
https://www.assemblyai.com/docs/getting-started/transcribe-an-audio-file
https://www.assemblyai.com/pricing

NOTA: "universal-3-pro" foi descontinuado - o nome atual do modelo e
"universal-3-5-pro" (confirmado via mensagem de erro 400 da propria API).

- speech_models=["universal-3-5-pro", "universal-2"]: Universal-3.5 Pro trata
  18 idiomas nativamente (incl. portugues e ingles) com code-switching
  automatico (segue o falante quando muda de idioma a meio da frase, sem
  precisar de nenhum parametro extra); Universal-2 fica como fallback para
  os restantes idiomas.
- language_detection=True + speaker_labels=True (diarizacao).
- prompt: descricao curta em frases (contexto). keyterms_prompt: lista de
  termos exatos (nomes, jargao) - ate 1000 termos, nao misturar com o prompt.
- Ficheiro inteiro num UNICO pedido (limite documentado: ate 10h, ate 5GB por
  pedido) - ao contrario do whisper-1/gpt-4o-transcribe, aqui NAO precisamos
  do nosso troceamento manual em blocos nem do mapa de timestamps.
- Preco: Universal-3.5 Pro = $0.21/hora ($0.0035/min).

Validado em 2026-07-12 contra duas gravacoes reais estruturalmente
diferentes (reuniao com dispositivo de sala PT-PT/PT-BR/EN e reuniao Teams
PT-only com microfones individuais) — venceu os dois testes: zero loops de
alucinacao, code-switching correto, melhor custo observado.

Uso:
    from transcription.credentials import get_key
    from transcription import assemblyai
    result = assemblyai.run("caminho/para/audio.mp4", get_key("ASSEMBLYAI_API_KEY"))
"""
import os
import sys
import time
import requests
from .paths import output_path, stem_for
from .transcript_utils import enforce_monotonic_segments, validate_segments, mark_repetition_loops

PRICE_PER_HOUR = 0.21  # Universal-3.5 Pro, USD (2026)
BASE_URL = "https://api.assemblyai.com"

# prompt = descricao curta em frases, keyterms_prompt = lista de termos exatos
# (a doc oficial pede para nao misturar os dois - "keep prompt to one short
# block of text... for lists of exact terms use keyterms_prompt instead")
PROMPT = (
    "Reuniao de trabalho em portugues (PT-PT e PT-BR), com trechos e termos "
    "tecnicos em ingles pelo meio da mesma conversa (code-switching)."
)
KEYTERMS = [
    "Leonardo", "Sergio", "Monica", "Carla", "Diego", "Feliciano", "Morato",
    "Andreia", "Ana", "demanda", "voada", "XPTO", "TCS", "Apex", "IB", "on hold",
]


def run(audio_path, api_key, log=print):
    """
    Transcreve audio_path com a AssemblyAI. Devolve um dict:
      {ok, raw_path, clean_path, clean_text, cost, duration_s, language, problems}
    log(msg) e chamado com linhas de progresso.
    """
    headers = {"authorization": api_key}

    log(f"A carregar {audio_path}...")
    start_time = time.time()
    with open(audio_path, "rb") as f:
        upload_resp = requests.post(f"{BASE_URL}/v2/upload", headers=headers, data=f)
    if not upload_resp.ok:
        raise RuntimeError(f"ERRO {upload_resp.status_code} da API AssemblyAI (upload): {upload_resp.text}")
    audio_url = upload_resp.json()["upload_url"]
    log("Upload concluido. A submeter pedido de transcricao...")

    submit_resp = requests.post(
        f"{BASE_URL}/v2/transcript",
        headers=headers,
        json={
            "audio_url": audio_url,
            "speech_models": ["universal-3-5-pro", "universal-2"],
            "language_detection": True,
            "speaker_labels": True,
            "prompt": PROMPT,
            "keyterms_prompt": KEYTERMS,
        },
    )
    if not submit_resp.ok:
        raise RuntimeError(f"ERRO {submit_resp.status_code} da API AssemblyAI: {submit_resp.text}")
    transcript_id = submit_resp.json()["id"]
    log(f"Pedido submetido (id={transcript_id}). A aguardar conclusao...")

    polling_url = f"{BASE_URL}/v2/transcript/{transcript_id}"
    poll_start = time.time()
    timeout_seconds = 1800
    while True:
        poll_resp = requests.get(polling_url, headers=headers)
        poll_resp.raise_for_status()
        transcript = poll_resp.json()
        status = transcript["status"]
        if status == "completed":
            break
        if status == "error":
            raise RuntimeError(f"Transcricao falhou: {transcript.get('error')}")
        if time.time() - poll_start > timeout_seconds:
            raise RuntimeError(f"Timeout ({timeout_seconds}s) a aguardar conclusao (ultimo estado: {status})")
        log(f"  ... estado: {status}")
        time.sleep(5)

    elapsed = time.time() - start_time

    utterances = transcript.get("utterances") or []
    all_segments = []
    if utterances:
        for utt in utterances:
            speaker = utt.get("speaker")
            text = (utt.get("text") or "").strip()
            if not text:
                continue
            start_s = utt["start"] / 1000.0
            end_s = utt["end"] / 1000.0
            label = f"[Speaker {speaker}] " if speaker is not None else ""
            all_segments.append((start_s, end_s, f"{label}{text}"))
    else:
        words = transcript.get("words") or []
        if words:
            cur_start, cur_end, buf = None, None, []
            for w in words:
                if cur_start is None:
                    cur_start = w["start"] / 1000.0
                cur_end = w["end"] / 1000.0
                buf.append(w["text"])
                if w["text"].endswith((".", "!", "?")):
                    all_segments.append((cur_start, cur_end, " ".join(buf)))
                    cur_start, buf = None, []
            if buf:
                all_segments.append((cur_start, cur_end, " ".join(buf)))
        elif (transcript.get("text") or "").strip():
            all_segments.append((0.0, transcript.get("audio_duration", 0), transcript["text"].strip()))

    original_duration = transcript.get("audio_duration") or (all_segments[-1][1] if all_segments else 0)

    all_segments, monotonic_corrections = enforce_monotonic_segments(all_segments)
    annotated, loop_events = mark_repetition_loops(all_segments)

    stem = stem_for(audio_path)
    raw_path = output_path("assemblyai", f"{stem}__raw.txt")
    raw_lines = [f"[{s:6.1f}s -> {e:6.1f}s]  {t}" for s, e, t, _ in annotated]
    raw_path.write_text("\n".join(raw_lines), encoding="utf-8")

    clean_path = output_path("assemblyai", f"{stem}__clean.txt")
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

    hours_processed = original_duration / 3600
    cost = hours_processed * PRICE_PER_HOUR

    log("-" * 70)
    log(f"Tempo total de processamento: {elapsed:.1f}s")
    log(f"Duracao do audio: {original_duration:.1f}s (~{original_duration/60:.1f} min)")
    log(f"Custo estimado: ~${cost:.4f} (${PRICE_PER_HOUR}/hora, universal-3.5-pro)")
    log(f"Idioma(s) detetado(s): {transcript.get('language_code')}")
    if loop_events:
        log(f"Alucinacoes detetadas: {len(loop_events)}")

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
        "language": transcript.get("language_code"),
        "problems": problems,
    }


if __name__ == "__main__":
    from .credentials import get_key
    _api_key = get_key("ASSEMBLYAI_API_KEY") or os.environ.get("ASSEMBLYAI_API_KEY")
    if not _api_key:
        raise SystemExit("Define a chave ASSEMBLYAI_API_KEY (Credential Manager ou variavel de ambiente) primeiro")
    _audio_path = sys.argv[1] if len(sys.argv) > 1 else "reuniao_teste.wav"
    _result = run(_audio_path, _api_key)
    print(_result["clean_text"])
    if not _result["ok"]:
        sys.exit(1)
