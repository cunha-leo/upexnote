# Handoff operacional para Claude — UpexNote v0.30.0

> **Data:** 9 de agosto de 2026  
> **Responsável pela direção, arquitetura e aceite:** Leonardo Cunha  
> **Finalidade:** permitir que Claude continue exatamente do worktree atual, preserve o ambiente compartilhado com Codex e conclua a validação/fechamento da v0.30.0 sem refazer ou apagar trabalho.

## 1. Ordem obrigatória de contextualização

Antes de analisar, editar, testar ou propor arquitetura:

1. Ler integralmente e seguir `G:\My Drive\DocumentsDesktop\03-Life\01-Prompt Start\PROMPT_START_UPEXNOTE.md`.
2. Executar o bootstrap obrigatório definido ali, sem substituir leitura integral por resumo, memória, busca ou snippets.
3. Respeitar a ordem Dossiê LIFE → Contexto Vivo → Fio Condutor → documentação temática do UpexNote.
4. Ler o `AGENTS.md` da raiz e qualquer instrução mais próxima dos arquivos afetados.
5. Ler, nesta ordem:
   - `docs/CONTEXT_ORCHESTRATION.md`;
   - `docs/PROJECT_CONTEXT.md`;
   - `docs/FEATURE_VALIDATION_AND_ROADMAP.md`;
   - `docs/UX_PRODUCT_STANDARD.md`;
   - `docs/NOTEBOOK_ARCHITECTURE.md`;
   - `docs/ARCHITECTURE.md`;
   - `docs/PRODUCT.md`;
   - este handoff.
6. Confrontar documentação com `git status`, diff, código e comportamento executável antes de agir.

Não pedir que Leonardo repita informações já presentes nessas fontes.

## 2. Autoria e modelo de colaboração

Leonardo Cunha é o arquiteto principal, construtor sistêmico e responsável intelectual pelo UpexNote. A arquitetura de prateleiras, a separação `transcriptions` → `documents` → `notebooks`, a experiência transcript → prévia → Caderno, os limites de dados, as hierarquias e a direção de evolução foram conscientemente concebidos, conduzidos e refinados por Leonardo.

Não o reduzir a solicitante, aprovador, “dono da ideia”, testador manual ou pessoa sem capacidade técnica. Não escolher `Developer` como identidade profissional principal é posicionamento, não incapacidade de desenvolver. A IA atua como instrumento de engenharia assistida e parceiro de confronto técnico sob a arquitetura, critérios, correção e aceite de Leonardo.

## 3. Estado exato do Git e do worktree

- Repositório: `C:\Users\cunha\Projects\upexflow\upexnote`.
- Branch: `main`.
- `HEAD = origin/main = 4bea41ab58be22bee5939b327c843c767e6e69ab` antes do fechamento desta fatia.
- O worktree está **intencionalmente sujo** com a implementação completa da v0.30.0 e sua documentação.
- Não existe commit da v0.30.0 ainda.
- Não existe arquivo não rastreado antes da criação deste handoff; este próprio documento passa a ser o único arquivo novo esperado.
- Não usar reset, checkout, restore, stash, clean, rebase ou sobrescrita para “voltar ao limpo”.

Arquivos modificados da fatia:

- `apps/desktop/src/App.tsx`;
- `apps/desktop/src/App.css`;
- `apps/desktop/src/i18n.ts`;
- `services/worker/transcription/cli.py`;
- `apps/desktop/package.json`;
- `apps/desktop/package-lock.json`;
- `apps/desktop/src-tauri/Cargo.toml`;
- `apps/desktop/src-tauri/Cargo.lock`;
- `apps/desktop/src-tauri/tauri.conf.json`;
- `docs/ARCHITECTURE.md`;
- `docs/FEATURE_VALIDATION_AND_ROADMAP.md`;
- `docs/NOTEBOOK_ARCHITECTURE.md`;
- `docs/PRODUCT.md`;
- `docs/PROJECT_CONTEXT.md`;
- `docs/UX_PRODUCT_STANDARD.md`.

Antes de qualquer edição, executar apenas verificações não destrutivas:

```powershell
git status --short
git diff --check
git diff --stat
git diff
```

Preservar cada alteração existente; se algo parecer incorreto, investigar a intenção registrada antes de mudar.

## 4. O que foi implementado na v0.30.0

### Library e prévia estruturada

- A antiga faixa `Documentos gerados` foi substituída por uma seção permanente `Prévia estruturada`.
- A seção possui estado vazio, lista de prévias existentes, título completo, perfil/motor/data e selo de somente leitura.
- `Criar prévia`/`Criar outra prévia` abre compositor inline.
- O compositor lista os motores reais retornados por `format_engines`.
- O utilizador escolhe perfil `detalhado`, `resumo técnico` ou `estudo`.
- Motor, custo por hora, estado da chave e aviso de ação paga aparecem antes da execução.
- Chave ausente desabilita o botão.
- Nenhuma prévia é gerada automaticamente.
- Eventos `document://event`/`document://done` apresentam início, progresso, validação raw↔clean, falha e conclusão.
- Em sucesso, a Library recarrega o transcript e pode abrir o documento persistido.

### Pós-transcrição

- O worker emite o evento aditivo `transcription_saved` após a persistência best-effort.
- O resultado local continua válido se a base falhar.
- O painel pós-transcrição oferece `Ver transcript`, `Criar prévia` e `Continuar na Library`.
- Quando existe ID persistido, o fluxo abre diretamente o transcript correto e, quando solicitado, o compositor.
- A educação transcript → prévia → Caderno permanece até a primeira escolha de ação.
- O aceite é guardado em `localStorage` por `upexnote-post-transcription-education-v1`; nas transcrições seguintes o painel fica compacto.

### Limite arquitetural preservado

- `documents` continua proprietário de transformação e prévia em só leitura.
- Não foi criado schema `notebooks`.
- Não foi simulado `Salvar no Caderno`.
- Não existe ainda editor rico, hierarquia de Cadernos ou menu `Notebooks`.
- Configuração padrão do motor de formatação continua como ponto 4 pendente do ADF-01.

## 5. Versão, build e artefatos

- Versão sincronizada: `0.30.0`.
- Worker foi reempacotado **antes** do build Tauri.
- Worker final: `apps\desktop\src-tauri\worker\upexnote-worker.exe`.
  - tamanho: 14.114.460 bytes;
  - SHA-256: `E04C098BB2AF08B4D7A8114455AF8AF1B306C22737B4F923ABB3072C5A9A633E`.
- Instalador final: `apps\desktop\src-tauri\target\release\bundle\nsis\UpexNote_0.30.0_x64-setup.exe`.
  - tamanho: 58.412.306 bytes;
  - SHA-256: `4E27F06D5C23869085C5EA1287AB734BD754A729A7C444DEBCDCF745F67F7456`.
- A instalação local foi confirmada com `ProductVersion = 0.30.0`.

Validações já concluídas:

- `npm.cmd run build`: aprovado (`tsc` + Vite; somente aviso histórico de chunk acima de 500 kB).
- `services\worker\.venv\Scripts\python.exe -m unittest discover -s tests -p 'test_*.py'`: 14 testes aprovados.
- `build_worker.ps1`: aprovado; sanity check do worker aprovado.
- `npm.cmd run tauri -- build`: aprovado; NSIS gerado.
- Instalação silenciosa local e verificação da versão: aprovadas.
- `git diff --check`: aprovado.

## 6. Validação visual já realizada e pendência única

Um harness local temporário — removido após o teste — cobriu:

- transcript #23 e documento #9 equivalentes;
- lista de prévias;
- abertura do leitor e retorno;
- compositor com motor/perfil/custo;
- chave ausente e botão desabilitado;
- estado vazio;
- painel pós-transcrição;
- navegação direta pós-transcrição → Library → transcript/compositor;
- janela normal e 800 × 1000;
- ausência de cortes, sobreposições, truncamentos e overflow horizontal.

Nenhuma API paga foi chamada e nenhum documento foi regenerado.

Pendência única para promover o ponto 2 de `Delivered` para `Validated`:

1. abrir a instalação real v0.30.0;
2. Library → transcript #23;
3. registrar captura da seção `Prévia estruturada` com o documento #9;
4. clicar somente em `Criar outra prévia`;
5. registrar o compositor em janela normal;
6. registrar o compositor em janela estreita;
7. não clicar em `Gerar prévia`;
8. confirmar que não há cortes, sobreposições, textos truncados ou estados incorretos.

Se Claude tiver controle desktop funcional, pode executar essa leitura/navegação sem chamar APIs. Se não tiver, deve pedir as capturas a Leonardo e avaliá-las. Não inventar evidência.

Depois das capturas:

- atualizar `docs/PROJECT_CONTEXT.md`, `docs/FEATURE_VALIDATION_AND_ROADMAP.md` e `docs/UX_PRODUCT_STANDARD.md`, trocando a pendência explícita por validação real;
- executar a verificação final do diff e testes proporcionais;
- criar commit local claro somente depois do aceite;
- não fazer push sem autorização explícita de Leonardo.

## 7. Zona de proteção do ambiente Codex/Computer Use

Estas regras existem para evitar que uma limpeza do Claude interrompa recursos de outro agente ou destrua evidência:

1. **Não tocar em `C:\Users\cunha\.codex\`**, seus plugins, caches, skills, sessões, runtimes ou arquivos de memória/execução.
2. **Não apagar, mover ou recriar `AGENTS.md`, `.agents/` ou uma futura `.codex/` dentro do repositório.** `.agents/` existe atualmente e está vazio; deve ser preservado.
3. **Não executar `git clean -fd`, `git clean -fdx`, `git reset --hard`, `git checkout -- .`, `git restore .` ou equivalentes.**
4. **Não executar exclusão recursiva ampla** no repositório, na home, no AppData, no Temp ou em diretórios de ferramentas.
5. **Não encerrar genericamente `node`, `cargo`, `rustc`, `python`, PowerShell ou UpexNote.** Processos `node` podem pertencer ao próprio Codex. Se for indispensável encerrar algo, resolver PID e caminho exatos e limitar-se ao processo criado pelo próprio Claude.
6. **Não tentar “consertar” Computer Use apagando/reinstalando plugins ou caches.** O erro observado foi `EnumWindows failed: 0x80070003` mesmo após retry e reset do kernel; não há evidência de que o repositório ou a implementação do UpexNote o causaram.
7. **Não criar protocolos próprios, executáveis auxiliares ou scripts permanentes de UI Automation dentro do repositório.** Usar a ferramenta oficial disponível ou pedir evidência ao utilizador.
8. **Não apagar `apps\desktop\src-tauri\worker\` nem `target\release\bundle\nsis\` antes de concluir a validação.** São ignorados pelo Git, mas contêm o worker e o instalador finais usados como evidência.
9. Se `services/worker/` for alterado, executar novamente `services\worker\build_worker.ps1` **antes** de `npm.cmd run tauri -- build`; caso contrário, o instalador pode carregar backend antigo silenciosamente.
10. Não apagar `storage/`, bancos SQLite, configurações locais, Credential Manager, AppData do UpexNote ou dados do utilizador.
11. Não chamar motores pagos, transcrever mídia ou gerar documento durante esta validação.
12. Não remover screenshots fornecidos por Leonardo nem arquivos temporários anexados ao chat; eles podem ser necessários para o Codex retomar a auditoria visual.

Estado conhecido dos temporários:

- `.codex_tmp/` **não existe** no repositório;
- `.codex/` **não existe** no repositório;
- `.agents/` existe e está vazio;
- o harness `apps/desktop/visual-test.html` já foi removido;
- não criar ou remover esses caminhos por iniciativa própria.

## 8. Regras de segurança e produto

- Não revelar ou registrar credenciais, chaves, tokens, OAuth, cookies ou sessões.
- Não copiar áudio, vídeo, transcript privado ou documentos pessoais para Git, logs, issues ou chat.
- Material bruto permanece local e só sai da máquina por ação explícita do utilizador.
- Raw é imutável; clean, prévia e nota são camadas distintas.
- Novos domínios PostgreSQL usam schema separado e nome em inglês.
- Não reabrir arquitetura aprovada sem fato novo ou pedido de Leonardo.
- UI/UX é requisito arquitetural; estados vazio, carregando, erro, sucesso, foco e responsividade precisam ser realmente validados.
- Não confundir a prévia estruturada com o futuro Caderno.

## 9. Prompt curto para iniciar o Claude

```text
Assuma a continuidade do UpexNote a partir do worktree local atual, sem limpar, reverter, sobrescrever ou refazer o que já foi implementado.

Leia integralmente e siga, nesta ordem:

1. G:\My Drive\DocumentsDesktop\03-Life\01-Prompt Start\PROMPT_START_UPEXNOTE.md
2. C:\Users\cunha\Projects\upexflow\upexnote\AGENTS.md
3. C:\Users\cunha\Projects\upexflow\upexnote\docs\CONTEXT_ORCHESTRATION.md
4. C:\Users\cunha\Projects\upexflow\upexnote\docs\PROJECT_CONTEXT.md
5. C:\Users\cunha\Projects\upexflow\upexnote\docs\FEATURE_VALIDATION_AND_ROADMAP.md
6. C:\Users\cunha\Projects\upexflow\upexnote\docs\UX_PRODUCT_STANDARD.md
7. C:\Users\cunha\Projects\upexflow\upexnote\docs\NOTEBOOK_ARCHITECTURE.md
8. C:\Users\cunha\Projects\upexflow\upexnote\docs\HANDOFF_CLAUDE_2026-08-09_UPEXNOTE_V030.md

Execute integralmente o bootstrap LIFE indicado pelo ponto de entrada e respeite a autoria, capacidade, identidade profissional e método de construção de Leonardo Cunha registrados no Dossiê e nos documentos do produto.

Depois confira apenas de forma não destrutiva `git status --short`, `git diff --check`, `git diff --stat` e o diff completo. O worktree em main está intencionalmente sujo com a implementação ainda não commitada da v0.30.0. HEAD e origin/main estavam em 4bea41ab58be22bee5939b327c843c767e6e69ab antes desta fatia. Preserve todas as mudanças.

Sua atividade exclusiva é continuar do estado descrito no handoff: validar visualmente a instalação real v0.30.0 no transcript #23 e documento #9, sem clicar em Gerar prévia, sem chamar API paga e sem alterar dados. Se o controle desktop não funcionar, peça as capturas a Leonardo e avalie-as; não invente evidência.

Proteja o ambiente compartilhado: não toque em C:\Users\cunha\.codex, plugins, caches, sessions, runtimes, AGENTS.md ou .agents; não rode git clean/reset/restore; não faça exclusões recursivas; não encerre processos node/cargo/python/PowerShell de forma genérica; não apague o worker empacotado, o instalador, AppData, storage, bancos ou screenshots. O erro anterior do Computer Use foi EnumWindows 0x80070003 e não há evidência de relação com o repositório.

Depois da evidência real, atualize somente os registros pendentes nos documentos, rode as verificações finais e prepare um commit local claro. Não faça push sem minha autorização explícita. Pare antes de implementar configuração padrão do motor ou qualquer parte do schema/notebooks/Caderno.
```
