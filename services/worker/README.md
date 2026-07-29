# UpexNote Worker

Worker local Python do UpexNote, empacotado com PyInstaller como sidecar da aplicação desktop.

## Responsabilidades atuais

- executar os motores de transcrição e emitir progresso por NDJSON;
- preservar os ficheiros `raw` e `clean` e validar cobertura, timestamps e repetições;
- gerir credenciais pelo Windows Credential Manager;
- guardar definições e escolher entre SQLite local e PostgreSQL administrativo;
- manter o túnel SSH persistente quando o modo VPS está ativo;
- servir Biblioteca, identidade local, administração e Data Studio ao shell Tauri;
- chamar a API central HTTPS para recuperação de senha, MFA, telemetria e suporte.

O worker não é um servidor HTTP local. O desktop lança processos controlados e troca payloads por stdin/stdout; operações longas emitem eventos NDJSON.

## Estrutura principal

- `transcription/assemblyai.py` — motor principal para arquivos, AssemblyAI Universal-3.5 Pro.
- `transcription/whisper_openai.py` — alternativa económica/monolingue.
- `transcription/deepgram.py` — Nova-3, alternativa e candidato futuro a baixa latência.
- `transcription/gpt4o_openai.py` — implementação de referência, não recomendada para arquivos longos.
- `transcription/audio_chunks.py` e `transcript_utils.py` — áudio, timestamps e validação.
- `transcription/paths.py` — destino local e preferências de armazenamento.
- `transcription/credentials.py` — integração com Windows Credential Manager.
- `transcription/db.py` — SQLite/PostgreSQL, Biblioteca, histórico e auditoria.
- `transcription/accounts.py` e `oauth.py` — contas e login social.
- `transcription/data_studio.py` — catálogo, consultas protegidas, SQL Editor e Saved Queries.
- `transcription/api_client.py` — cliente HTTPS da API central.
- `transcription/cli.py` — contrato de entrada do sidecar.

## Segurança e privacidade

- Chaves nunca são passadas por argumentos.
- Payloads sensíveis da UI seguem por stdin.
- Vídeo permanece no caminho original.
- Áudio só vai a um motor cloud por ação explícita.
- O arquivo local é gravado antes da escrita best-effort no banco.
- Edição da Biblioteca altera apenas o `clean`; o `raw` permanece imutável.
- Operações administrativas revalidam o ator e, quando exigido, a sessão MFA.
- Data Studio compõe identificadores pelo driver, parametriza valores, mascara colunas protegidas e confirma mutações por hash do plano.

## CLI NDJSON

Exemplos básicos em desenvolvimento:

```powershell
python -m transcription.cli engines
python -m transcription.cli transcribe --engine assemblyai --file "C:\gravacoes\reuniao.mp4"
python -m transcription.cli get-settings
python -m transcription.cli list-keys
python -m transcription.cli db-check --mode local
```

Os grupos de comandos atuais abrangem:

- motores, transcrição, destino e definições;
- credenciais;
- SQLite/PostgreSQL e túnel persistente;
- Biblioteca e migrações;
- contas, OAuth e administração;
- Data Studio;
- recuperação de senha e MFA central;
- telemetria;
- suporte.

O comando `transcribe` emite `start`, zero ou mais eventos `progress` e `result` ou `error`. O stdout permanece reservado a JSON/NDJSON; mensagens internas seguem para stderr.

## Empacotamento e testes

```powershell
.\build_worker.ps1
python -m unittest discover -s tests
```

`build_worker.ps1` gera o sidecar onedir e copia o recurso necessário para o bundle Tauri. O formato onedir evita a descompactação repetida e a latência de um executável onefile em cada operação curta.

O estado validado mais recente e os resultados dos testes ficam em [`docs/PROJECT_CONTEXT.md`](../../docs/PROJECT_CONTEXT.md).
