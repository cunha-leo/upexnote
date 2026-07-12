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

## Ponto de entrada: CLI NDJSON (`transcription.cli`)

O `apps/desktop` (shell Tauri) lança este worker como processo/sidecar e lê o **stdout linha a linha** — cada linha é um objeto JSON completo (NDJSON). Sem servidor HTTP, portas ou CORS.

### Segurança das chaves

As chaves API **nunca** são passadas por argumentos (argv é visível na lista de processos). O `transcribe` lê a chave do Windows Credential Manager sozinho. Para gravar uma chave, o utilizador corre `set-key`, que lê o valor por stdin **sem eco** (`getpass`) — a chave nunca fica no comando nem no histórico do terminal.

### Comandos

```bash
# Listar motores (JSON único), incluindo se a chave já está configurada
python -m transcription.cli engines

# Transcrever — emite eventos NDJSON: start, progress (0..N), result | error
python -m transcription.cli transcribe --engine assemblyai --file "C:/gravacoes/reuniao.mp4"

# Guardar uma chave (corre isto tu mesmo; lê por stdin, sem eco)
python -m transcription.cli set-key --name ASSEMBLYAI_API_KEY

# Ver se uma chave está configurada (nunca revela o valor)
python -m transcription.cli check-key --name ASSEMBLYAI_API_KEY
```

### Protocolo de eventos do `transcribe` (stdout, um JSON por linha)

| `type` | Quando | Campos |
|---|---|---|
| `start` | ao iniciar | `engine`, `file` |
| `progress` | 0..N vezes | `message` |
| `result` | sucesso | `ok`, `clean_text`, `clean_path`, `raw_path`, `cost`, `duration_s`, `problems`, `language` |
| `error` | falha | `message` |

Prints internos soltos do pipeline vão para **stderr**, para o stdout ficar só com NDJSON. Código de saída: `0` sucesso, `2` concluído mas com validação falhada (ver `problems`), `1` erro.

### Uso direto em Python (para testes)

```python
from transcription.credentials import get_key
from transcription import assemblyai

result = assemblyai.run("C:/caminho/para/reuniao.mp4", get_key("ASSEMBLYAI_API_KEY"))
print(result["clean_text"])
```

## Próximo passo

Ligar o `apps/desktop` (Tauri) a esta CLI: lançar o sidecar, mapear `engines`/`check-key` para o ecrã de definições e `transcribe` para a barra de progresso + vista de transcript.
