"""
Registo de motores de transcricao disponiveis — usado por qualquer
interface (CLI, IPC/HTTP local para o shell Tauri, testes) para listar
opcoes, saber que chave cada uma precisa, e invocar o motor sem acoplar a
UI a logica de cada provedor.
"""
from . import formatting

# Registo — 2026-08-13: os 4 modulos de motor (assemblyai/whisper_openai/
# deepgram/gpt4o_openai) eram importados aqui EM CIMA, sem condicao — e este
# ficheiro e importado por cli.py logo no arranque, ou seja, em TODO comando
# do worker, mesmo os que nada tem a ver com transcricao (notebook-note-open,
# library, etc.). Dois desses modulos importam "openai" (SDK pesado) e dois
# importam audio_chunks.py, que importa numpy + av (PyAV, dezenas de DLLs de
# ffmpeg) — o Leonardo reparou que a app "voltou a ficar lenta" assim que
# passamos a correr sempre em modo desenvolvimento (sem o worker empacotado);
# esta e' a causa concreta: cada spawn de processo pagava estes imports
# pesados mesmo para abrir uma nota do Caderno. Os wrappers abaixo adiam o
# import de cada motor para o momento em que e' mesmo invocado (comando
# `transcribe`) — os restantes comandos deixam de pagar este custo.
def _run_assemblyai(*args, **kwargs):
    from . import assemblyai
    return assemblyai.run(*args, **kwargs)


def _run_assemblyai_stt37(*args, **kwargs):
    from . import assemblyai
    return assemblyai.run(*args, **kwargs, speech_models=['assemblyai-stt-3-7'], engine_id='assemblyai_stt37')


def _run_gpt4o_mini(*args, **kwargs):
    from . import gpt4o_openai
    return gpt4o_openai.run(*args, **kwargs, model_id='gpt-4o-mini-transcribe', engine_id='gpt4o_mini')


def _run_assemblyai_u2(*args, **kwargs):
    from . import assemblyai
    return assemblyai.run(*args, **kwargs, speech_models=["universal-2"], engine_id="assemblyai_u2")


def _run_deepgram_nova2(*args, **kwargs):
    from . import deepgram
    return deepgram.run(*args, **kwargs, model_id="nova-2", engine_id="deepgram_nova2")


def _run_groq_turbo(*args, **kwargs):
    from . import whisper_openai
    return whisper_openai.run(*args, **kwargs, model_id="whisper-large-v3-turbo",
                              engine_id="groq_v3_turbo", base_url="https://api.groq.com/openai/v1",
                              price_per_hour=0.04)


def _run_groq_large(*args, **kwargs):
    from . import whisper_openai
    return whisper_openai.run(*args, **kwargs, model_id="whisper-large-v3",
                              engine_id="groq_v3", base_url="https://api.groq.com/openai/v1",
                              price_per_hour=0.111)


def _run_gpt_transcribe(*args, **kwargs):
    from . import audio_multimodel
    return audio_multimodel.run(*args, **kwargs, engine_id="gpt_transcribe")


def _run_gemini_audio(*args, **kwargs):
    from . import audio_multimodel
    return audio_multimodel.run(*args, **kwargs, engine_id="gemini_audio")


def _run_xai_voice(*args, **kwargs):
    from . import audio_multimodel
    return audio_multimodel.run(*args, **kwargs, engine_id="grok_voice_stt")


def _run_whisper_openai(*args, **kwargs):
    from . import whisper_openai
    return whisper_openai.run(*args, **kwargs)


def _run_deepgram(*args, **kwargs):
    from . import deepgram
    return deepgram.run(*args, **kwargs)


def _run_gpt4o_openai(*args, **kwargs):
    from . import gpt4o_openai
    return gpt4o_openai.run(*args, **kwargs)


ENGINES = {
    "assemblyai": {
        "provider": "assemblyai", "model": "universal-3-5-pro",
        "label": "AssemblyAI Universal-3.5 Pro (recomendado)",
        "recommended": True,
        "key_name": "ASSEMBLYAI_API_KEY",
        "run": _run_assemblyai,
        "info": "Melhor fidelidade geral, multilingue (PT/EN), diarizacao e melhor custo observado. Motor principal.",
        "primary": True,
    },
    "assemblyai_stt37": {
        "provider": "assemblyai", "model": "assemblyai-stt-3-7",
        "label": "AssemblyAI STT-3.7 (benchmark pendente)",
        "key_name": "ASSEMBLYAI_API_KEY", "run": _run_assemblyai_stt37,
        "info": "32 idiomas, code-switching e diarização; novo modelo em testes. ~US$0,21/h.",
        "primary": False,
    },
    "assemblyai_u2": {
        "provider": "assemblyai", "model": "universal-2",
        "label": "Universal-2 (99 idiomas · económico)",
        "key_name": "ASSEMBLYAI_API_KEY", "run": _run_assemblyai_u2,
        "info": "Cobertura ampla de idiomas, alternativa económica. Menor precisão em reuniões PT/EN do que Universal-3.5 Pro; benchmark local pendente.",
        "primary": False,
    },
    "gpt_transcribe": {
        "provider": "openai", "model": "gpt-transcribe",
        "label": "GPT-Transcribe (atual · em avaliação)",
        "recommended": True,
        "key_name": "OPENAI_API_KEY", "run": _run_gpt_transcribe,
        "info": "Nova opção oficial para áudio gravado; multi-idioma. Transcrição curta aprovada. Tempos aproximados por bloco; custo por tokens de áudio/texto, conferir no painel. Benchmark longo pendente.",
        "primary": False,
    },
    "gemini_audio": {
        "provider": "gemini", "model": "gemini-3-flash-preview",
        "label": "Gemini 3 Flash · áudio (em avaliação)",
        "key_name": "GEMINI_API_KEY", "run": _run_gemini_audio,
        "info": "LLM multimodal que aceita áudio diretamente, sem STT intermediário. Teste curto aprovado. Sem timestamps exatos por palavra; custo variável por tokens. Benchmark de reuniões pendente.",
        "primary": False,
    },
    "grok_voice_stt": {
        "provider": "grok", "model": "grok-voice-transcribe-2.0",
        "label": "Grok Voice Transcribe 2.0 (em avaliação)",
        "key_name": "GROK_API_KEY", "run": _run_xai_voice,
        "info": "Transcrição nativa xAI de 38+ idiomas, reconhece mudança de idioma e devolve tempos por palavra; teste curto HTTP 200. Ainda sem benchmark local longo. Custos: consultar condições da API.",
        "primary": False,
    },
    "whisper_openai": {
        "provider": "openai", "model": "whisper-1",
        "label": "whisper-1 (OpenAI)",
        "key_name": "OPENAI_API_KEY",
        "run": _run_whisper_openai,
        "info": "Whisper-1 legado, bom português e segmentos; falha com inglês misto em benchmarks. Descontinuação anunciada para 26/02/2027. Preferir avaliar GPT-Transcribe.",
        "primary": False,
    },
    "deepgram": {
        "provider": "deepgram", "model": "nova-3",
        "label": "Deepgram Nova-3",
        "recommended": True,
        "key_name": "DEEPGRAM_API_KEY",
        "run": _run_deepgram,
        "info": "Baixa latencia, candidato a modo ao vivo futuro; diarizacao/qualidade geral um pouco abaixo da AssemblyAI.",
        "primary": False,
    },
    "deepgram_nova2": {
        "provider": "deepgram", "model": "nova-2",
        "label": "Nova-2 (legado · teste pendente)",
        "key_name": "DEEPGRAM_API_KEY", "run": _run_deepgram_nova2,
        "info": "Nova-2 detecta o idioma predominante; para áudio com português+inglês misturados, prefira Nova-3. Custo histórico US$0,0043/min; preço atual e benchmark longo pendentes.",
        "primary": False,
    },
    "gpt4o_openai": {
        "provider": "openai", "model": "gpt-4o-transcribe",
        "label": "gpt-4o-transcribe (OpenAI) — nao recomendado",
        "key_name": "OPENAI_API_KEY",
        "run": _run_gpt4o_openai,
        "info": "Não recomendado para reuniões longas: repetições graves observadas nos benchmarks. Legado até 26/02/2027, mantido para comparação.",
        "primary": False,
    },
    "gpt4o_mini": {
        "provider": "openai", "model": "gpt-4o-mini-transcribe",
        "label": "gpt-4o-mini-transcribe (benchmark pendente)",
        "key_name": "OPENAI_API_KEY", "run": _run_gpt4o_mini,
        "info": "Modelo económico legado (~US$0,003/min em tarifas históricas); curto teste passou, reuniões longas pendentes. Descontinuação anunciada 26/02/2027.",
        "primary": False,
    },
    "groq_v3_turbo": {
        "provider": "groq", "model": "whisper-large-v3-turbo",
        "label": "Whisper Large V3 Turbo (chave Groq necessária)",
        "key_name": "GROQ_API_KEY", "run": _run_groq_turbo,
        "info": "Whisper V3 Turbo via Groq, multilingue e rápido; preço público US$0,04/h. Ainda não homologado com credencial Groq.",
        "primary": False,
    },
    "groq_v3": {
        "provider": "groq", "model": "whisper-large-v3",
        "label": "Whisper Large V3 (chave Groq necessária)",
        "key_name": "GROQ_API_KEY", "run": _run_groq_large,
        "info": "Whisper Large V3 via Groq, multilingue; preço público US$0,111/h. Ainda não homologado com credencial Groq.",
        "primary": False,
    },
}

# Motores de FORMATACAO (clean -> documento estruturado, ADF-01). Distinto de
# ENGINES (audio -> transcript): entrada e saida diferentes, chave diferente
# por finalidade (ver credentials.KEY_PURPOSES). Nao ha motor padrao — os
# seis foram validados no benchmark de 06/08/2026 (docs/FEATURE_VALIDATION_
# AND_ROADMAP.md) e ficam todos disponiveis; a UI mostra nome do modelo +
# custo/hora lado a lado para a pessoa escolher.
def _format_variant(provider, engine_id, model):
    """Wrapper leve para modelos concretos com endpoints já homologados."""
    def run(clean_text, api_key, profile="detalhado", log=print):
        if provider == "deepseek":
            return formatting._run_openai_compatible(
                clean_text, api_key, engine_id, model, "https://api.deepseek.com",
                profile, log)
        if provider == "grok":
            return formatting._run_openai_compatible(
                clean_text, api_key, engine_id, model, "https://api.x.ai/v1",
                profile, log, temperature=None)
        if provider == "openai":
            return formatting._run_openai_compatible(
                clean_text, api_key, engine_id, model, None,
                profile, log, temperature=None)
        if provider == "anthropic":
            return formatting._run_claude(
                clean_text, api_key, engine_id, model, profile, log)
        if provider == "gemini":
            return formatting.run_gemini(
                clean_text, api_key, profile=profile, log=log,
                model_id=model, engine_id=engine_id)
        raise ValueError("Provedor de formatação não suportado")
    return run


FORMAT_ENGINES = {
    "deepseek": {
        "provider": "deepseek", "model": "deepseek-flash",
        "label": "DeepSeek Flash (API verificada)",
        "recommended": True,
        "key_name": "DEEPSEEK_API_KEY",
        "run": formatting.run_deepseek,
        "info": "DeepSeek Flash: API e formatação curta aprovadas. Referência histórica indicava baixo custo, mas preços dependem de tokens e plano; benchmark longo pendente.",
        "cost_hora_brl": None,
    },
    "grok": {
        "provider": "grok", "model": "grok-4.20-0309-non-reasoning",
        "label": "Grok 4.20 (API verificada)",
        "recommended": True,
        "key_name": "GROK_API_KEY",
        "run": formatting.run_grok,
        "info": "Grok 4.20 não-raciocínio: API e formatação curta aprovadas. Preço e fidelidade deste ID ainda não têm benchmark longo; versão anterior era rápida.",
        "cost_hora_brl": None,
    },
    "gpt5_mini": {
        "provider": "openai", "model": "gpt-5-mini",
        "label": "OpenAI (gpt-5-mini)",
        "recommended": True,
        "key_name": "OPENAI_API_KEY",
        "run": formatting.run_gpt5_mini,
        "info": "Custo/qualidade intermediario (~R$0,10-0,28/hora).",
        "cost_hora_brl": "0,10–0,28",
    },
    "claude_haiku": {
        "provider": "anthropic", "model": "claude-haiku-4-5-20251001",
        "label": "Claude Haiku 4.5",
        "recommended": True,
        "key_name": "ANTHROPIC_API_KEY",
        "run": formatting.run_claude_haiku,
        "info": "Boa organizacao (usou tabela markdown para responsabilidades no teste). ~R$0,21-0,54/hora.",
        "cost_hora_brl": "0,21–0,54",
    },
    "gemini": {
        "provider": "gemini", "model": "gemini-3-flash-preview",
        "label": "Gemini 3 Flash Preview (API verificada)",
        "recommended": True,
        "key_name": "GEMINI_API_KEY",
        "run": formatting.run_gemini,
        "info": "Gemini 3 Flash Preview: API e formatação curta aprovadas. Quotas e faturamento dependem do projeto Gemini API, não automaticamente da assinatura Google Pro.",
        "cost_hora_brl": None,
    },
    "claude_sonnet": {
        "provider": "anthropic", "model": "claude-sonnet-5",
        "label": "Claude Sonnet 5",
        "key_name": "ANTHROPIC_API_KEY",
        "run": formatting.run_claude_sonnet,
        "info": "Claude Sonnet 5: referência histórica para estruturação completa. Tarifas promocionais antigas expiraram; consultar preço atual e revalidar o modelo.",
        "cost_hora_brl": "0,73–1,62",
    },
    "deepseek_pro": {
        "provider": "deepseek", "model": "deepseek-v4-pro",
        "label": "DeepSeek V4 Pro (candidato · mais recursos)",
        "key_name": "DEEPSEEK_API_KEY",
        "run": _format_variant("deepseek", "deepseek_pro", "deepseek-v4-pro"),
        "info": "Modelo V4 Pro com saída JSON verificada em chamada curta; custo e qualidade em transcrições longas ainda não aferidos.",
        "cost_hora_brl": None,
        "recommended": False,
    },
    "grok_43": {
        "provider": "grok", "model": "grok-4.3",
        "label": "Grok 4.3 (alternativo · em teste)",
        "key_name": "GROK_API_KEY",
        "run": _format_variant("grok", "grok_43", "grok-4.3"),
        "info": "Grok 4.3 com saída JSON verificada. Comparar custo, latência e precisão com Grok 4.20.",
        "cost_hora_brl": None,
        "recommended": False,
    },
    "openai_nano": {
        "provider": "openai", "model": "gpt-5.4-nano",
        "label": "GPT-5.4 Nano (baixo custo · em teste)",
        "key_name": "OPENAI_API_KEY",
        "run": _format_variant("openai", "openai_nano", "gpt-5.4-nano"),
        "info": "Opção de texto compacta; JSON verificado, benchmarking estruturado pendente. Custo por tokens, não por hora fixa.",
        "cost_hora_brl": None,
        "recommended": False,
    },
    "openai_mini": {
        "provider": "openai", "model": "gpt-5.4-mini",
        "label": "GPT-5.4 Mini (alternativo · em teste)",
        "key_name": "OPENAI_API_KEY",
        "run": _format_variant("openai", "openai_mini", "gpt-5.4-mini"),
        "info": "Opção intermediária de texto; JSON verificado, benchmarking estruturado pendente. Custo por tokens.",
        "cost_hora_brl": None,
        "recommended": False,
    },
    "claude_haiku55": {
        "provider": "anthropic", "model": "claude-haiku-5-5",
        "label": "Claude Haiku 5.5 (candidato · em teste)",
        "key_name": "ANTHROPIC_API_KEY",
        "run": _format_variant("anthropic", "claude_haiku55", "claude-haiku-5-5"),
        "info": "Haiku 5.5 validado em geração de JSON curto. Benchmark de estruturação e custos ainda pendente.",
        "cost_hora_brl": None,
        "recommended": False,
    },
    "claude_sonnet55": {
        "provider": "anthropic", "model": "claude-sonnet-5-5",
        "label": "Claude Sonnet 5.5 (maior capacidade · em teste)",
        "key_name": "ANTHROPIC_API_KEY",
        "run": _format_variant("anthropic", "claude_sonnet55", "claude-sonnet-5-5"),
        "info": "Sonnet 5.5 validado em JSON curto; potencial maior qualidade, com custo a conferir. Benchmark pendente.",
        "cost_hora_brl": None,
        "recommended": False,
    },
    "gemini_lite31": {
        "provider": "gemini", "model": "gemini-3.1-flash-lite-preview",
        "label": "Gemini 3.1 Flash Lite (económico · em teste)",
        "key_name": "GEMINI_API_KEY",
        "run": _format_variant("gemini", "gemini_lite31", "gemini-3.1-flash-lite-preview"),
        "info": "Modelo de texto económico em preview; JSON curto validado, custos e fidelidade ainda não aferidos.",
        "cost_hora_brl": None,
        "recommended": False,
    },
}