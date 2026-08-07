"""
Motores de FORMATACAO — etapa distinta da transcricao (ADF-01). Aqui a
entrada ja e o transcript CLEAN (texto), nunca audio; a saida e um
documento estruturado em blocos, nao um novo transcript.

Jornada (docs/FEATURE_VALIDATION_AND_ROADMAP.md, ADF-01):
  transcript clean validado
    -> validacao de integridade raw<->clean (etapa separada, fora deste modulo)
    -> este modulo: clean -> documento estruturado (JSON de blocos)
    -> workspace de edicao/estudo (ADF-02, fora deste modulo)

Modelo de saida (contrato fechado em 05/08/2026 e 06/08/2026):
  O usuario nunca ve Markdown cru nem JSON cru — a UI e um editor rico
  renderizado a partir de um modelo estruturado. Este modulo produz esse
  modelo estruturado, um dict:

    {
      "title": str,
      "objective": str | None,          # objetivo em uma frase
      "blocks": [
        {
          "id": str,                    # ID de bloco ESTAVEL (ancora para
                                         # comentarios/referencias futuras;
                                         # nunca reordena/reaproveita nem
                                         # muda com uma nova geracao)
          "type": str,                  # ver BLOCK_TYPES abaixo
          "heading": str | None,
          "content": str | list | dict, # forma depende do "type"
          "speaker": str | None,        # quando aplicavel/identificavel
          "timestamp": str | None,      # quando disponivel no clean
        },
        ...
      ],
      "jargon": [{"term": str, "meaning": str}, ...],
      "engine": str,        # id do motor (ex.: "deepseek")
      "model": str,         # nome exato do modelo usado
      "profile": str,       # perfil de transformacao usado
      "generated_at": str,  # ISO-8601 UTC
    }

  BLOCK_TYPES cobre a lista de "conteudo que a transformacao deve poder
  estruturar" do roadmap: "section", "objective", "requirement", "decision",
  "action", "risk", "question", "topic", "technical_context", "excerpt".
  Um motor pode nao usar todos os tipos numa geracao — a lista descreve o
  vocabulario disponivel, nao uma obrigacao de preenchimento.

Perfis de transformacao (extensivel, nao fechado):
  "detalhado"       - versao completa, cobre tudo que da para estruturar.
  "resumo_tecnico"  - so o essencial: objetivo, decisoes, acoes, riscos.
  "estudo"          - pensado para revisao/aprendizagem: topicos, jargao
                      explicado, perguntas em aberto.

Regras que valem para TODOS os motores deste modulo (ver PRODUCT.md e
FEATURE_VALIDATION_AND_ROADMAP.md):
  - a reorganizacao NUNCA inventa fatos nem apaga silenciosamente conteudo
    importante do clean;
  - o resultado identifica motor, modelo e data (feito pelo chamador via
    "engine"/"model"/"generated_at" no dict devolvido);
  - nenhuma chamada acontece sem a chave da respetiva finalidade
    (ver credentials.KEY_PURPOSES) configurada explicitamente pelo utilizador.

NOTA DE MANUTENCAO: o benchmark de 06/08/2026 testou o alias "deepseek-chat"
(V4-Flash), ja descontinuado pela DeepSeek — usa-se "deepseek-v4-flash"
aqui. Tambem foi levantada uma suspeita de descontinuacao do "grok-4-fast"
(pagina de docs dedicada fora do ar na xAI), mas chamadas reais em
07/08/2026 confirmaram os DOIS modelos ativos e funcionais na conta ("
deepseek-chat" tambem respondeu quando testado diretamente). Se algum dos
dois parar de responder no futuro, e' sinal de descontinuacao real — nesse
caso trocar o identificador aqui (deepseek: ver docs.deepseek.com; grok: ver
docs.x.ai) antes de investigar mais fundo.
"""
import json
import time
from datetime import datetime, timezone

import requests

BLOCK_TYPES = (
    "section", "objective", "requirement", "decision", "action",
    "risk", "question", "topic", "technical_context", "excerpt",
)

PROFILES = ("detalhado", "resumo_tecnico", "estudo")

_PROFILE_INSTRUCTIONS = {
    "detalhado": (
        "Gere a versao DETALHADA: cubra secoes/subtitulos, objetivo, "
        "requisitos, decisoes, acoes com responsavel quando identificavel, "
        "riscos, duvidas, topicos principais, contexto tecnico, jargoes/"
        "siglas com explicacao, e trechos relevantes com falante/timestamp "
        "quando disponiveis no transcript."
    ),
    "resumo_tecnico": (
        "Gere um RESUMO TECNICO enxuto: só objetivo em uma frase, decisoes, "
        "acoes com responsavel quando identificavel, e riscos. Omita "
        "conversa paralela, small talk e detalhes que nao mudam a decisao."
    ),
    "estudo": (
        "Gere uma versao de ESTUDO: organize por topicos de aprendizagem, "
        "explique jargoes/siglas tecnicas encontradas, liste perguntas em "
        "aberto/duvidas nao resolvidas, e destaque o contexto tecnico "
        "necessario para alguem que nao estava na conversa entender o "
        "material."
    ),
}

_SYSTEM_PROMPT = """Você transforma o transcript CLEAN de uma reunião/aula em um \
documento estruturado, devolvido como um único objeto JSON (nada de texto \
fora do JSON, nada de blocos de código markdown).

Regras inegociáveis:
- Nunca invente fatos, nomes, decisões ou números que não estejam no texto \
de origem. Se algo não está claro, marque como dúvida/pergunta em vez de \
adivinhar.
- Nunca apague silenciosamente conteúdo importante — se cortar algo (ex.: \
no perfil resumo_tecnico), o corte é por design do perfil, não perda \
acidental de informação relevante ao objetivo da conversa.
- A mesma ideia pode reaparecer espalhada ao longo da conversa: agrupe por \
tema, não apenas por ordem cronológica.
- Preserve nomes próprios, números e termos técnicos exatamente como \
aparecem no transcript.
- Responda em português (varie PT-PT/PT-BR conforme o texto de origem), \
preservando trechos em outro idioma quando fizerem parte do conteúdo \
original (code-switching).

Formato de saída — APENAS este objeto JSON, sem comentários:
{
  "title": "string curta",
  "objective": "string de uma frase, ou null se não for possível resumir",
  "blocks": [
    {
      "id": "b1",
      "type": "um de: section, objective, requirement, decision, action, risk, question, topic, technical_context, excerpt",
      "heading": "string ou null",
      "content": "string (ou lista de strings para listas, ex. requisitos/ações)",
      "speaker": "string ou null",
      "timestamp": "string ou null"
    }
  ],
  "jargon": [{"term": "string", "meaning": "string"}]
}

IDs de bloco: sequenciais e estáveis dentro desta geração ("b1", "b2", ...).
"""


def _build_messages(clean_text: str, profile: str) -> list:
    instruction = _PROFILE_INSTRUCTIONS.get(profile, _PROFILE_INSTRUCTIONS["detalhado"])
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": (
            f"{instruction}\n\n"
            f"--- TRANSCRIPT CLEAN (fonte única, não invente além disto) ---\n"
            f"{clean_text}\n"
            f"--- FIM DO TRANSCRIPT ---"
        )},
    ]


def _strip_code_fence(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t[3:]
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def _parse_document(raw_text: str) -> dict:
    """Faz parsing tolerante da resposta do motor. Levanta ValueError com
    mensagem util (vira "problem"/erro NDJSON) se nao for JSON valido."""
    cleaned = _strip_code_fence(raw_text)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValueError(f"Resposta do motor nao e JSON valido: {e}") from e
    if not isinstance(data, dict) or "blocks" not in data:
        raise ValueError("Resposta do motor nao tem o formato esperado (falta 'blocks').")
    data.setdefault("title", "Documento sem titulo")
    data.setdefault("objective", None)
    data.setdefault("jargon", [])
    for i, block in enumerate(data.get("blocks") or []):
        block.setdefault("id", f"b{i + 1}")
        block.setdefault("heading", None)
        block.setdefault("speaker", None)
        block.setdefault("timestamp", None)
        if block.get("type") not in BLOCK_TYPES:
            block["type"] = "section"
    return data


def _finish(document: dict, engine_id: str, model: str, profile: str, elapsed_s: float, usage: dict | None) -> dict:
    document["engine"] = engine_id
    document["model"] = model
    document["profile"] = profile
    document["generated_at"] = datetime.now(timezone.utc).isoformat()
    return {
        "ok": True,
        "document": document,
        "processing_s": round(elapsed_s, 1),
        "usage": usage or {},
        "problems": [],
    }


def _fail(message: str) -> dict:
    return {"ok": False, "document": None, "problems": [message]}


# ---------------------------------------------------------------------------
# OpenAI e compativeis com a API OpenAI (chat.completions + response_format
# json_object): OpenAI, DeepSeek e xAI/Grok expõem o mesmo formato de request.
# ---------------------------------------------------------------------------

def _run_openai_compatible(clean_text, api_key, engine_id, model, base_url, profile, log, temperature=0.2):
    from openai import OpenAI

    client = OpenAI(api_key=api_key, base_url=base_url) if base_url else OpenAI(api_key=api_key)
    log(f"Enviando transcript para {engine_id} ({model})...")
    started = time.time()
    kwargs = dict(
        model=model,
        messages=_build_messages(clean_text, profile),
        response_format={"type": "json_object"},
    )
    # gpt-5-mini (modelo de raciocinio) só aceita o temperature padrao (1) —
    # 400 "Unsupported value" se enviarmos qualquer outro valor (achado real,
    # 07/08/2026). Outros motores OpenAI-compativeis aceitam 0.2 normalmente.
    if temperature is not None:
        kwargs["temperature"] = temperature
    try:
        resp = client.chat.completions.create(**kwargs)
    except Exception as e:  # noqa: BLE001
        return _fail(f"Falha ao chamar {engine_id}: {e}")
    elapsed = time.time() - started
    raw_text = resp.choices[0].message.content or ""
    try:
        document = _parse_document(raw_text)
    except ValueError as e:
        return _fail(str(e))
    usage = {}
    if getattr(resp, "usage", None):
        usage = {
            "input_tokens": getattr(resp.usage, "prompt_tokens", None),
            "output_tokens": getattr(resp.usage, "completion_tokens", None),
        }
    log(f"Recebido em {elapsed:.1f}s ({len(document.get('blocks', []))} blocos).")
    return _finish(document, engine_id, model, profile, elapsed, usage)


def run_deepseek(clean_text, api_key, profile="detalhado", log=print):
    # https://api-docs.deepseek.com — API compativel com OpenAI.
    # "deepseek-chat" (alias antigo, V4-Flash) foi descontinuado; usar o
    # identificador atual "deepseek-v4-flash". Confirmar na conta antes de
    # depender disto em producao (ver nota de manutencao no topo do modulo).
    return _run_openai_compatible(clean_text, api_key, "deepseek", "deepseek-v4-flash",
                                   "https://api.deepseek.com", profile, log)


def run_grok(clean_text, api_key, profile="detalhado", log=print):
    # https://docs.x.ai — API compativel com OpenAI. "grok-4-fast" confirmado
    # ativo com chamada real em 07/08/2026 (a preocupacao de descontinuacao
    # levantada pela pesquisa de 06/08 nao se confirmou na pratica).
    return _run_openai_compatible(clean_text, api_key, "grok", "grok-4-fast",
                                   "https://api.x.ai/v1", profile, log)


def run_gpt5_mini(clean_text, api_key, profile="detalhado", log=print):
    # gpt-5-mini so aceita o temperature padrao (achado real, 07/08/2026 —
    # ver nota em _run_openai_compatible); por isso temperature=None aqui.
    return _run_openai_compatible(clean_text, api_key, "gpt5_mini", "gpt-5-mini",
                                   None, profile, log, temperature=None)


# ---------------------------------------------------------------------------
# Anthropic (Claude) — Messages API, sem SDK dedicado instalado; usa requests
# diretamente para nao acrescentar dependencia so por isto.
# ---------------------------------------------------------------------------

def _run_claude(clean_text, api_key, engine_id, model, profile, log):
    log(f"Enviando transcript para {engine_id} ({model})...")
    started = time.time()
    messages = _build_messages(clean_text, profile)
    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    user_msg = next(m["content"] for m in messages if m["role"] == "user")
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": 8192,
                "system": system_msg,
                "messages": [{"role": "user", "content": user_msg}],
            },
            timeout=180,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        detail = getattr(e.response, "text", "") if getattr(e, "response", None) is not None else ""
        return _fail(f"Falha ao chamar {engine_id}: {e} {detail}".strip())
    elapsed = time.time() - started
    payload = resp.json()
    raw_text = "".join(block.get("text", "") for block in payload.get("content", []))
    try:
        document = _parse_document(raw_text)
    except ValueError as e:
        return _fail(str(e))
    usage_raw = payload.get("usage", {}) or {}
    usage = {"input_tokens": usage_raw.get("input_tokens"), "output_tokens": usage_raw.get("output_tokens")}
    log(f"Recebido em {elapsed:.1f}s ({len(document.get('blocks', []))} blocos).")
    return _finish(document, engine_id, model, profile, elapsed, usage)


def run_claude_haiku(clean_text, api_key, profile="detalhado", log=print):
    return _run_claude(clean_text, api_key, "claude_haiku", "claude-haiku-4-5-20251001", profile, log)


def run_claude_sonnet(clean_text, api_key, profile="detalhado", log=print):
    return _run_claude(clean_text, api_key, "claude_sonnet", "claude-sonnet-5", profile, log)


# ---------------------------------------------------------------------------
# Google Gemini — REST generateContent, tambem via requests (sem SDK extra).
# ---------------------------------------------------------------------------

def run_gemini(clean_text, api_key, profile="detalhado", log=print):
    model = "gemini-3.6-flash"
    log(f"Enviando transcript para gemini ({model})...")
    started = time.time()
    messages = _build_messages(clean_text, profile)
    system_msg = next(m["content"] for m in messages if m["role"] == "system")
    user_msg = next(m["content"] for m in messages if m["role"] == "user")
    try:
        resp = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            params={"key": api_key},
            json={
                "system_instruction": {"parts": [{"text": system_msg}]},
                "contents": [{"role": "user", "parts": [{"text": user_msg}]}],
                "generationConfig": {"responseMimeType": "application/json", "temperature": 0.2},
            },
            timeout=180,
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        detail = getattr(e.response, "text", "") if getattr(e, "response", None) is not None else ""
        return _fail(f"Falha ao chamar gemini: {e} {detail}".strip())
    elapsed = time.time() - started
    payload = resp.json()
    try:
        candidate = payload["candidates"][0]
        raw_text = "".join(p.get("text", "") for p in candidate["content"]["parts"])
    except (KeyError, IndexError) as e:
        return _fail(f"Resposta do gemini sem conteudo utilizavel: {e} — payload: {payload}")
    try:
        document = _parse_document(raw_text)
    except ValueError as e:
        return _fail(str(e))
    usage_raw = payload.get("usageMetadata", {}) or {}
    usage = {"input_tokens": usage_raw.get("promptTokenCount"), "output_tokens": usage_raw.get("candidatesTokenCount")}
    log(f"Recebido em {elapsed:.1f}s ({len(document.get('blocks', []))} blocos).")
    return _finish(document, "gemini", model, profile, elapsed, usage)
