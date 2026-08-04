# UpexNote — Feature Validation and Roadmap

> **Natureza:** submatriz operacional para descoberta, validação, priorização, implementação e promoção de novas funcionalidades.
>
> **Não representa automaticamente:** estado entregue do produto, autorização irrestrita de implementação, decisão comercial definitiva ou substituição dos documentos especializados.
>
> **Relação com a matriz principal:** este documento deve ser lido em conjunto com `docs/PROJECT_CONTEXT.md`. O `PROJECT_CONTEXT.md` continua sendo a matriz consolidada do estado validado, das decisões vigentes, das versões entregues e do histórico principal. Este arquivo controla o trabalho ainda em validação, execução ou fechamento.
>
> **Regra de promoção:** uma funcionalidade só se torna estado vigente do produto depois de implementada, validada, registrada aqui como concluída e promovida para `docs/PROJECT_CONTEXT.md`.

---

## 1. Objetivo

Este documento existe para impedir que hipóteses, possibilidades, frentes aprovadas e funcionalidades já entregues sejam tratadas como se fossem a mesma coisa.

Ele deve:

- registrar frentes antes da implementação;
- preservar problema, objetivo, hipótese de valor, escopo e critérios de aceite;
- organizar dependências técnicas, de produto, segurança, privacidade e UX;
- ser retroalimentado durante a execução;
- registrar decisões, desvios, evidências, commits, versões e validações;
- manter o histórico completo depois da entrega;
- promover somente a verdade consolidada para `docs/PROJECT_CONTEXT.md`;
- consultar e atualizar documentos especializados quando a frente tocar seus domínios;
- permitir que uma nova IA ou sessão reconstrua não apenas o que será feito, mas por que, em que ordem e com quais limites.

Este arquivo funciona como uma submatriz conectiva. Ele não substitui os demais documentos. Ele coordena quando cada documento deve ser consultado, respeitado, atualizado e novamente refletido neste roadmap.

---

## 2. Modelo documental: matriz, submatriz e agentes de domínio

A documentação do UpexNote funciona como um sistema cooperativo de memória versionada.

```text
PROJECT_CONTEXT.md
  matriz consolidada do estado real e validado
            ↑ promoção após entrega e validação
            |
FEATURE_VALIDATION_AND_ROADMAP.md
  submatriz de descoberta, prioridade, execução e fechamento
            ↕ consulta e retroalimentação por domínio
            |
  documentos especializados de produto, UX, arquitetura,
  suporte, dados, continuidade, mídia/IA e possibilidades futuras
```

O fluxo é bidirecional:

1. A submatriz consulta a matriz e os documentos especializados antes de definir ou implementar uma frente.
2. Durante a execução, decisões e evidências retornam para esta submatriz.
3. Quando uma decisão muda um domínio especializado, o documento daquele domínio também é atualizado.
4. Depois da validação final, o resumo consolidado é promovido para `PROJECT_CONTEXT.md`.
5. O fechamento permanece neste arquivo como histórico auditável; não é apagado após a promoção.

Nenhum documento especializado deve ficar isolado. Nenhum deles deve ser lido indiscriminadamente em toda tarefa. A consulta depende do domínio afetado.

---

## 3. Autoridade e momento de consulta de cada documento

### `docs/PROJECT_CONTEXT.md`

**Papel:** matriz principal e fonte consolidada de verdade do projeto.

**Consultar:**

- no início de qualquer sessão de desenvolvimento ou decisão relevante;
- antes de assumir que uma funcionalidade existe, está validada ou permanece vigente;
- antes de alterar arquitetura, produto, dados, segurança ou backlog;
- no fechamento de uma entrega, para promover o novo estado consolidado.

**Atualizar:**

- somente depois de implementação e validação suficientes;
- quando uma decisão vigente, versão, capacidade entregue ou regra durável mudar;
- com resumo do que foi entregue, limites, versão, evidências e estado atual.

**Não usar como:** área extensa de exploração, rascunho de hipótese ou fila operacional detalhada.

### `docs/FEATURE_VALIDATION_AND_ROADMAP.md`

**Papel:** submatriz operacional das frentes ainda não consolidadas.

**Consultar:**

- antes de iniciar qualquer nova feature ou evolução;
- para saber prioridade, estado, dependências, critérios de aceite e documentos obrigatórios;
- durante a execução, para manter a continuidade entre sessões e IAs;
- no fechamento, antes da promoção para `PROJECT_CONTEXT.md`.

**Atualizar:** continuamente durante descoberta, validação, implementação, teste e encerramento.

### `docs/UX_PRODUCT_STANDARD.md`

**Papel:** autoridade de UX e critério de aceite de experiência.

**Consulta obrigatória antes de qualquer implementação que afete:**

- layout ou front-end;
- fluxo, navegação ou hierarquia visual;
- menu contextual, painel lateral, modal, tabela ou editor;
- estados vazio, carregando, erro, sucesso, foco, hover ou seleção;
- acessibilidade, teclado, responsividade, densidade, temas e legibilidade;
- retorno visual de salvar, editar, excluir, exportar ou processar;
- comportamento em desktop normal sem rolagem horizontal exposta.

Uma funcionalidade com interface não pode ser marcada como concluída sem validação contra esse documento.

### `docs/ARCHITECTURE.md`

**Papel:** limites e contratos arquiteturais gerais.

**Consultar quando houver:**

- novo módulo, domínio, serviço, worker ou comando Tauri;
- mudança entre processamento local, API e VPS;
- alteração de responsabilidades entre React, Rust, Python, SQLite, PostgreSQL ou armazenamento;
- fila, job, sincronização, cache, eventos ou integração externa;
- nova fronteira de segurança ou persistência.

**Atualizar quando:** a arquitetura vigente ou seus contratos mudarem de forma durável.

### `docs/PRODUCT.md`

**Papel:** definição de produto, problema, público, princípios e jornada funcional.

**Consultar quando houver:**

- alteração na proposta de valor;
- novo público, caso de uso ou fluxo principal;
- decisão de posicionamento, empacotamento ou limites do produto;
- risco de transformar possibilidade comercial em requisito já aprovado.

**Atualizar quando:** uma mudança de produto for aceita como direção vigente, não apenas imaginada.

### `docs/AI_MEDIA_EVOLUTION.md`

**Papel:** memória especializada de Formatação, Estudo, leitura, reprodução, voz, idiomas, sincronização e modo ao vivo.

**Consulta obrigatória antes de implementar:**

- conteúdo estruturado derivado do transcript;
- editor/leitor de estudo;
- Action Items, tópicos, decisões, riscos, quiz ou chat ancorado;
- tradução e experiências multilíngues;
- player, timestamps por palavra, TTS ou vozes;
- captura e transcrição ao vivo;
- qualquer IA aplicada ao transcript ou a conteúdo derivado.

**Atualizar quando:** testes, fornecedores, capacidades, decisões de privacidade ou dependências desse domínio mudarem.

### `docs/SUPPORT_ARCHITECTURE.md`

**Papel:** autoridade do domínio de suporte e de seu schema PostgreSQL isolado.

**Consultar quando houver:**

- tickets, comentários, atribuições, prioridades, SLA ou notificações;
- integração bidirecional com e-mail;
- evidências, anexos, spool, arquivamento e manifesto;
- alterações no histórico, auditoria ou ciclo de vida de chamados.

**Atualizar quando:** contratos, objetos, políticas de retenção, fluxos ou infraestrutura de suporte forem alterados.

### `docs/DATA_STUDIO_ARCHITECTURE.md`

**Papel:** autoridade do Data Studio e de seus limites administrativos.

**Consultar quando houver:**

- Visual Builder, SQL Editor, Saved Queries ou ER Diagram;
- scheduler, jobs, eventos, entregas ou relatórios de consultas;
- APIs, webhooks, CRM, n8n ou conectores originados no Data Studio;
- qualquer mutação, exposição ou movimentação de dados PostgreSQL.

**Atualizar quando:** uma fase do Data Studio for aprovada, entregue ou tiver seus contratos alterados.

### `docs/FUTURE_PRODUCT_IDEAS.md`

**Papel:** biblioteca de possibilidades exploratórias não aprovadas.

**Consultar quando:** uma ideia futura reaparecer, para evitar redescoberta ou tratamento indevido como novidade.

**Atualizar quando:** surgir possibilidade relevante ainda sem validação suficiente para entrar no roadmap operacional.

**Mover para este roadmap quando:** a ideia ganhar problema definido, objetivo, prioridade, critérios e autorização para validação ou implementação.

### `docs/ACCOUNT_CONTINUITY_HANDOFF.md`

**Papel:** continuidade de conta, ambiente e transferência segura de contexto entre sessões ou ferramentas.

**Consultar quando houver:**

- troca de conta, IA, ambiente ou máquina;
- necessidade de reconstruir o estado documental e operacional;
- dúvida sobre como retomar o projeto sem perder contexto;
- preparação de handoff para outra sessão.

**Atualizar quando:** a ordem de leitura, os documentos centrais, o fluxo de retomada ou os pontos de continuidade mudarem.

### `docs/NEW_ACCOUNT_BOOTSTRAP_PROMPT.md`

**Papel:** instrução de inicialização para uma nova conta ou IA.

**Consultar quando:** uma sessão nova precisar ser preparada para trabalhar no repositório.

**Atualizar quando:** a sequência obrigatória de leitura ou a rede documental ganhar um novo documento central.

A leitura de bootstrap deve incluir, no mínimo, `PROJECT_CONTEXT.md`, este roadmap e os documentos de domínio exigidos pela tarefa.

### `README.md` e READMEs de módulos

**Papel:** entrada operacional e orientação técnica localizada.

**Consultar quando:** a tarefa tocar instalação, execução, estrutura do repositório ou um módulo específico.

**Atualizar quando:** comandos, dependências, caminhos ou instruções operacionais mudarem.

### `AGENTS.md`

**Papel:** regras locais para agentes e ferramentas de desenvolvimento.

**Consulta obrigatória:** antes de modificar qualquer arquivo dentro do escopo coberto pelo `AGENTS.md` aplicável.

---

## 4. Precedência e resolução de conflito

Quando documentos parecerem divergir:

1. código executável e estado validado determinam o que realmente existe;
2. `PROJECT_CONTEXT.md` determina o estado consolidado e as decisões vigentes;
3. o documento especializado determina os contratos do seu domínio;
4. este roadmap determina prioridade, status e fluxo das frentes ainda não consolidadas;
5. `FUTURE_PRODUCT_IDEAS.md` preserva possibilidades, sem transformá-las em compromisso.

A divergência deve ser registrada e resolvida explicitamente. Não se deve apagar histórico útil nem misturar hipótese com entrega.

---

## 5. Estados controlados

Cada frente usa um dos estados abaixo:

- `Exploring`: problema ou possibilidade ainda em descoberta;
- `Validating`: hipótese sendo confrontada com evidências, testes ou desenho;
- `Approved`: direção aprovada e pronta para refinamento executivo;
- `Ready`: escopo, dependências e critérios suficientes para implementação;
- `In progress`: implementação em andamento;
- `Blocked`: impedimento explícito e documentado;
- `Delivered`: implementação concluída, ainda aguardando validação final ou promoção;
- `Validated`: entrega comprovada contra critérios e uso real relevante;
- `Promoted to PROJECT_CONTEXT`: resumo consolidado transferido para a matriz principal;
- `Closed`: ciclo encerrado, mantendo histórico;
- `Discarded`: descartada com justificativa, sem apagar o raciocínio;
- `Dormant`: preservada, mas sem prioridade atual.

Fluxo normal:

```text
Exploring
  → Validating
  → Approved
  → Ready
  → In progress
  → Delivered
  → Validated
  → Promoted to PROJECT_CONTEXT
  → Closed
```

Nem toda frente precisa percorrer todos os estados. Qualquer salto deve ter justificativa.

---

## 6. Regras de retroalimentação

Durante a execução, cada frente deve registrar:

- decisões tomadas;
- dúvidas abertas e respostas;
- alterações de escopo;
- dependências descobertas;
- riscos e mitigações;
- testes executados;
- evidências visuais e funcionais;
- arquivos e módulos alterados;
- commits e versões;
- itens adiados, descartados ou transferidos;
- divergências entre documentação e implementação;
- atualização necessária nos documentos especializados.

Ao concluir:

1. marcar o escopo entregue e o que ficou de fora;
2. registrar critérios de aceite e resultados;
3. indicar versão, commits e evidências;
4. atualizar documentos especializados afetados;
5. produzir resumo consolidado para `PROJECT_CONTEXT.md`;
6. promover o estado validado;
7. marcar `Promoted to PROJECT_CONTEXT`;
8. mover o registro para a seção de histórico fechado, sem apagá-lo.

---

## 7. Critério mínimo para uma frente entrar em implementação

Uma frente só pode chegar a `Ready` quando possuir:

- problema real e claramente descrito;
- objetivo e resultado esperado;
- usuário ou cenário beneficiado;
- hipótese de valor;
- escopo incluído e excluído;
- dependências documentais e técnicas;
- regras de privacidade e segurança;
- jornada principal;
- estados de UI/UX quando aplicável;
- modelo de dados ou persistência quando aplicável;
- tratamento de erro, cancelamento e retomada;
- critérios de aceite verificáveis;
- estratégia de validação;
- decisão explícita sobre o que não será feito nessa fase.

---

## 8. Approved Delivery Front

### ADF-01 — Structured Document Generation

**Status:** `Approved`

**Prioridade:** máxima na evolução atual do produto.

**Problema:** o UpexNote já entrega transcript raw e clean com qualidade, rastreabilidade e segurança, mas a jornada ainda termina predominantemente no transcript. O utilizador precisa transformar a conversa em material organizado sem copiar o conteúdo para várias ferramentas externas.

**Objetivo:** transformar o transcript clean em um documento estruturado, legível e reutilizável, preservando o vínculo com a fonte.

**Jornada-base:**

```text
áudio ou vídeo
  → transcript raw imutável
  → transcript clean validado
  → documento estruturado derivado
  → workspace de edição e estudo
  → salvamento, exportação e uso posterior
```

**Conteúdo que a transformação deve poder estruturar:**

- seções e subtítulos;
- objetivos;
- requisitos;
- decisões;
- ações e responsáveis quando identificáveis;
- riscos;
- dúvidas;
- tópicos principais;
- contexto técnico;
- jargões, siglas e palavras-chave;
- definições ou explicações contextuais quando justificadas;
- trechos relevantes e referência ao falante ou timestamp quando disponível.

**Regras:**

- o raw permanece imutável;
- o clean permanece uma camada derivada separada;
- o documento estruturado é uma nova camada derivada, editável e versionada;
- reorganização não pode inventar fatos nem apagar silenciosamente conteúdo importante;
- conteúdo gerado deve identificar motor, data, origem e tipo de processamento;
- chamadas cloud exigem ação explícita, fornecedor visível e custo compreensível;
- a arquitetura deve abstrair fornecedor e permitir motores alternativos;
- o documento deve permanecer portável.

**Documentos obrigatórios:**

- `PROJECT_CONTEXT.md`;
- `UX_PRODUCT_STANDARD.md`;
- `ARCHITECTURE.md`;
- `PRODUCT.md`;
- `AI_MEDIA_EVOLUTION.md`.

**Decisões ainda necessárias antes de `Ready`:**

- modelo interno do documento;
- formato de persistência;
- perfis iniciais de transformação;
- contrato entre clean, documento e referências;
- motor inicial e benchmark próprio;
- custo e limites por execução;
- comportamento diante de conteúdo ambíguo ou incompleto.

---

### ADF-02 — Rich Study Workspace

**Status:** `Approved`

**Prioridade:** máxima e acoplada à ADF-01.

**Problema:** gerar um documento bonito sem permitir trabalho humano dentro dele mantém a fricção de exportar, editar e estudar em outras ferramentas.

**Objetivo:** criar uma superfície visual de leitura, edição, anotação e estudo, com experiência próxima de um editor moderno e formato portável por baixo.

**Direção de interface:** editor rico estruturado, não whiteboard espacial livre. Pode usar Markdown ou representação estruturada equivalente como base, desde que a experiência visual não exponha complexidade desnecessária.

**Capacidades aprovadas para refinamento:**

- títulos, subtítulos e seções;
- negrito, itálico, listas, citações e blocos;
- destaques e marca-texto;
- criação, remoção e reorganização de seções;
- edição do conteúdo derivado;
- notas pessoais;
- salvamento local no destino escolhido;
- histórico e versionamento;
- retorno ou comparação com o transcript de origem;
- exportação sem perder estrutura;
- estados claros de edição, salvamento, erro, conflito e recuperação.

**UX obrigatória:**

- consultar `UX_PRODUCT_STANDARD.md` antes do desenho e antes do aceite;
- responder claramente onde o usuário está, o que pode fazer, o que aconteceu e como retornar ou aprofundar;
- suportar teclado, foco, seleção, temas, zoom e densidade;
- evitar poluir o menu principal;
- manter o fluxo coerente com Library e detalhe do transcript;
- permitir acesso após a conclusão da transcrição e a partir de materiais existentes.

**Documentos obrigatórios:**

- `PROJECT_CONTEXT.md`;
- `UX_PRODUCT_STANDARD.md`;
- `ARCHITECTURE.md`;
- `PRODUCT.md`;
- `AI_MEDIA_EVOLUTION.md`.

---

### ADF-03 — Anchored Comments and Study References

**Status:** `Approved`

**Prioridade:** alta dentro do Rich Study Workspace.

**Objetivo:** permitir que o usuário selecione palavra, termo, frase, parágrafo ou seção e associe uma anotação persistente ao trecho.

**Experiência esperada:**

- seleção de um trecho abre ações contextuais;
- ação de comentário cria um balão ou indicador visual ancorado;
- painel lateral lista comentários e referências;
- clicar no indicador abre o conteúdo correspondente;
- comentários podem ser criados, editados, removidos, resolvidos e navegados;
- o vínculo deve sobreviver à reabertura do documento;
- alterações no texto devem preservar ou sinalizar referências quebradas;
- o usuário deve perceber imediatamente que há conteúdo associado ao trecho.

**Dados mínimos de uma anotação:**

- documento;
- trecho ou âncora;
- seção e posição;
- texto selecionado;
- comentário;
- autor local;
- datas de criação e alteração;
- estado;
- origem, quando for definição ou referência externa.

**Exportação:**

Comentários e referências não precisam poluir o corpo principal. Podem ser incluídos em uma seção final, por exemplo `Notas e comentários` ou `Referências de estudo`, contendo trecho, localização, comentário, definição e fonte.

**Critério de produto:** a funcionalidade deve aumentar compreensão e reutilização sem aprisionamento artificial. Portabilidade e exportação permanecem obrigatórias.

---

### ADF-04 — Dictionary and Glossary Layer

**Status:** `Approved`

**Prioridade:** alta, depois da base de seleção, âncoras e comentários.

**Objetivo:** oferecer definição lexical e construção de glossário sem tornar cada interação dependente de IA.

**Fluxo previsto:**

1. usuário seleciona uma palavra ou termo, ou digita manualmente;
2. menu contextual oferece `Consultar definição`;
3. o sistema identifica ou permite escolher o idioma;
4. consulta dicionário local, cache ou API desacoplada por idioma;
5. apresenta significado, classe gramatical, exemplos e fonte quando disponíveis;
6. permite `Adicionar como referência de estudo`;
7. cria âncora, indicador visual e entrada no painel lateral;
8. inclui o termo no glossário do documento;
9. permite exportar o glossário com o material.

**Distinção obrigatória:**

- dicionário responde ao significado geral e verificável;
- explicação contextual por IA é uma ação separada e posterior;
- IA pode ser fallback para jargão, sigla ou expressão técnica não resolvida, nunca substituição automática da fonte lexical.

**Requisitos técnicos:**

- provedores desacoplados;
- cache local quando permitido;
- fonte e idioma preservados;
- tratamento de termo não encontrado;
- suporte a palavras e expressões compostas;
- privacidade e custo visíveis quando houver serviço externo;
- nenhuma definição externa deve alterar silenciosamente o texto principal.

---

### ADF-05 — Persistence, History and Structured Export

**Status:** `Approved`

**Prioridade:** necessária para concluir o primeiro ciclo de valor.

**Objetivo:** garantir que documento, edições, comentários, referências e glossário formem um ativo durável e portável.

**Escopo aprovado para refinamento:**

- persistência local;
- armazenamento no local escolhido pelo usuário;
- histórico de versões;
- recuperação após falha;
- exportação em Markdown e formatos adicionais a definir;
- inclusão opcional de comentários, notas, glossário e referências;
- pacote de contexto para uso em outra IA;
- manutenção da origem e relação com raw e clean.

**Regras:**

- salvar localmente antes de qualquer sincronização central;
- não enviar conteúdo privado à telemetria;
- não misturar conteúdo derivado no schema `public` sem decisão arquitetural;
- qualquer novo domínio PostgreSQL usa schema inglês isolado;
- exportação deve ser legível fora do UpexNote.

---

## 9. Later Backlog

Itens conhecidos, úteis, mas sem prioridade imediata sobre a frente de transformação e estudo.

### LB-01 — Multilingual and Translation Workflows

- documento no idioma original;
- documento totalmente traduzido;
- visualização bilíngue;
- original e tradução em blocos relacionados;
- glossário multilíngue;
- preservação de code-switching;
- tradução contextual validada.

### LB-02 — Portable AI Context Package

- documento estruturado;
- transcript clean selecionável;
- referências ao raw;
- notas, comentários e glossário;
- prompt preparado;
- instruções de análise;
- anexos selecionados pelo usuário;
- uso em ChatGPT, Gemini, NotebookLM ou outro ambiente.

### LB-03 — Anchored Editing Assistant

- localizar trecho no transcript;
- explicar termo no contexto;
- recuperar informação omitida;
- reorganizar seção;
- sugerir alteração;
- aplicar edição somente mediante confirmação;
- apontar a origem usada.

### LB-04 — Live Capture and Transcription

- microfone;
- áudio do sistema por loopback;
- transcript incremental;
- preservação raw;
- clean ao final;
- encaminhamento para a mesma cadeia de documento e estudo;
- possível atualização progressiva futura.

### LB-05 — Support Evidence Persistence

Referência obrigatória: `SUPPORT_ARCHITECTURE.md`.

- volume persistente `/data/support-spool`;
- job de arquivamento;
- checksum;
- `case.json` e `case.md`;
- manifesto no Drive;
- remoção somente após verificação.

### LB-06 — Actionable Aggregate Telemetry

- definir quais métricas realmente geram decisão;
- preservar consentimento e anonimato;
- avaliar exportação CSV/Excel;
- separar telemetria de produto, instalação e organização;
- não coletar conteúdo, caminhos, identidade ou diagnósticos arbitrários.

Ainda não existe definição suficiente de valor para priorização imediata.

### LB-07 — Saved Queries Scheduler and Reports

Referência obrigatória: `DATA_STUDIO_ARCHITECTURE.md`.

- execução manual facilitada de consultas salvas;
- scheduler;
- jobs;
- eventos;
- entregas;
- relatórios recorrentes;
- histórico sem persistir valores sensíveis;
- exportação controlada.

### LB-08 — Support Operational Maturity

Referência obrigatória: `SUPPORT_ARCHITECTURE.md`.

- filtros avançados;
- SLA;
- prioridade;
- atribuições;
- notificações;
- integração bidirecional com e-mail;
- histórico completo do atendimento.

Não é prioridade enquanto o produto principal ainda está em evolução.

### LB-09 — Direct Export to Knowledge Tools

- exportação para um vault do Obsidian por Markdown e anexos;
- integração autenticada com Notion;
- seleção de workspace e página;
- conversão para blocos suportados;
- preservação de estrutura, referências e glossário.

Essa frente depende da consolidação do modelo de documento e exportação.

---

## 10. Exploratory Possibilities

Estas possibilidades têm valor potencial, mas ainda não representam compromisso de implementação.

### EP-01 — Team and Organization Mode

- múltiplos usuários;
- infraestrutura da organização;
- papéis e permissões;
- isolamento de conteúdo;
- administração centralizada;
- políticas explícitas de propriedade e visibilidade dos transcripts.

### EP-02 — Organizational Telemetry

- horas processadas;
- custo por motor;
- volume por período;
- adoção;
- falhas;
- tendências de uso;
- relatórios para gestores sem acesso automático ao conteúdo individual.

### EP-03 — Managed Corporate Infrastructure

- implantação em VPS do cliente;
- PostgreSQL e API dedicados;
- Docker e hospedagem;
- documentação e treinamento;
- opção de sustentação mensal;
- suporte e governança contratados.

### EP-04 — Generic Events, Webhooks and Connectors

Webhooks são infraestrutura genérica de entrada e saída de eventos ou dados. Não equivalem a uma integração específica com Jira ou Confluence.

Possibilidades:

- eventos de processamento;
- execução de batch;
- entrega de resultados;
- Power BI;
- CRM;
- n8n;
- e-mail;
- consumidores internos ou externos;
- entradas e saídas com autenticação, retries, status e auditoria.

A implementação só deve ocorrer depois de contratos reais de evento, payload, permissão, retenção e responsabilidade.

### EP-05 — Broader Commercial Packaging

- licença solo local-first e BYOK;
- assinatura anual ou mensal;
- equipe pequena;
- implantação corporativa;
- infraestrutura gerenciada;
- consultoria e integrações.

Permanece hipótese comercial até validação de público, disposição de pagamento, custo de suporte e exigências legais.

---

## 11. Template obrigatório para novas frentes

```markdown
### ID — Nome da frente

**Status:**
**Prioridade:**
**Responsável pela decisão:** Leonardo Cunha

**Problema**

**Objetivo**

**Usuário ou cenário**

**Hipótese de valor**

**Escopo incluído**

**Escopo excluído**

**Jornada principal**

**Estados e UX**

**Dados e persistência**

**Privacidade e segurança**

**Dependências técnicas**

**Documentos obrigatórios**

**Riscos**

**Dúvidas abertas**

**Critérios de aceite**

**Estratégia de validação**

**Decisões durante a execução**

**Evidências e testes**

**Arquivos, commits e versão**

**Entregue**

**Ficou de fora**

**Documentos especializados atualizados**

**Resumo para promoção ao PROJECT_CONTEXT**

**Data da promoção**
```

---

## 12. Checklist antes de implementar UI ou fluxo

- [ ] `PROJECT_CONTEXT.md` foi consultado.
- [ ] Este roadmap foi consultado.
- [ ] `UX_PRODUCT_STANDARD.md` foi consultado integralmente para a frente.
- [ ] O documento especializado do domínio foi consultado.
- [ ] A jornada principal está definida.
- [ ] Estados vazio, carregando, erro e sucesso estão definidos.
- [ ] Foco, teclado, hover e seleção estão definidos.
- [ ] Responsividade e densidade foram consideradas.
- [ ] Privacidade, custo e conteúdo enviado estão explícitos.
- [ ] Persistência local e recuperação foram definidas.
- [ ] Critérios de aceite são verificáveis.
- [ ] O que não pertence à fase está registrado.

---

## 13. Checklist de fechamento e promoção

- [ ] Implementação concluída.
- [ ] Testes técnicos executados.
- [ ] Validação visual executada quando aplicável.
- [ ] Jornada end-to-end validada.
- [ ] Critérios de UX atendidos.
- [ ] Privacidade e segurança revisadas.
- [ ] Escopo entregue e exclusões registrados.
- [ ] Commits e versão registrados.
- [ ] Documentos especializados atualizados.
- [ ] Resumo consolidado preparado.
- [ ] `PROJECT_CONTEXT.md` atualizado.
- [ ] Estado marcado como `Promoted to PROJECT_CONTEXT`.
- [ ] Registro preservado no histórico fechado.

---

## 14. Regra para novas contas e novas IAs

Uma nova IA não deve começar a implementar apenas com base em uma conversa isolada.

Ordem mínima:

1. ler `AGENTS.md` aplicável;
2. ler `docs/PROJECT_CONTEXT.md`;
3. ler `docs/FEATURE_VALIDATION_AND_ROADMAP.md`;
4. identificar a frente e seu status;
5. ler `docs/UX_PRODUCT_STANDARD.md` se houver qualquer impacto de UI/UX;
6. ler todos os documentos especializados listados na frente;
7. confrontar documentação com o código e o estado atual;
8. perguntar apenas o que for material e ainda não resolvido;
9. implementar sem misturar possibilidade, backlog e entrega;
10. retroalimentar este roadmap e promover somente após validação.

Para troca de conta ou handoff, consultar também:

- `docs/ACCOUNT_CONTINUITY_HANDOFF.md`;
- `docs/NEW_ACCOUNT_BOOTSTRAP_PROMPT.md`.

---

## 15. Estado inicial deste documento

Na criação desta submatriz:

- a transformação de transcript clean em documento estruturado foi definida como a frente mais importante da evolução atual;
- o Rich Study Workspace, comentários ancorados, referências de estudo, dicionário/glossário, persistência e exportação foram aprovados para refinamento;
- suporte operacional, telemetria, scheduler, webhooks e integrações foram reclassificados como backlog posterior ou possibilidades exploratórias;
- `PROJECT_CONTEXT.md` permanece como matriz principal e deverá apontar para este documento como fonte operacional das frentes não entregues;
- documentos especializados continuam com autoridade sobre seus domínios e devem ser consultados e atualizados conforme as regras acima.
