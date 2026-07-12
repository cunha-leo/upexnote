"""
Registo de motores de transcricao disponiveis — usado por qualquer
interface (CLI, IPC/HTTP local para o shell Tauri, testes) para listar
opcoes, saber que chave cada uma precisa, e invocar o motor sem acoplar a
UI a logica de cada provedor.
"""
from . import assemblyai, whisper_openai, deepgram, gpt4o_openai

ENGINES = {
    "assemblyai": {
        "label": "AssemblyAI Universal-3.5 Pro (recomendado)",
        "key_name": "ASSEMBLYAI_API_KEY",
        "run": assemblyai.run,
        "info": "Melhor fidelidade geral, multilingue (PT/EN), diarizacao e melhor custo observado. Motor principal.",
        "primary": True,
    },
    "whisper_openai": {
        "label": "whisper-1 (OpenAI)",
        "key_name": "OPENAI_API_KEY",
        "run": whisper_openai.run,
        "info": "Rapido e barato, muito fiel em portugues; pode falhar em ingles inserido a meio de frases (limitacao de deteccao de idioma por bloco).",
        "primary": False,
    },
    "deepgram": {
        "label": "Deepgram Nova-3",
        "key_name": "DEEPGRAM_API_KEY",
        "run": deepgram.run,
        "info": "Baixa latencia, candidato a modo ao vivo futuro; diarizacao/qualidade geral um pouco abaixo da AssemblyAI.",
        "primary": False,
    },
    "gpt4o_openai": {
        "label": "gpt-4o-transcribe (OpenAI) — nao recomendado",
        "key_name": "OPENAI_API_KEY",
        "run": gpt4o_openai.run,
        "info": "Desqualificado para reunioes longas: loops de alucinacao graves em testes reais. Mantido so por referencia.",
        "primary": False,
    },
}
