# UpexNote — Fechamento técnico R03.1 (26/11/2026)

> **Estado:** checkpoint cumulativo FULL de recuperação e entrega do código desktop, com UX das edições Personal e Internal aprovada pelo responsável. Esta nota não significa homologação de todos os modelos em todos os idiomas ou cargas. **Versões executáveis:** Personal `v0.45.0` e Internal `v0.45.0-internal`.

## Alcance entregue

- Edições Personal (local-first, sem comandos administrativos/VPS) e Internal (recursos administrativos sujeitos à autorização). Instaladores e portáteis distintos podem coexistir. O armazenamento SQLite do utilizador é partilhado intencionalmente.
- Catálogo de **13 motores de transcrição em seis provedores**: AssemblyAI (3), OpenAI (4), Deepgram (2), Groq (2), Gemini (1) e xAI/Grok (1).
- Catálogo de **13 modelos de formatação em cinco provedores**: DeepSeek (2), xAI/Grok (2), OpenAI (3), Anthropic (4) e Gemini (2).
- Fluxo aprovado por finalidade: **Provedor → Modelo → descrição dinâmica**, com recomendados em primeiro lugar, outras opções compatíveis disponíveis e informação de custo/limitações e maturidade dos testes. Modelos somente de texto não recebem áudio diretamente sem pipeline STT.
- Credenciais BYOK no Gerenciador de Credenciais do Windows. Presença da chave indica armazenamento, não necessariamente validade. Campo ElevenLabs reservado a voz/VSL futuros, sem execução integrada; OrcaRouter não integra a interface. Groq precisa de chave própria.
- Proteção do RAW imutável; CLEAN, documentos estruturados e notas são camadas derivadas independentes; falhas de autenticação e transcrições vazias não são gravadas como sucesso.
- Na Prévia estruturada da Biblioteca, campo Perfil alinhado aos seletores e dica informativa. **Aprovado visualmente no Personal e Internal**, em capturas e confirmação do responsável de 26/11/2026.

## Evidências disponíveis

- Compilação React/TypeScript/Vite e Tauri/Rust/NSIS nas duas edições; hashes SHA-256 arquivados com os artefactos.
- **46 testes `unittest` do worker aprovados** e **2 testes novos da API FastAPI para UTF-8 aprovados**; verificadores de edição nos workers empacotados aplicaram testes negativos do Personal (comandos administrativos, VPS, modo persistente) e preservaram o Internal.
- Workers empacotados de ambas as edições enumeraram 13 motores STT e 13 de formatação.
- Smokes de áudio curtos com AssemblyAI, OpenAI, Deepgram, Gemini e xAI/Grok; OpenAI GPT-Transcribe e Deepgram Nova-2 também passaram nos workers empacotados de ambas as edições. Nova-2 requer deteção automática do idioma dominante e não substitui Nova-3 para code-switching PT/EN.
- Chaves OpenAI, Deepgram, Anthropic e Gemini renovadas pelo proprietário; verificações HTTP 200; DeepSeek e Grok também com geração API válida. Não registrar valores de chaves no código ou documentação.
- Testes curtos de geração estruturada com GPT-5.4 Nano, Grok 4.3, Claude Haiku 5.5 e Gemini 3.1 Flash Lite, além dos modelos já testados. Não extrapolar resultado curto para transcrições extensas.

## R03.1 — auditoria de pendências

| Referência | Situação em 26/11/2026 |
|---|---|
| SEC-01 isolamento Personal | Testes negativos no worker empacotado, incluindo execução `serve`; flag Internal preservada; sem configuração privada de PostgreSQL no bundle Personal |
| BUG-01 arrays/Markdown na prévia → nota | Conversão de blocos nativos e exportação com testes de listas, Unicode e escapes; não reescreveu notas existentes |
| BUG-02 título do Suporte no tema Nord | CSS ajustado para seguir tema; validação visual específica desse cenário não documentada |
| BUG-03 caracteres corrompidos em mensagem histórica | **Resolvido em produção, 26/11/2026**: um único registro de `support.ticket_descriptions`, confirmado corrompido na origem; corrigido após snapshot privado, com `support.ticket_audit` transacional e leitura de verificação. API e worker passaram testes UTF-8 de regressão. |
| BUG-04 duração inferior a minuto | `fmtDur` mostra segundos para valores abaixo de 60 |
| UX da Biblioteca: seletor Perfil | Aprovada visualmente nas duas edições |

## Limites e próximas validações

- Benchmark de áudios longos, PT-BR/PT-PT/EN/ES mistos, diarização, custo real por token, timestamps, latência e alucinação.
- Modelos Groq ainda sem credencial e sem smoke de produção. Alguns modelos de formatação têm apenas teste JSON curto, não teste completo do documento.
- Dica/campo Perfil aprovados, mas outros temas e a central de suporte específica Nord requerem inspeção direcionada.
- BUG-03 **fechado com evidências**: valor antigo preservado em Recovery privado e auditoria do PostgreSQL; alteração atômica limitada ao chamado histórico `UN-000001`, sem migração em massa. Os novos textos atravessam o cliente worker e a API FastAPI em UTF-8, com testes de regressão. Não aplicar correções globais de codificação.
- Voz/VSL, IA do Caderno, tradução, orquestração e outros provedores são evoluções futuras, não entregas desta versão.
- O modo `Personal` não é atalho para serviços administrativos; a edição `Internal` preserva verificações reais de autorização. Não publicar configs privadas nem reinstalar banco.

**Continuidade:** o arquivo privado `UPEXNOTE-LATEST.zip` na pasta Recovery do projeto mantém os checkpoints R01/R02/R03/R03.1, a documentação funcional visual e benchmarks históricos, a árvore de código correspondente ao release e os instaladores. Não há ingestão LIFE ou exportação de conteúdo do utilizador para o Git.
