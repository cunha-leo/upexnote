# AGENTS.md — UpexNote

> **Regra permanente:** toda documentação gerada ou alterada também deve atualizar o docs.upexflow.com (grupo UpexNote). Leia `00-REGRA-DOCS-UPEXFLOW.md` na raiz do Hub-UpexFlow (Drive) antes de encerrar o trabalho. Não colocar segredos nem valores reais de infraestrutura no docs.

> **Valores reais de infraestrutura:** este repositório público usa marcadores (`<VPS_HOST>`, `<DB_PORT>`, `<SSH_USER>`, `<CHAVE_SSH_VPS>`, `<USER>`, `<LINK_DRIVE_PRIVADO>` etc.). A tabela de equivalência está em `docs/private/INFRA_LOCAL.md`, arquivo local ignorado pelo Git. Antes de operar SSH, banco, caminhos locais ou links do Drive, leia esse arquivo; se não existir, peça ao Leonardo — não invente valores.

Este arquivo tem duas partes, nesta ordem: a **Parte 1** manda carregar o contexto de Leonardo pelo start do UpexNote (Drive); a **Parte 2** traz as regras do repositório. Não pular a Parte 1.

---

# PARTE 1 — CONTEXTO: LER O START DO UPEXNOTE

Antes de qualquer ação neste repositório, abrir e seguir o **`PROMPT_START_UPEXNOTE.md`**, na pasta `01-Prompt Start` do Drive de Leonardo (link em `docs/private/INFRA_LOCAL.md`; use sempre a versão mais alta e ignore a subpasta `old`).

O start é o mapa de entrada: ele manda ler o `AGENTS.md` do protocolo LIFE e o Dossiê LIFE (versão mais alta na pasta Manifesto), e define a ordem de leitura dentro do repositório. Este arquivo não repete o protocolo LIFE nem fixa versões de Dossiê: isso mora no start, que é mantido atualizado.

**Enquadramento.** O UpexNote tem dupla natureza: é um produto do UpexFlow e também um trabalho de Leonardo que serve de evidência profissional (LinkedIn, posicionamento). Entender essa dupla função antes de decidir texto, escopo ou prioridade.

Se o Drive ou o start não estiverem acessíveis, parar, dizer qual documento falhou e pedir a Leonardo que anexe o start. Nunca presumir o conteúdo.

---

# PARTE 2 — REGRAS DO REPOSITÓRIO UPEXNOTE

Estas regras se aplicam a todo o repositório e complementam — nunca substituem — a Parte 1. Um `AGENTS.md` mais próximo pode acrescentar regras específicas de uma subárvore, sem enfraquecer privacidade, segurança ou preservação do trabalho existente.

## 11. Antes de agir

1. Ler `docs/CONTEXT_ORCHESTRATION.md` — é ele que coordena a ordem, a necessidade e a profundidade de leitura de todo o resto.
2. Ler integralmente: `docs/PROJECT_CONTEXT.md`, `docs/FEATURE_VALIDATION_AND_ROADMAP.md`, `docs/UX_PRODUCT_STANDARD.md`, `README.md`, este arquivo e quaisquer `AGENTS.md` das pastas afetadas.
3. Ler os documentos especializados exigidos pela tarefa — por exemplo `docs/NOTEBOOK_ARCHITECTURE.md` para qualquer trabalho em Prévia/Caderno, `docs/ARCHITECTURE.md` para limites técnicos, `docs/AI_MEDIA_EVOLUTION.md` para IA/áudio/idiomas.
4. Conferir sem modificar: `git status --short`, `git log --oneline -20`, `git branch -vv`, estrutura relevante em `apps/`, `services/`, `ops/` e `docs/`. Se a branch estiver `behind` de `origin/main`, ler as versões via `git show origin/main:<caminho>` antes de assumir o conteúdo local como canônico.
5. Preservar mudanças preexistentes no worktree. Descobrir o que já existe antes de propor backlog ou arquitetura nova.

## 12. Regras não negociáveis

- Nunca exponha ou registre segredos, tokens, OAuth, senhas, credenciais, áudio, vídeo ou transcrições privadas.
- UpexNote é local-first: material bruto não sai da máquina sem ação e consentimento explícitos.
- O transcript raw é imutável e é a referência; o clean é uma camada derivada separada e validada; a prévia estruturada é outra camada derivada em `documents`, versionável e só-leitura; a nota editável do Caderno é outra camada derivada em `notebooks`, com ciclo de vida independente e linhagem para a origem — nenhuma dessas camadas pode sobrescrever a anterior silenciosamente.
- Cada novo domínio de banco usa schema PostgreSQL próprio, em inglês (padrão já seguido por `documents`, `support`, `data_studio`; `notebooks` é o próximo).
- UI/UX é requisito arquitetural e segue `docs/UX_PRODUCT_STANDARD.md`. Uma interface visual só está concluída quando a funcionalidade opera de ponta a ponta — protótipo visual não é entrega.
- Administração usa menu lateral hierárquico; não transformar submódulos em navegação principal por abas horizontais.
- Chamadas a motores de IA/cloud pagos exigem ação explícita do utilizador, fornecedor e custo visíveis antes de executar — nunca chamada automática oculta.
- Não executar deploy, mudanças externas, push ou operações destrutivas sem autorização específica de Leonardo.
- Material pessoal e editorial nunca entra no repositório: rascunhos e decisões de publicações (LinkedIn e outras redes), notas da série, prompts de retomada editoriais, estratégia de carreira e qualquer documento de trabalho que não faça parte do produto. Esses arquivos ficam apenas em `docs/private/` (ignorado pelo Git; subpasta `docs/private/linkedin/` para a série), na máquina de Leonardo e na sessão da IA. Antes de qualquer commit, conferir com `git status` que nenhum desses arquivos está listado; se estiver, mover para `docs/private/` em vez de versionar. O repositório guarda somente o produto, sua documentação técnica e os materiais públicos que o README referencia.

## 13. Disciplina de build e de entrega

- `npm run tauri build` NÃO reempacota o worker Python. Se a fatia tocar em `services/worker/`, correr primeiro `powershell -ExecutionPolicy Bypass -File services\worker\build_worker.ps1` e só depois `npm.cmd run tauri build`. Esquecer produz um instalador com backend antigo cujo sintoma é silencioso: nada falha, a funcionalidade apenas não aparece na app.
- Implementar em fatias pequenas — uma ou duas funcionalidades complementares por vez, build, versão nova, commit e push, seguindo o padrão incremental já visível no histórico do `PROJECT_CONTEXT.md`. Não acumular funcionalidades grandes numa única versão não lançada.
- Nunca usar `git add -A`; sempre listar arquivos explícitos ao commitar.
- Ao finalizar uma etapa autorizada: executar validações (incluindo verificação visual quando houver UI); atualizar `docs/PROJECT_CONTEXT.md` (Registro + Estado atual) e `docs/FEATURE_VALIDATION_AND_ROADMAP.md` (estado da frente) quando houver mudança relevante; atualizar qualquer documento especializado afetado; criar commit claro; fazer push apenas após autorização aplicável e confirmação de segurança.
- Documentação desatualizada é considerada entrega incompleta.

## 14. Fonte de verdade

Use esta prioridade:

1. código e estado real do repositório/Git;
2. `docs/PROJECT_CONTEXT.md`;
3. documentos arquiteturais específicos da frente (`docs/NOTEBOOK_ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, etc.);
4. `docs/UX_PRODUCT_STANDARD.md`;
5. `docs/FEATURE_VALIDATION_AND_ROADMAP.md` para prioridade e estado futuro;
6. `docs/FUTURE_PRODUCT_IDEAS.md` e `docs/AI_MEDIA_EVOLUTION.md` para possibilidades ainda não aprovadas;
7. conversas antigas apenas como contexto complementar.

Ler `docs/ACCOUNT_CONTINUITY_HANDOFF.md` quando houver troca de conta, sessão ou agente, e `docs/NEW_ACCOUNT_BOOTSTRAP_PROMPT.md` para inicialização prática de uma conta nova.

## 15. Vocabulário do utilizador

- "Ambiente" significa o navegador interno do agente (Codex/Claude em Chrome) com os acessos de trabalho, não uma pasta ou documento do repositório.
- Quando Leonardo disser "abra o ambiente", abrir ou reutilizar uma aba para cada destino habitual:
  - Google Cloud/API do projeto UpexNote: `https://console.cloud.google.com/apis/credentials?project=upexnote&pli=1`;
  - GitHub: `https://github.com/cunha-leo`;
  - EasyPanel/VPS: `<URL_PAINEL_EASYPANEL>`;
  - Hostinger hPanel: `https://hpanel.hostinger.com/`;
  - webmail da conta `contact@upexflow.com`, usando a sessão autenticada disponível.
- Reutilizar abas e sessões existentes quando possível, evitar duplicatas e deixar os destinos abertos para acompanhamento do utilizador.
- Se algum serviço solicitar autenticação, deixar a página visível para Leonardo concluir o acesso e continuar abrindo os demais destinos.
- Nunca copiar, expor ou registrar cookies, sessões, senhas, tokens ou outros dados de autenticação desses serviços.

## 16. Infraestrutura de referência rápida

- Raiz de desenvolvimento atual (confirmada em 24/11/2026): `C:\Dev\upexnote` (disco local, fora de sincronização em nuvem — o código não fica no Google Drive).
- GitHub: repositório privado `cunha-leo/upexnote`, branch principal `main`.
- VPS: Hostinger KVM 2 com EasyPanel, PostgreSQL acessível via DBeaver/SSH; nunca usar para guardar biblioteca crescente de vídeo ou transcrição pesada.
- Acesso SSH à VPS nunca usa password — sempre chave SSH (`~/.ssh/<CHAVE_SSH_VPS>`); ver runbook completo em `docs/PROJECT_CONTEXT.md`, seção 8, se a chave precisar ser recriada.
