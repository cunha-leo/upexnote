# Prompt de retomada — colar na abertura do novo chat

> Substitui o `PROMPT_RETOMADA_2026-08-07.md`. A disciplina de leitura (Etapas 1 a 5) é idêntica; o que mudou é a Etapa 6 — o estado real depois da sessão de 08/08/2026, em que o worktree foi sincronizado, os documentos LIFE subiram de versão e duas frentes novas foram registradas.

```text
Você está continuando um chat anterior (Leonardo Cunha).

LEI ABSOLUTA DESTA SESSÃO — não é sugestão, não é boa prática, é regra indiscutível:
Antes de propor, implementar ou responder qualquer coisa sobre a tarefa, você tem que ler cada documento listado abaixo INTEIRO, do início ao fim, linha por linha, e absorver e entender o conteúdo de verdade — não é permitido abstrair, resumir por cima, pular seção, selecionar só o que parece relevante, ou parar antes do fim porque o arquivo é longo. Isso vale para TODOS os documentos, sem exceção nenhuma.

Um checklist marcado como "lido integralmente" sem prova real não vale nada. Cada item só pode ser marcado como concluído com a prova descrita na ETAPA 5. Sem prova, o item fica como "não concluído", mesmo que você "ache" que leu.

Se a ferramenta de leitura cortar o arquivo em partes, continue automaticamente na próxima parte, exatamente de onde parou, até cobrir 100% das linhas, sem lacunas e sem duplicações.

ORDEM OBRIGATÓRIA DE LEITURA:

ETAPA 1 — Camada humana e decisória (LIFE), pasta do Google Drive "03-Life\00- Manifesto&Decisions"
1. Leia integralmente o `AGENTS.md` dessa pasta e execute o protocolo de inicialização LIFE nele descrito, incluindo a seção 8.1 de validação visual de documentos.
2. Localize a versão mais alta de cada documento na pasta real e leia cada um INTEIRO, nesta ordem:
   a. Dossiê/Manifesto LIFE — linha de base em 08/08/2026: v1.2 (81 páginas). Ler todas as seções e todos os apêndices, incluindo a Adenda G.
   b. Contexto Vivo de Decisão — linha de base em 08/08/2026: v2.9 (88 páginas). Ler todas as partes, I a IX, todos os RDs em sequência, matriz de cenários e catálogo de fontes.
   c. Fio Condutor — Objetivo Central LIFE v1.0 — documento curto, ler até a última linha.
3. Não trate mudança de foco entre frentes de vida como desvio de escopo — o Fio Condutor explica por que são a mesma busca por renda própria e liberdade geográfica de 100%.

ETAPA 2 — Camada técnica UpexFlow/UpexNote
4. Leia integralmente `docs/CONTEXT_ORCHESTRATION.md` e siga suas coordenadas, incluindo a seção 9.1 (protocolo obrigatório de renderização documental) e a regra de confronto com o Git.
5. Leia INTEIRO: `AGENTS.md` da raiz; `docs/PROJECT_CONTEXT.md`; `docs/FEATURE_VALIDATION_AND_ROADMAP.md`.

ETAPA 2.5 — Documentação visual/funcional (Google Drive, "Product Strategy & Validation")
   a. `UpexNote_CONTINUIDADE_DOCUMENTACAO_VISUAL.md` (também versionado na raiz do repositório);
   b. `UpexNote_Documentacao_Funcional_Visual_v1.0_FINAL` (DOCX, 95 páginas, 65 figuras). Atenção: o nome diz v1.0_FINAL, a versão interna diz v0.1 — é uma consolidação parcial, não um aceite fechado.

ETAPA 3 — Documentos de domínio obrigatórios da frente ativa (ADF-01/ADF-02)
6. `docs/UX_PRODUCT_STANDARD.md`, `docs/ARCHITECTURE.md`, `docs/PRODUCT.md`, `docs/AI_MEDIA_EVOLUTION.md` — todos inteiros. A próxima fatia é 100% de tela, portanto o UX_PRODUCT_STANDARD é central, não acessório.
7. Se a tarefa tocar outro documento especializado, leia-o antes de responder.

ETAPA 4 — Confronto com o estado real
8. `git status --short`, `git log --oneline -20`, `git branch -vv`, estrutura de `apps/`, `services/`, `docs/`. Se a branch estiver `behind`, ler as versões de `origin/main` antes de assumir o conteúdo local.

ETAPA 5 — Prova de leitura (obrigatória, item por item)
Para cada documento: total de linhas (ou páginas); as faixas efetivamente lidas, somando o arquivo inteiro sem buracos; e uma citação literal curta do primeiro terço, uma do meio e uma do último terço.

ETAPA 6 — Onde este chat parou (contexto operacional, não substitui a leitura acima)

9. FRENTE ATIVA: ADF-01 — Structured Document Generation, status `In progress`. O passo 1 (backend do worker) está entregue, testado com transcripts reais e publicado em `origin/main`. O PRÓXIMO PASSO MATERIAL é o passo 2, que é a UI, na ordem escrita no roadmap: (1) ponte Rust→worker em `apps/desktop/src-tauri/src/main.rs` para `format-engines`, `document-generate`, `document-item` e `document-delete`, com `async` + `spawn_blocking`; (2) botões "Documento formatado" e "Estudo" na Biblioteca e no fim do Transcribe, com microcopy de incentivo, ícones Lucide e textos nos 3 idiomas em `i18n.ts`; (3) leitor do documento em SÓ-LEITURA consumindo `document-item`, desenhando os blocos por `block_type` mais o glossário; (4) motor padrão em Configurações + popup de primeira vez. Só depois começa a ADF-02. A fatia termina com build, versão nova e instalador.

10. DECISÃO EM ABERTO, é do Leonardo: "Documento formatado" e "Estudo" são dois botões separados, ou um botão único "Formatar" com os perfis dentro? As decisões de 06/08/2026 registram as duas formulações e não convergem. Não bloqueia começar pelos pontos 1 e 3.

11. RESOLVIDO, não reabrir: a antiga pendência "confirmar limite de contexto e rate limit por provedor" está fechada desde 07/08/2026 — decidiu-se não fazer chunking nesta etapa, porque os transcripts reais (~5 a ~20 min) ficam muito abaixo da janela de contexto dos 6 provedores.

11-B. ESTADO EXATO NO FIM DE 08/08/2026 (handoff para o Codex ou para a próxima IA).
    O QUE ESTÁ FEITO E PUBLICADO em origin/main: ponte Rust para os comandos de documento (2314418); library_item passa a devolver os documentos gerados do transcript (1772b78); leitor DocumentReader.tsx em só leitura (bca80d3); versão 0.29.0 (d736ccc); documentação promovida (f5c3c15). Todos os builds passaram: cargo check limpo, tsc --noEmit exit 0, vite build verde, Tauri/NSIS concluído.
    O QUE FALTA, POR ORDEM: (1) VALIDAÇÃO VISUAL, que é a única coisa a bloquear a promoção a `Validated` — instalar o instalador VÁLIDO de 58.410.023 bytes (SHA-256 A0F52AA1D589959EFBE2186CD6E04328E2EE8C6ED0AC370A80A38E4CF7465023), abrir a Biblioteca no transcript #23, que tem o documento #9, e confirmar que a faixa "Documentos gerados" aparece abaixo dos badges e que o leitor desenha blocos e glossário; (2) escrever no docs/UX_PRODUCT_STANDARD.md os dois padrões novos que esta fatia criou e que ele ainda não descreve — o nível de navegação "detalhe -> artefacto derivado" com voltar para a origem, e os componentes da faixa de chips e dos pares campo/valor que empilham em janela estreita; isto foi deixado de fora de propósito, para não canonizar um layout antes de alguém o ver; (3) pontos 2 e 4 do passo 2 do ADF-01 — botão "Formatar" com os perfis dentro, eventos de progresso pelo canal document://event, e motor padrão em Configurações com popup de primeira vez.
    ARMADILHA DE BUILD, custou um ciclo inteiro em 08/08/2026: `npm run tauri build` NÃO reempacota o worker Python. O primeiro instalador da 0.29.0 saiu com o worker de 25/07 e a funcionalidade simplesmente não aparecia — sintoma silencioso, nada falha. Se a fatia tocar em services/worker/, correr primeiro `powershell -ExecutionPolicy Bypass -File services\worker\build_worker.ps1` e só depois `npm.cmd run tauri build`, e conferir a data de apps/desktop/src-tauri/worker/upexnote-worker.exe antes de instalar.
    FACTO JÁ CONFIRMADO CONTRA O POSTGRES REAL, não repetir a investigação: documents.structured_documents tem 9 linhas — documentos 1 a 8 no transcript #21, documento 9 no #23. Os contadores do Explorer do Data Studio mostravam 0 para essa tabela; são estimativas do Postgres, não contagens, não confiar neles.

12. ESTADO DO REPOSITÓRIO EM 08/08/2026: o worktree local estava dois commits atrás de `origin/main` e o `AGENTS.md` da raiz havia sido sobrescrito por uma cópia antiga do AGENTS.md do LIFE, sem a seção 8.1. Foi feito stash do AGENTS.md sobrescrito e `git pull --ff-only` até `43d4175`. Os ~28 arquivos que apareciam como modificados eram artefato de fim de linha do mount Linux, não alteração real; vistos nativamente do Windows a árvore estava limpa. LIÇÃO PERMANENTE: confrontar com `origin/main` antes de tratar o arquivo local como canônico.

13. FRENTES DE VIDA NOVAS (contexto, não ação técnica aqui): Career & Mobility ganhou frente própria com `PROMPT_START_CAREER_MOBILITY.md`; MKD tem `PROMPT_START_MKD.md`. Ambos na mesma pasta canônica e compartilhando o mesmo Bloco 1 LIFE. O visto D3 avançou para análise na Embaixada de Portugal em Brasília. Está tudo registrado na Parte IX do Contexto Vivo v2.9.

14. FERRAMENTA (se você for o Claude em Cowork): o plugin GitKraken expõe `git_push`, `git_status`, `git_commit`, `git_add`, `git_pull`, `git_stash` etc., e eles rodam na máquina do Leonardo com as credenciais dele — passe o caminho Windows `C:\Users\cunha\Projects\upexflow\upexnote`. O `bash` do Cowork é um contêiner Linux remoto sem credencial de GitHub. Importante: o mount do Cowork bloqueia `unlink`, então `git checkout`, `git pull` e `rm` falham por lá — use o plugin. Procure as ferramentas disponíveis antes de declarar incapacidade.

15. Existe uma pasta `_to_delete/2026-08-08/` na raiz do repositório com backups da limpeza (AGENTS.md sobrescrito, cópias antigas de handoff e do CONTINUIDADE). Ela é untracked e pode ser apagada pelo Leonardo quando ele quiser. Nunca use `git add -A` neste repositório — sempre arquivos explícitos.

16. Regra de trabalho permanente: commit não basta. Toda entrega tem que atualizar também `PROJECT_CONTEXT.md` (Registro + Estado atual), `FEATURE_VALIDATION_AND_ROADMAP.md` (estado da frente) e qualquer documento especializado afetado. Documentação desatualizada é considerada entrega incompleta.
```
