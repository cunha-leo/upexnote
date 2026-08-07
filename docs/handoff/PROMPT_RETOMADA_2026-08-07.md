# Prompt de retomada — colar na abertura do novo chat

> Substitui o `PROMPT_RETOMADA_2026-08-06.md`. A disciplina de leitura (Etapas 1 a 5) é idêntica; o que mudou é a Etapa 6 — o estado real depois da sessão de 06–07/08/2026.

```text
Você está continuando um chat anterior (Leonardo Cunha).

LEI ABSOLUTA DESTA SESSÃO — não é sugestão, não é boa prática, é regra indiscutível:
Antes de propor, implementar ou responder qualquer coisa sobre a tarefa, você tem que ler cada documento listado abaixo INTEIRO, do início ao fim, linha por linha, e absorver e entender o conteúdo de verdade — não é permitido abstrair, resumir por cima, pular seção, selecionar só o que parece relevante, ou parar antes do fim porque o arquivo é longo. Isso vale para TODOS os documentos, sem exceção nenhuma. É a prioridade real desta sessão, acima de qualquer pressa em responder.

Um checklist marcado como "lido integralmente" sem prova real não vale nada — já aconteceu de você (ou outra instância sua) declarar leitura integral no checklist e, na prática, não ter lido tudo (pulou o documento de padrão de interface do UpexNote inteiro, não leu o Fio Condutor até o fim, deixou MDs de domínio de fora). Por isso, a autodeclaração sozinha não é mais aceita — cada item do checklist final só pode ser marcado como concluído se vier acompanhado da prova descrita na ETAPA 5. Sem prova, o item fica como "não concluído", mesmo que você "ache" que leu.

Se a ferramenta de leitura cortar o arquivo em partes (paginação, limite de linhas), continue automaticamente na próxima parte, exatamente de onde parou, até cobrir 100% das linhas do arquivo, sem lacunas, sem duplicações e sem pedir autorização no meio.

Não vale reutilizar resumo, memória, busca direcionada por palavra-chave ou conhecimento aproximado de sessão anterior no lugar da leitura. "Li a maior parte", "li o suficiente para a tarefa" ou "essa parte não parecia necessária" não são respostas aceitáveis — só existe leitura integral comprovada ou leitura não concluída (e leitura não concluída deve ser dita com todas as letras, nunca disfarçada).

ORDEM OBRIGATÓRIA DE LEITURA:

ETAPA 1 — Camada humana e decisória (LIFE), pasta do Google Drive "00- Manifesto&Decisions"
1. Leia integralmente o arquivo `AGENTS.md` dessa pasta e execute o protocolo de inicialização LIFE nele descrito.
2. Localize a versão mais alta de cada um destes três documentos na pasta real (não assuma a linha de base citada dentro do próprio AGENTS.md — ela pode estar desatualizada) e leia cada um INTEIRO, nesta ordem, do início ao fim, sem pular nenhuma seção ou apêndice:
   a. Dossiê/Manifesto LIFE (Dossie_Leonardo_Cunha_LIFE_v<versão mais alta>.docx) — todas as seções e todos os apêndices, até a última linha;
   b. Contexto Vivo de Decisão (Contexto_Vivo_Decisao_Portugal_Brasil_Leonardo_v<versão mais alta>.docx) — todas as partes do documento até a última linha, incluindo matriz de cenários, catálogo de fontes e todos os registros de decisão (RDs) em sequência, não localizados por busca de palavra-chave;
   c. Fio Condutor — Objetivo Central LIFE (Fio_Condutor_Objetivo_Central_v<versão mais alta>.md) — até a última linha. Este documento é curto; não há justificativa nenhuma para lê-lo parcialmente.
3. Não trate mudança de foco entre frentes de vida (UpexNote, ARAMIS, LMSC, UNB, cursos avaliados, busca de vaga) como desvio de escopo — o Fio Condutor explica por que são a mesma busca por renda própria e liberdade geográfica de 100%.

ETAPA 2 — Camada técnica UpexFlow/UpexNote
4. Leia integralmente `docs/CONTEXT_ORCHESTRATION.md` no repositório e siga suas coordenadas.
5. Leia INTEIRO, do início ao fim, sem pular nada:
   a. `AGENTS.md` da raiz do repositório;
   b. `docs/PROJECT_CONTEXT.md`;
   c. `docs/FEATURE_VALIDATION_AND_ROADMAP.md`.

ETAPA 2.5 — Documentação visual/funcional do UpexNote (Google Drive)
Na pasta do Google Drive `G:\My Drive\DocumentsDesktop\03-Life\04-Active Ventures\UpexFlow\UpexNote\Product Strategy & Validation`, leia INTEIRO, do início ao fim, sem pular nada:
   a. `UpexNote_CONTINUIDADE_DOCUMENTACAO_VISUAL.md`;
   b. `UpexNote_Documentacao_Funcional_Visual_v1.0_FINAL` (o Google Doc/docx principal de documentação visual e funcional — é o mais importante dos dois e não pode ficar de fora).
Confira se existe versão mais alta que `v1.0_FINAL` nessa mesma pasta antes de ler; se houver, leia a mais recente. Esses dois documentos registram a continuidade visual/funcional do produto e são parte da leitura obrigatória, não um anexo opcional.

ETAPA 3 — Documentos de domínio obrigatórios da frente ativa (ADF-01/ADF-02)
6. O próprio `FEATURE_VALIDATION_AND_ROADMAP.md` lista os documentos obrigatórios da ADF-01. Leia TODOS eles inteiros, sem escolher apenas os que parecem mais óbvios:
   a. `docs/UX_PRODUCT_STANDARD.md` — padrão de interface/UX do UpexNote, obrigatório para qualquer frente com impacto de tela ou fluxo (a próxima fatia é 100% de tela, portanto este documento é central, não acessório);
   b. `docs/ARCHITECTURE.md`;
   c. `docs/PRODUCT.md`;
   d. `docs/AI_MEDIA_EVOLUTION.md`.
7. Se durante a leitura você identificar que a tarefa toca outro documento especializado (ex.: `SUPPORT_ARCHITECTURE.md`, `DATA_STUDIO_ARCHITECTURE.md`), leia esse também antes de responder — não decida sozinho que está fora de escopo sem justificar.

ETAPA 4 — Confronto com o estado real
8. Depois da leitura documental completa, confronte com o estado real: `git status`, `git log --oneline -20`, estrutura de `apps/`, `services/`, `docs/`.

ETAPA 5 — Prova de leitura (obrigatória, item por item, sem isso o checklist não vale)
Para cada um dos documentos das Etapas 1, 2, 2.5 e 3, ao marcá-lo como lido você precisa apresentar:
- o total de linhas (ou páginas, se for .docx) do arquivo;
- a soma das faixas de linhas efetivamente lidas via ferramenta (ex.: 1–500, 501–1000, 1001–1567), confirmando que a soma cobre o arquivo inteiro sem buracos;
- uma citação literal curta (uma frase, entre aspas) extraída do primeiro terço, uma do meio e uma do último terço do documento — para provar que o conteúdo do meio e do fim foi realmente processado, não só o início.
Se não conseguir apresentar isso para algum documento, ele NÃO pode ser marcado como "lido integralmente" — declare como pendente e continue a leitura antes de responder.

ETAPA 6 — Onde este chat parou (contexto operacional, não substitui a leitura acima)

9. A frente ativa é a ADF-01 — Structured Document Generation. O status mudou de `Ready` para `In progress`: o PASSO 1 (backend do worker) foi entregue, testado com dados reais e publicado em `origin/main` em 07/08/2026. Leia a seção "Passo 1 entregue" e "Passo 2 — próxima fatia" dentro da ADF-01 no roadmap; o Registro 2026-08-07 do `PROJECT_CONTEXT.md` cobre o mesmo do ângulo do contexto vivo.

10. O que já existe e funciona (não reimplementar, não redescobrir):
    - `services/worker/transcription/formatting.py` — os 6 motores de formatação (DeepSeek, Grok, gpt-5-mini, Claude Haiku 4.5, Claude Sonnet 5, Gemini), todos validados com transcripts reais, sem alucinação. Sem motor padrão, por decisão.
    - `services/worker/transcription/doc_validation.py` — gate raw↔clean (heurística v1 por razão de palavras).
    - Schema hub-and-spoke no schema Postgres dedicado `documents` (`documents.structured_documents` + `document_blocks`/`document_glossary`/`document_metrics`/`documents_history`). A migração de `public` para `documents` já foi executada e validada na VPS real. SQLite local não usa schemas — a tradução em `_to_sqlite_sql()` remove o prefixo.
    - Comandos de CLI: `format-engines`, `format`, `document-generate --transcription-id`, `transcribe --format-engine` (encadeado), `document-item --id`, `document-delete --id`, `db-migrate-documents-schema`.
    - Chaves categorizadas por finalidade em `credentials.py` (`KEY_PURPOSES`), pré-requisito da tela de Configurações.

11. PRÓXIMO PASSO MATERIAL — passo 2 do ADF-01, que é a UI. A ordem está escrita no roadmap: (1) ponte Rust→worker em `apps/desktop/src-tauri/src/main.rs` para os comandos de documento, usando `async` + `spawn_blocking` como os comandos `library*` já fazem; (2) botões de entrada na Biblioteca e no fim do Transcribe, com microcopy de incentivo, ícones Lucide e textos nos 3 idiomas em `i18n.ts`; (3) leitor do documento em SÓ-LEITURA, consumindo `document-item` e desenhando os blocos por `block_type` + glossário; (4) motor padrão em Configurações + popup de primeira vez. Só depois disso a ADF-02 (edição) começa — o leitor do ponto 3 é a base sobre a qual o editor cresce. A fatia termina com build, versão nova e instalador.

12. DECISÃO EM ABERTO, é do Leonardo e ninguém deve resolver sozinho: "Documento formatado" e "Estudo" são dois botões separados, ou um botão único "Formatar" com os perfis dentro? As decisões de 06/08/2026 registram as duas formulações em momentos diferentes e não convergem. Não bloqueia começar pelos pontos 1 e 3 do item 11.

13. A pendência antiga "confirmar limite de contexto e rate limit por provedor" está RESOLVIDA e fechada: decidiu-se não fazer chunking/fragmentação nesta etapa, porque os transcripts reais (~5 a ~20 min) ficam muito abaixo da janela de contexto de qualquer um dos 6 provedores. Não reabrir sem motivo novo.

14. A ADF-02 (Rich Study Workspace) continua `Approved` e precisa de especificação para chegar a `Ready` — a lista de capacidades no roadmap é escopo aprovado, não plano de implementação.

15. Sujeira pré-existente na árvore de trabalho, que NÃO é da ADF-01 e continua por decidir: `AGENTS.md` com diff real de ~226 linhas (não escrito nas sessões recentes), `docs/handoff/`, `UpexNote_CONTINUIDADE_DOCUMENTACAO_VISUAL.md` na raiz, e ~20 ficheiros `.fuse_hidden*` em `services/worker/transcription/` (lixo de mount, candidatos a `.gitignore`). Nunca use `git add -A` neste repositório — sempre ficheiros explícitos, ou você arrasta isso para dentro de um commit.

16. FERRAMENTA (se você for o Claude em Cowork): o plugin GitKraken expõe `git_push`, `git_status`, `git_commit`, `git_add`, `git_log_or_diff` etc., e eles rodam na máquina do Leonardo com as credenciais dele — passe o caminho Windows `C:\Users\cunha\Projects\upexflow\upexnote`. O `bash` do Cowork é um contêiner Linux remoto e não tem credencial de GitHub, então `git push` de lá falha. Em 07/08/2026 uma instância anterior afirmou "não consigo fazer push" e fez o Leonardo perder tempo com terminal e Git GUI, enquanto o plugin já estava instalado. Procure as ferramentas disponíveis antes de declarar incapacidade.

17. Regra de trabalho permanente: commit não basta. Toda entrega tem que atualizar também `PROJECT_CONTEXT.md` (Registro + Estado atual), `FEATURE_VALIDATION_AND_ROADMAP.md` (estado da frente) e qualquer documento especializado afetado, para que qualquer IA que pegue o projeto depois saiba exatamente o que foi feito e onde parou. Documentação desatualizada é considerada entrega incompleta.
```
