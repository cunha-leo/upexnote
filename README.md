# UpexNote

> Transcreva, organize e explore suas conversas.

UpexNote é o produto de transcrição, contexto e estudo do ecossistema UpexFlow.

## Princípios

- Vídeos brutos nunca entram neste projeto: são escolhidos pelo utilizador no momento da transcrição e permanecem no local de origem.
- Código e documentação são versionados no Git privado.
- Transcripts, contextos e exportações podem ser sincronizados pelo Google Drive, mas ficam fora do Git.
- Credenciais ficam exclusivamente no Windows Credential Manager.
- A aplicação será local-first: interface web moderna com um worker local para mídia, transcrição e a futura captura ao vivo no Windows.

## Estrutura

- `apps/desktop` — interface local-first do UpexNote.
- `services/worker` — pipelines locais de mídia e transcrição.
- `docs` — arquitetura, produto e decisões técnicas.
- `storage` — conteúdo gerado pelo utilizador; ignorado pelo Git.

## Estado

Fundação inicial do projeto. Os pipelines de transcrição já validados serão migrados do protótipo anterior para `services/worker` sem alterar os resultados que foram testados.
