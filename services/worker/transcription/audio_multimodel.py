"""
Multimodelos de áudio com entrada suportada e resultados por motor.
OpenAI GPT-Transcribe, Gemini áudio multimodal e xAI Speech-to-Text.
Nenhum resultado vazio é persistido. WAV dividido por blocos, com
timestamps precisos apenas onde o provedor os fornece.
"""
import base64
import io
import time
import requests

from .audio_chunks import iter_wav_chunks
from .paths import transcript_path
from .transcript_utils import enforce_monotonic_segments, mark_repetition_loops, validate_segments


def _provider_error(name, response):
    status = response.status_code
    if status == 401:
        reason = "chave rejeitada"
    elif status == 403:
        reason = "acesso ao modelo bloqueado"
    elif status == 429:
        reason = "limite de uso, créditos ou quota"
    else:
        reason = "erro de chamada ao provedor"
    raise RuntimeError(f"{name}: HTTP {status} ({reason}); nenhum resultado vazio foi guardado")


def _as_segments(text, chunk_start, chunk_end, words=None):
    """Retorna segmentos com tempos exatos quando a API dá palavras.
    Caso contrário, fornece apenas os limites aproximados do BLOCO,
    sem fingir timestamps por palavra/frase.
    """
    if not words:
        return [(chunk_start, chunk_end, text.strip())] if text.strip() else []
    groups = []
    batch = []
    for word in words:
        token = str(word.get("text") or "").strip()
        if not token:
            continue
        batch.append(word)
        if len(batch) >= 22 or token.endswith((".", "?", "!")):
            groups.append(batch)
            batch = []
    if batch:
        groups.append(batch)
    segments = []
    for group in groups:
        line = " ".join(str(w.get("text") or "").strip() for w in group).strip()
        begin = chunk_start + float(group[0].get("start") or 0.0)
        end = chunk_start + float(group[-1].get("end") or (chunk_end-chunk_start))
        if line:
            segments.append((max(chunk_start,begin), min(chunk_end,max(begin,end)),line))
    return segments


def _call_openai(wav, key):
    r = requests.post(
        "https://api.openai.com/v1/audio/transcriptions",
        headers={"Authorization":f"Bearer {key}"},
        data={"model":"gpt-transcribe"},
        files={"file":("segment.wav",io.BytesIO(wav),"audio/wav")},
        timeout=180,
    )
    if not r.ok:
        _provider_error("OpenAI gpt-transcribe",r)
    data=r.json()
    return data.get("text") or "", None, (data.get("languages") or []), data.get("usage")


def _call_gemini(wav,key):
    # BLOCO 120 s: mesmo em WAV grande, o JSON fica abaixo do limite inline.
    payload = {
      "contents":[{"parts":[
        {"text":"Transcreva literalmente todas as falas deste áudio. Preserve o idioma de cada frase (português, inglês, espanhol ou outros). Não resuma, não traduza, não complete silêncios e não acrescente comentários. Retorne somente o texto falado."},
        {"inlineData":{"mimeType":"audio/wav","data":base64.b64encode(wav).decode("ascii")}},
      ]}],
      "generationConfig":{"maxOutputTokens":5000},
    }
    r=requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent",
        headers={"x-goog-api-key":key,"content-type":"application/json"},
        json=payload,timeout=180)
    if not r.ok:
        _provider_error("Gemini audio",r)
    data=r.json()
    texts=[p.get("text") or "" for c in data.get("candidates",[]) for p in c.get("content",{}).get("parts",[]) if p.get("text")]
    return "\n".join(texts).strip(),None,[],data.get("usageMetadata")


def _call_xai(wav,key):
    # format=true exige language. Para detectar alternância de idiomas,
    # format=false é a escolha apropriada (documentação xAI).
    r=requests.post(
       "https://api.x.ai/v1/stt",
       headers={"Authorization":f"Bearer {key}"},
       data=[("model","grok-voice-transcribe-2.0"),("format","false")],
       files={"file":("segment.wav",io.BytesIO(wav),"audio/wav")},
       timeout=180)
    if not r.ok:
        _provider_error("xAI Grok Voice Transcribe",r)
    d=r.json()
    return d.get("text") or "",d.get("words"),[],None


CALLS={"gpt_transcribe":_call_openai,"gemini_audio":_call_gemini,"grok_voice_stt":_call_xai}


def run(audio_path,api_key,log=print,*,engine_id):
    if engine_id not in CALLS:
        raise ValueError("Engine de áudio multimodal desconhecido")
    started=time.time()
    segments=[]
    detected_language=None
    usage=[]
    for index,(chunk_start,chunk_end,wav_bytes) in enumerate(iter_wav_chunks(audio_path,chunk_seconds=120)):
        log(f"Bloco {index}: {chunk_start:.1f}s–{chunk_end:.1f}s ({engine_id})")
        try:
            text,words,langs,item_usage=CALLS[engine_id](wav_bytes,api_key)
        except requests.RequestException as exc:
            raise RuntimeError(f"{engine_id}: falha de rede ({type(exc).__name__}); nenhum resultado vazio foi guardado") from exc
        if not text.strip():
            raise RuntimeError(f"{engine_id}: bloco {index} sem transcrição; não será salvo como sucesso")
        segments.extend(_as_segments(text,chunk_start,chunk_end,words))
        if item_usage:
            usage.append(item_usage)
        if not detected_language and langs:
            first=langs[0]
            detected_language=first.get("code") if isinstance(first,dict) else str(first)
    if not segments:
        raise RuntimeError(f"{engine_id}: nenhum segmento produzido")
    final_duration=max(end for _,end,_ in segments)
    segments,_=enforce_monotonic_segments(segments)
    annotated,loops=mark_repetition_loops(segments)
    # Gera os arquivos em memória primeiro e apenas os grava após todas as chamadas terminarem.
    raw_path=transcript_path(engine_id,audio_path,"raw")
    clean_path=transcript_path(engine_id,audio_path,"clean")
    raw_lines=[f"[{s:6.1f}s -> {e:6.1f}s]  {txt}" for s,e,txt,_ in annotated]
    seen=set()
    clean_lines=[]
    for s,e,txt,loop_id in annotated:
        if loop_id is None:
            clean_lines.append(f"[{s:6.1f}s -> {e:6.1f}s]  {txt}")
        elif loop_id not in seen:
            seen.add(loop_id)
            clean_lines.append(f"[{s:6.1f}s -> {e:6.1f}s]  {txt}  [POSSÍVEL REPETIÇÃO/ALUCINAÇÃO]")
    ok,problems=validate_segments(segments,final_duration,loop_events=loops)
    if not ok:
        log(f"AVISO: {len(problems)} observações de validação")
    raw_path.write_text("\n".join(raw_lines),encoding="utf-8")
    clean_text="\n".join(clean_lines)
    clean_path.write_text(clean_text,encoding="utf-8")
    log(f"Tempo: {time.time()-started:.1f}s; custo monetário: não apurado, conferir faturamento da API")
    if engine_id!="grok_voice_stt":
        log("Timestamps apenas aproximados por bloco; não são timestamps por palavra")
    log(f"Guardado em {raw_path} e {clean_path}")
    return {"ok":ok,"raw_path":raw_path,"clean_path":clean_path,"clean_text":clean_text,
            "cost":None,"duration_s":final_duration,"language":detected_language,
            "problems":problems,"usage":usage,"timing_precision":"word" if engine_id=="grok_voice_stt" else "chunk"}
