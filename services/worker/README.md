# UpexNote Worker

Worker local responsável por encapsular os pipelines Python já validados.

## Estado

Migrado de `C:\Users\cunha\Project\scripts\` (protótipo Tkinter) em 2026-07-12, sem alterar a lógica de nenhum motor — só o destino dos ficheiros gerados, que passou de `resultados\<motor>\` para `storage\transcripts\<motor>\`, e a remoção do acoplamento à interface Tkinter (essa UI será substituída por Tauri + React, ver `docs/ARCHITECTURE.md`).

## Estrutura

`transcription/` — pacote Python com os motores e utilitários partilhados:

- `assemblyai.py` — motor principal (AssemblyAI Universal-3.5 Pro).
- `whisper_openai.py` — whisper-1 (OpenAI), alternativa económica/monolingue.
- `deepgram.py` — Nova-3, candidato a modo ao vivo futuro.
- `gpt4o_openai.py` — gpt-4o-transcribe, **não recomendado** (mantido só por referência; ver docstring do módulo).
- `audio_chunks.py` / `transcript_utils.py` — chunking em silêncio, mapa de timestamps, deteção de alucinações/loops, validação de cobertura.
- `paths.py` — resolve `storage/transcripts/<motor>/` a partir da raiz do projeto.
- `credentials.py` — chaves via Windows Credential Manager (`keyring`), nunca em ficheiro.
- `registry.py` — `ENGINES` dict framework-agnostic para uma futura CLI/IPC invocar qualquer motor sem acoplar à lógica de cada provedor.

## Uso (ainda sem CLI/IPC formal)

```python
from transcription.credentials import get_key
from transcription import assemblyai

result = assemblyai.run("C:/caminho/para/reuniao.mp4", get_key("ASSEMBLYAI_API_KEY"))
print(result["clean_text"])
```

## Próximo passo

Construir o primeiro ponto de entrada (CLI ou pequeno servidor IPC/HTTP local) que o `apps/desktop` possa chamar, usando `registry.ENGINES` para listar motores e invocar `run()`.
