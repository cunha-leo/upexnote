# UpexNote Worker

Worker local responsável por encapsular os pipelines Python já validados:

- AssemblyAI Universal-3.5 Pro;
- OpenAI whisper-1;
- Deepgram Nova-3;
- Whisper local;
- validação de timestamps e alucinações;
- extração temporária de áudio.

Os scripts do protótipo serão migrados de forma incremental, preservando os parâmetros e as proteções empiricamente validadas.
