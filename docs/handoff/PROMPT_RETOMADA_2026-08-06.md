# Prompt de retomada — colar na abertura do novo chat

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
   a. `docs/UX_PRODUCT_STANDARD.md` — padrão de interface/UX do UpexNote, obrigatório para qualquer frente com impacto de tela ou fluxo (ADF-01 e ADF-02 têm);
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
9. A frente ativa é a ADF-01 — Structured Document Generation, status `Ready`, com todas as decisões de UX, modelo de dados, fluxo de execução na tela de Transcribe e o benchmark de motores de formatação já fechadas (05–06/08/2026). ADF-02 (Rich Study Workspace) está `Approved`, acoplada.
10. Pendente antes de codar: confirmar limite de contexto/tokens e rate limit por provedor de formatação (DeepSeek, Grok, OpenAI, Anthropic, Gemini), considerando reuniões longas — cenário-teste até 1h30–2h, além dos ~20 min já testados. Esse é o próximo passo material, não uma sugestão entre várias.
11. Fora do UpexNote: a frente paralela de mini apps/micro-SaaS (RD-20 cancelado e concluído, RD-22 com compra decidida) já está fechada no Contexto Vivo — é contexto de vida, não exige ação técnica aqui.

ETAPA 7 — Resposta final
Só depois do checklist da Etapa 5 completo, com prova, para todos os documentos, responda com: versões carregadas, estado técnico atual (versão/commit), frente ativa e status, o pendente da Etapa 10, e pergunte apenas o que for material e ainda não resolvido. Não implemente nada nesta primeira resposta — só confirme que está pronto, com as provas de leitura, e aguarde a próxima instrução.
```
