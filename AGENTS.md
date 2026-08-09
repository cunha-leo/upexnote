# AGENTS.md — UpexNote

Este arquivo tem duas camadas obrigatórias, nesta ordem. A ordem é a mesma exigida por `docs/CONTEXT_ORCHESTRATION.md`: primeiro a camada humana e decisória (quem é Leonardo e o estado vivo das decisões), depois a camada técnica do repositório e da aplicação.

1. **PARTE 1 — Bootstrap LIFE** (protocolo de leitura do Dossiê, Contexto Vivo e Fio Condutor no Google Drive).
2. **PARTE 2 — Regras do repositório UpexNote** (regras não negociáveis, disciplina de trabalho e fonte de verdade para a aplicação).

Não pular a Parte 1 para ir direto à Parte 2. O Dossiê e o Contexto Vivo explicam como Leonardo decide, valida e prioriza; sem isso, a Parte 2 é seguida sem entender por quê.

---

# PARTE 1 — PROTOCOLO DE INICIALIZAÇÃO LIFE

Versão do protocolo: 1.0
Responsável: Leonardo Cunha
Status: ativo

## 1. Objetivo

Este bloco é uma instrução operacional para qualquer nova conversa ou projeto LIFE, incluindo este repositório. Quando Leonardo pedir para ler este arquivo, inicializar o LIFE ou carregar o contexto LIFE, execute o protocolo inteiro sem pedir que ele repita seu histórico.

A sessão só pode ser considerada contextualizada depois de verificar e, quando necessário, ler integralmente os documentos canônicos nesta ordem:

Dossiê/Manifesto LIFE — identidade, trajetória, arquitetura cognitiva, método de trabalho, capacidades, limites e forma de interpretar Leonardo.

Contexto Vivo de Decisão — estado atual, fatos recentes, ramos ativos, ramos abstraídos, critérios, registros formais de decisão e próximos passos.

Fio Condutor — Objetivo Central LIFE — lente de interpretação sobre os dois anteriores, lida por último.

O Dossiê sempre vem primeiro. O Contexto Vivo sempre vem depois. O Fio Condutor por último.

## 2. Pasta e fontes canônicas

Use exclusivamente a pasta abaixo como fonte oficial:

Pasta: 00- Manifesto&Decisions
ID: 1mTd5Zv12Pniqs2-YqF0IfUC0KoY-Wpsb
URL: https://drive.google.com/drive/folders/1mTd5Zv12Pniqs2-YqF0IfUC0KoY-Wpsb

Não escolher cópias homônimas existentes em outras pastas. Versões antigas de um mesmo documento devem ficar na subpasta `old` dessa pasta canônica, nunca soltas ao lado da versão atual.

Localize dentro dessa pasta a versão mais alta de cada família.

### Dossiê/Manifesto LIFE

Padrão: Dossie_Leonardo_Cunha_LIFE_v\<versão\>.docx
Linha de base em 9 de agosto de 2026: v1.3
As linhas de base não são fixas. Sempre verificar se existe versão posterior na pasta canônica.

### Contexto Vivo de Decisão

Padrão: Contexto_Vivo_Decisao_Portugal_Brasil_Leonardo_v\<versão\>.docx
Linha de base em 9 de agosto de 2026: v2.9

### Fio Condutor — Objetivo Central LIFE

Padrão: Fio_Condutor_Objetivo_Central_v\<versão\>.md
Linha de base em 9 de agosto de 2026: v1.0

## 3. Estado mínimo da sessão

Mantenha estes marcadores na sessão:

LIFE_DOSSIER_LOADED_VERSION
LIFE_DOSSIER_LOADED_FILE_ID
LIFE_DOSSIER_LOADED_MODIFIED_TIME
LIFE_CONTEXT_LOADED_VERSION
LIFE_CONTEXT_LOADED_FILE_ID
LIFE_CONTEXT_LOADED_MODIFIED_TIME
LIFE_BOOTSTRAP_COMPLETE

Não considerar um documento já lido apenas porque existem memórias, resumos, trechos, mensagens anteriores ou conhecimento aproximado. Ele só está carregado quando o conteúdo integral daquela versão foi lido nesta sessão e os marcadores correspondentes podem ser identificados.

## 4. Regra condicional de leitura

Para cada documento, compare versão, ID e data de modificação do Drive com o estado da sessão.

Ler integralmente quando ocorrer qualquer uma destas condições:

- não existe versão registrada na sessão;
- não existe prova de leitura integral na sessão;
- a versão do Drive é maior que a versão carregada;
- o ID do arquivo mudou;
- a data de modificação é posterior à registrada na sessão;
- existe dúvida sobre cortes, lacunas, trechos omitidos ou leitura incompleta.

Não reler somente quando todas estas condições forem verdadeiras:

- a versão da sessão é idêntica à versão mais recente do Drive;
- o ID é o mesmo;
- a data de modificação é a mesma;
- a leitura integral já foi concluída nesta sessão.

Se a sessão indicar versão maior do que a existente na pasta, não fazer downgrade silencioso. Informar a divergência e preservar a versão mais nova já carregada até localizar a fonte correta ou receber orientação de Leonardo.

## 5. Leitura integral obrigatória

Quando a leitura for necessária:

- abrir o arquivo completo, não apenas o resultado de busca;
- ler do início ao fim, em ordem;
- ler todo o conteúdo textual, parágrafo por parágrafo e linha por linha;
- não abstrair, não pular capítulos e não selecionar apenas partes relevantes;
- não usar resumo, memória, índice, capa, snippet ou busca como substituto;
- não interromper para pedir autorização entre blocos;
- quando a ferramenta exigir leitura em partes, continuar automaticamente do ponto exato em que parou, sem lacunas nem duplicações;
- não começar análise estratégica, aconselhamento ou atualização documental antes de concluir os três documentos;
- declarar claramente qualquer falha de acesso ou leitura e nunca afirmar leitura integral sem evidência operacional suficiente.

## 6. Ordem de execução

**Etapa A — Descoberta.** Listar os arquivos da pasta canônica, identificar a maior versão do Dossiê, do Contexto Vivo e do Fio Condutor e comparar versão, ID e data de modificação com o estado da sessão.

**Etapa B — Dossiê/Manifesto LIFE.** Aplicar a regra condicional. Quando necessário, ler integralmente. Depois registrar versão, ID e data de modificação carregados.

**Etapa C — Contexto Vivo de Decisão.** Executar somente depois da Etapa B. Aplicar a mesma regra condicional.

**Etapa D — Fio Condutor.** Executar por último, como lente de interpretação sobre os dois anteriores.

**Etapa E — Ativação da sessão.** Depois que os três documentos estiverem atualizados: definir LIFE_BOOTSTRAP_COMPLETE = true; usar o Dossiê como base de identidade, método, capacidades e estilo cognitivo; usar o Contexto Vivo como base do estado decisório atual e das prioridades; usar o Fio Condutor para entender por que as frentes de vida se conectam; continuar sem pedir que Leonardo repita informações já presentes nesses documentos.

## 7. Hierarquia de interpretação

Ao trabalhar depois da leitura, usar esta precedência:

1. instrução explícita mais recente de Leonardo na conversa atual;
2. evidência primária e fatos datados;
3. Contexto Vivo mais recente para estado, decisões e prioridades;
4. Dossiê LIFE mais recente para identidade, método, capacidades e limites;
5. interpretações e hipóteses, sempre identificadas como tais.

O Dossiê não substitui uma decisão posterior registrada no Contexto Vivo. O Contexto Vivo não apaga a identidade e o método estruturados no Dossiê.

## 8. Fidelidade e limites

- preservar a terminologia, a arquitetura e os contrastes dos documentos;
- não reduzir Leonardo a desenvolvedor, generalista superficial, analista burocrático ou testador manual — ele possui capacidade demonstrada de conceber e construir sistemas de ponta a ponta; não adotar "Developer" como identidade profissional principal é decisão de carreira, não limitação técnica (Dossiê v1.3, Adenda H);
- não transformar hipótese em fato nem propaganda em evidência;
- não reabrir ramo abstraído sem fato estrutural novo ou instrução explícita;
- não sobrescrever versões anteriores ao atualizar documentos — mover a versão superada para a subpasta `old`, nunca apagar;
- criar nova versão conforme o esquema definido no Contexto Vivo;
- não carregar outros cadernos, cursos ou anexos no bootstrap inicial, salvo pedido explícito ou necessidade da tarefa;
- não copiar o conteúdo integral do Dossiê ou do Contexto Vivo para dentro deste repositório Git — este arquivo referencia o protocolo, não duplica o conteúdo pessoal.

### 8.1. Validação visual de documentos

Quando o Dossiê, o Contexto Vivo ou outro documento canônico estiver em `DOCX` ou `PDF`, a leitura textual não substitui a renderização das páginas. Imagens, diagramas, tabelas, cabeçalhos, rodapés e elementos de layout também compõem o conteúdo integral.

Para tarefas de leitura visual, revisão, criação ou edição documental:

- converter `DOCX` para PDF com LibreOffice em modo headless;
- rasterizar o PDF com Poppler ou ferramenta equivalente, gerando uma imagem por página;
- conferir a contagem e revisar visualmente todas as páginas;
- depois de qualquer edição, repetir a renderização e a revisão completas;
- nunca afirmar leitura integral ou fidelidade visual quando as imagens ou páginas não puderam ser processadas;
- em caso de falha, diagnosticar ferramentas, `PATH`, permissões, diretório temporário, URI do perfil, fontes e imagens antes de recorrer a extração textual.

Configuração conhecida nesta máquina Windows:

```text
LibreOffice/soffice:
C:\Users\cunha\AppData\Local\Programs\LibreOfficeCodex\program\soffice.exe

Poppler (pdfinfo/pdftoppm):
C:\Users\cunha\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin
```

Se necessário, adicionar esses diretórios ao `PATH` do processo atual. No Windows, fornecer o perfil temporário do LibreOffice como URI válida `file:///C:/...`, preferencialmente gerada por `Path(...).resolve().as_uri()`, nunca como `file://C:\...`.

Em cloud ou outro ambiente, localizar ferramentas equivalentes. Se não houver capacidade real de renderizar páginas e imagens, declarar a limitação e não substituir silenciosamente a validação visual por leitura de texto.

## 9. Resposta ao concluir

Quando houve leitura: "Bootstrap LIFE concluído. Dossiê vX lido integralmente; Contexto Vivo vY lido integralmente; Fio Condutor vZ lido integralmente; sessão atualizada."

Quando já estavam carregados e idênticos: "Bootstrap LIFE verificado. Dossiê vX, Contexto Vivo vY e Fio Condutor vZ já estavam integralmente carregados nesta sessão e permanecem idênticos às versões canônicas do Drive."

Quando apenas um precisou ser atualizado, informar qual foi relido, qual foi reaproveitado e as versões correspondentes.

Não apresentar resumo extenso automaticamente. O objetivo do bootstrap é absorver o contexto e ficar pronto para a tarefa seguinte.

## 10. Comando de ativação recomendado

Leia o arquivo AGENTS.md da pasta 00- Manifesto&Decisions e execute integralmente o protocolo de inicialização LIFE. Depois disso, esta instrução deve conduzir toda a descoberta, comparação e leitura sem exigir que Leonardo reescreva o contexto.

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
  - EasyPanel/VPS: `https://vps.upexflow.com/`;
  - Hostinger hPanel: `https://hpanel.hostinger.com/`;
  - webmail da conta `contact@upexflow.com`, usando a sessão autenticada disponível.
- Reutilizar abas e sessões existentes quando possível, evitar duplicatas e deixar os destinos abertos para acompanhamento do utilizador.
- Se algum serviço solicitar autenticação, deixar a página visível para Leonardo concluir o acesso e continuar abrindo os demais destinos.
- Nunca copiar, expor ou registrar cookies, sessões, senhas, tokens ou outros dados de autenticação desses serviços.

## 16. Infraestrutura de referência rápida

- Raiz de desenvolvimento: `C:\Users\cunha\Projects\upexflow\upexnote` (disco local, fora de sincronização em nuvem — o código não fica no Google Drive).
- GitHub: repositório privado `cunha-leo/upexnote`, branch principal `main`.
- VPS: Hostinger KVM 2 com EasyPanel, PostgreSQL acessível via DBeaver/SSH; nunca usar para guardar biblioteca crescente de vídeo ou transcrição pesada.
- Acesso SSH à VPS nunca usa password — sempre chave SSH (`~/.ssh/upexnote_vps`); ver runbook completo em `docs/PROJECT_CONTEXT.md`, seção 8, se a chave precisar ser recriada.
