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
        "label": "AssemblyAI Universal-3.5 Pro (recomendado)",
        "key_name": "ASSEMBLYAI_API_KEY",
        "run": _run_assemblyai,
        "info": "Melhor fidelidade geral, multilingue (PT/EN), diarizacao e melhor custo observado. Motor principal.",
        "primary": True,
    },
    "whisper_openai": {
        "label": "whisper-1 (OpenAI)",
        "key_name": "OPENAI_API_KEY",
        "run": _run_whisper_openai,
        "info": "Rapido e barato, muito fiel em portugues; pode falhar em ingles inserido a meio de frases (limitacao de deteccao de idioma por bloco).",
        "primary": False,
    },
    "deepgram": {
        "label": "Deepgram Nova-3",
        "key_name": "DEEPGRAM_API_KEY",
        "run": _run_deepgram,
        "info": "Baixa latencia, candidato a modo ao vivo futuro; diarizacao/qualidade geral um pouco abaixo da AssemblyAI.",
        "primary": False,
    },
    "gpt4o_openai": {
        "label": "gpt-4o-transcribe (OpenAI) — nao recomendado",
        "key_name": "OPENAI_API_KEY",
        "run": _run_gpt4o_openai,
        "info": "Desqualificado para reunioes longas: loops de alucinacao graves em testes reais. Mantido so por referencia.",
        "primary": False,
    },
}

# Motores de FORMATACAO (clean -> documento estruturado, ADF-01). Distinto de
# ENGINES (audio -> transcript): entrada e saida diferentes, chave diferente
# por finalidade (ver credentials.KEY_PURPOSES). Nao ha motor padrao — os
# seis foram validados no benchmark de 06/08/2026 (docs/FEATURE_VALIDATION_
# AND_ROADMAP.md) e ficam todos disponiveis; a UI mostra nome do modelo +
# custo/hora lado a lado para a pessoa escolher.
FORMAT_ENGINES = {
    "deepseek": {
        "label": "DeepSeek (deepseek-v4-flash)",
        "key_name": "DEEPSEEK_API_KEY",
        "run": formatting.run_deepseek,
        "info": "Mais barato no benchmark (~R$0,02-0,04/hora). Alias antigo 'deepseek-chat' foi descontinuado.",
        "cost_hora_brl": "0,02–0,04",
    },
    "grok": {
        "label": "Grok (grok-4-fast)",
        "key_name": "GROK_API_KEY",
        "run": formatting.run_grok,
        "info": "Mais rapido e mais enxuto no teste real (confirmado ativo em 07/08/2026). ~R$0,03-0,05/hora.",
        "cost_hora_brl": "0,03–0,05",
    },
    "gpt5_mini": {
        "label": "OpenAI (gpt-5-mini)",
        "key_name": "OPENAI_API_KEY",
        "run": formatting.run_gpt5_mini,
        "info": "Custo/qualidade intermediario (~R$0,10-0,28/hora).",
        "cost_hora_brl": "0,10–0,28",
    },
    "claude_haiku": {
        "label": "Claude Haiku 4.5",
        "key_name": "ANTHROPIC_API_KEY",
        "run": formatting.run_claude_haiku,
        "info": "Boa organizacao (usou tabela markdown para responsabilidades no teste). ~R$0,21-0,54/hora.",
        "cost_hora_brl": "0,21–0,54",
    },
    "gemini": {
        "label": "Gemini (gemini-3.6-flash)",
        "key_name": "GEMINI_API_KEY",
        "run": formatting.run_gemini,
        "info": "Texto legivel e sensato. ~R$0,51-1,48/hora.",
        "cost_hora_brl": "0,51–1,48",
    },
    "claude_sonnet": {
        "label": "Claude Sonnet 5",
        "key_name": "ANTHROPIC_API_KEY",
        "run": formatting.run_claude_sonnet,
        "info": "Mais completo no benchmark (separa trabalho de conversa pessoal). ~R$0,73-1,62/hora; preco promocional ate 31/08/2026.",
        "cost_hora_brl": "0,73–1,62",
    },
}
