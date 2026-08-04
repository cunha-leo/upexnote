# UpexNote — Context Orchestration

> **Papel:** porta única e obrigatória de entrada para qualquer IA, agente, conta, ambiente ou nova sessão que precise compreender Leonardo, suas decisões e o projeto UpexFlow/UpexNote antes de propor ou executar trabalho.
>
> **Uso esperado:** em vez de reconstruir manualmente um prompt com vários arquivos, Leonardo pode instruir apenas: **“Leia `docs/CONTEXT_ORCHESTRATION.md` e siga integralmente suas coordenadas antes de agir.”**
>
> **Regra principal:** este documento coordena a ordem de leitura. Ele não substitui as fontes referenciadas e não autoriza implementação por si só.

---

## 1. Objetivo

Este documento elimina a necessidade de Leonardo repetir, em cada nova IA ou sessão, quais documentos devem ser lidos, em que ordem e com qual autoridade.

A contextualização deve reconstruir quatro camadas distintas e conectadas:

1. **Leonardo:** identidade operacional, método, critérios e forma de colaboração;
2. **decisões vivas:** momento pessoal e profissional, ramificações abertas, fechadas ou adormecidas;
3. **UpexFlow/UpexNote:** estado técnico e de produto consolidado;
4. **execução atual:** frentes aprovadas, validações, backlog, documentos especializados e retorno documental.

A IA somente estará contextualizada quando tiver percorrido as camadas aplicáveis, distinguido fatos de hipóteses e confrontado a documentação técnica com o estado real do repositório.

---

## 2. Ponto único de entrada

Toda nova sessão relevante deve começar por este arquivo.

```text
CONTEXT_ORCHESTRATION.md
  → Dossiê Leonardo Cunha
  → Contexto Vivo Portugal/Brasil
  → AGENTS.md aplicável
  → PROJECT_CONTEXT.md
  → FEATURE_VALIDATION_AND_ROADMAP.md
  → documentos especializados exigidos pela tarefa
  → código, Git e estado executável
  → proposta ou implementação autorizada
  → retroalimentação dos documentos de domínio
  → retorno ao roadmap
  → promoção ao PROJECT_CONTEXT.md
```

Não iniciar pelo código isoladamente, por uma conversa antiga ou por um único documento técnico quando esta porta de entrada estiver disponível.

---

## 3. Camada humana e decisória — Google Drive

Antes de descer para o projeto, consultar os dois documentos vivos localizados em:

```text
Google Drive
└─ My Drive
   └─ Documentos Desktop
      └─ Life
```

Ordem obrigatória:

1. `Dossie_Leonardo_Cunha_LIFE_v1.0.docx`
2. `Contexto_Vivo_Decisao_Portugal_Brasil_Leonardo_v2.3.docx`

### 3.1. Dossiê Leonardo Cunha

**Função:** explicar como Leonardo pensa, investiga, decide, trabalha, valida e colabora com IA.

A leitura deve preservar, entre outros pontos:

- Leonardo como integrador de sistemas e arquiteto de contexto, não reduzido a uma função técnica isolada;
- autoria humana de intenção, arquitetura, critérios, priorização e aceite;
- uso da IA como acelerador de investigação e implementação;
- método de partir da pergunta concreta, abrir variáveis e hipóteses, buscar evidências, confrontar a realidade, abstrair, podar e decidir;
- divergência para compreender, convergência para agir e documentação para reutilizar;
- preferência por continuidade, precisão, validação real e separação entre fato, hipótese e promessa.

### 3.2. Contexto Vivo

**Função:** atualizar as decisões humanas e profissionais que podem influenciar prioridades, disponibilidade, risco, direção comercial e critérios de escolha.

A leitura deve identificar:

- decisões vigentes;
- ramificações abertas;
- ramificações fechadas;
- hipóteses adormecidas e seus gatilhos de reabertura;
- mudanças desde a última sessão;
- relações legítimas entre o momento de Leonardo e o trabalho no UpexFlow.

O contexto pessoal orienta a colaboração e as decisões relevantes, mas não deve ser forçado artificialmente em tarefas técnicas sem relação.

---

## 4. Verificação de atualidade

Os dois documentos do Drive são vivos e podem ser retroalimentados por outro fluxo, conta ou IA.

Por isso:

- não confiar apenas em memória de uma sessão anterior;
- verificar a versão, data de alteração ou conteúdo mais recente disponível;
- reler quando houver nova sessão, nova ferramenta, troca de conta, handoff ou indício de atualização;
- numa sessão contínua e sem alteração dos arquivos, pode-se reutilizar o contexto já lido;
- quando houver dúvida razoável sobre atualização, prevalece a releitura;
- não assumir que o nome da versão no arquivo garante que o conteúdo local ou do Drive não mudou.

A IA deve informar com honestidade quando não tiver acesso a esses arquivos. Não deve fingir que os leu nem reconstruir detalhes ausentes por inferência.

---

## 5. Indisponibilidade dos documentos pessoais

Quando o ambiente não puder acessar o Google Drive ou os arquivos não forem fornecidos:

1. registrar explicitamente a limitação;
2. não inventar o contexto pessoal ou decisório;
3. solicitar acesso, anexação ou conteúdo somente quando isso for material para a tarefa;
4. para trabalho técnico seguro e já delimitado, continuar com o contexto do repositório, marcando a camada humana como não verificada;
5. não tomar decisões estratégicas, comerciais ou pessoais como se os documentos tivessem sido consultados;
6. reler e reconciliar assim que o acesso for restaurado.

Conteúdo pessoal, decisões sensíveis e documentos do Drive não devem ser copiados integralmente para Git, logs, issues ou commits.

---

## 6. Camada UpexFlow/UpexNote — sequência obrigatória

Depois da camada humana e decisória, descer para o repositório nesta ordem:

### 6.1. Regras locais

1. localizar e ler o `AGENTS.md` da raiz;
2. localizar qualquer `AGENTS.md` mais próximo dos arquivos afetados;
3. cumprir a regra mais específica aplicável ao caminho modificado.

### 6.2. Matriz consolidada

Ler `docs/PROJECT_CONTEXT.md` para compreender:

- estado real consolidado;
- versão e último estado validado;
- capacidades entregues;
- decisões vigentes;
- arquitetura e regras não negociáveis;
- histórico técnico e de produto;
- referências para documentos especializados.

O `PROJECT_CONTEXT.md` não é área livre de exploração. Ele recebe a verdade consolidada depois da entrega e validação.

### 6.3. Submatriz operacional

Ler `docs/FEATURE_VALIDATION_AND_ROADMAP.md` para compreender:

- frente aprovada atual;
- prioridade;
- estado de cada iniciativa;
- backlog posterior;
- possibilidades exploratórias;
- dependências e critérios de aceite;
- documentos de domínio obrigatórios;
- processo de retroalimentação e promoção.

Não tratar `Approved`, `Later Backlog` ou `Exploratory Possibilities` como funcionalidade já entregue.

### 6.4. Documentos especializados

Consultar apenas os documentos exigidos pelo domínio, sem deixá-los isolados:

- `docs/UX_PRODUCT_STANDARD.md`: qualquer UI, UX, layout, fluxo, acessibilidade ou front-end;
- `docs/ARCHITECTURE.md`: limites técnicos, módulos, serviços, persistência, filas e fronteiras;
- `docs/PRODUCT.md`: proposta de valor, público, jornada e direção de produto;
- `docs/AI_MEDIA_EVOLUTION.md`: formatação, estudo, IA, leitura, áudio, voz, idiomas e modo ao vivo;
- `docs/SUPPORT_ARCHITECTURE.md`: tickets, evidências, e-mail, SLA, suporte e arquivamento;
- `docs/DATA_STUDIO_ARCHITECTURE.md`: SQL, Saved Queries, scheduler, jobs, eventos, relatórios, webhooks e conectores;
- `docs/FUTURE_PRODUCT_IDEAS.md`: possibilidades ainda não aprovadas;
- `docs/ACCOUNT_CONTINUITY_HANDOFF.md`: mudança de conta, agente, ambiente ou transferência de contexto;
- `docs/NEW_ACCOUNT_BOOTSTRAP_PROMPT.md`: inicialização prática de uma nova conta ou IA;
- `README.md` e READMEs locais: execução, instalação e orientação do módulo.

O detalhamento de quando consultar e atualizar cada documento permanece em `FEATURE_VALIDATION_AND_ROADMAP.md`.

---

## 7. Confronto com a realidade técnica

Depois da leitura documental e antes de propor alteração:

- verificar o repositório, branch e worktree;
- preservar mudanças existentes;
- conferir histórico e versão atual;
- inspecionar o código relacionado;
- confirmar se a funcionalidade já existe total ou parcialmente;
- distinguir documentação vigente de implementação real;
- registrar divergências;
- não usar uma conversa antiga como fonte superior ao código e à matriz consolidada.

Ordem de autoridade para determinar o que existe:

1. comportamento executável e evidência validada;
2. código e estado do Git;
3. `PROJECT_CONTEXT.md`;
4. documento especializado do domínio;
5. `FEATURE_VALIDATION_AND_ROADMAP.md` para prioridade e estado futuro;
6. ideias e conversas históricas.

Uma divergência não deve ser escondida. Ela deve ser resolvida ou marcada antes de continuar.

---

## 8. Autorização e execução

Ler esta rede documental não equivale a autorização para alterar arquivos, infraestrutura ou serviços externos.

Antes de implementar, confirmar:

- pedido atual de Leonardo;
- escopo autorizado;
- estado da frente no roadmap;
- critérios de aceite;
- documentos obrigatórios;
- riscos e ações externas;
- necessidade de confirmação adicional para mudanças destrutivas ou sensíveis.

Durante a implementação:

- manter o roadmap retroalimentado;
- registrar decisões e desvios relevantes;
- atualizar o documento especializado quando seu contrato mudar;
- validar técnica, visual e funcionalmente conforme a natureza da frente;
- não promover uma feature antes de comprová-la.

---

## 9. Caminho de retorno documental

O fluxo não termina na implementação.

```text
implementação e testes
  → evidências e decisões
  → documento especializado afetado
  → FEATURE_VALIDATION_AND_ROADMAP.md
  → validação final
  → resumo consolidado
  → PROJECT_CONTEXT.md
  → continuidade para a próxima sessão
```

Regras:

- documentos especializados preservam contratos e decisões do domínio;
- o roadmap preserva descoberta, execução, escopo, evidências e fechamento;
- o `PROJECT_CONTEXT.md` recebe somente o estado consolidado e vigente;
- o registro fechado não é apagado do roadmap;
- os documentos pessoais só são atualizados por seu fluxo próprio e quando houver decisão humana real a registrar;
- uma mudança técnica não deve alterar o contexto pessoal por automatismo.

---

## 10. Contexto mínimo que a IA deve conseguir reconstruir

Antes de começar trabalho relevante, a IA deve conseguir explicar sem inventar:

- quem é Leonardo no processo de decisão e colaboração;
- como ele investiga, valida e aceita trabalho;
- quais decisões vivas podem ser pertinentes;
- o que é UpexFlow e o que é UpexNote;
- qual é a versão e o estado técnico atual;
- o que já foi entregue;
- qual é a frente aprovada;
- o que está apenas em backlog ou exploração;
- quais documentos governam a tarefa;
- quais limites de privacidade, dados, segurança e UX são obrigatórios;
- como a entrega será retroalimentada e promovida.

Se não conseguir responder a esses pontos, a contextualização está incompleta.

---

## 11. Prompt mínimo reutilizável

Para iniciar qualquer nova IA, sessão ou ambiente com acesso às fontes:

```text
Leia primeiro `docs/CONTEXT_ORCHESTRATION.md` e siga integralmente todas as coordenadas de leitura, verificação de atualidade, precedência e retorno documental. Não proponha nem implemente nada antes de concluir a contextualização aplicável e confrontá-la com o estado real do repositório. Ao terminar, apresente o contexto reconstruído, as limitações de acesso encontradas e aguarde ou execute apenas o escopo que eu autorizar.
```

Quando os documentos pessoais forem anexados diretamente à conversa, a mesma ordem deve ser preservada: Dossiê primeiro, Contexto Vivo depois.

---

## 12. Checklist de inicialização

- [ ] `CONTEXT_ORCHESTRATION.md` lido integralmente.
- [ ] Dossiê pessoal localizado e lido, ou indisponibilidade registrada.
- [ ] Contexto Vivo localizado e lido, ou indisponibilidade registrada.
- [ ] Atualidade dos dois documentos verificada.
- [ ] `AGENTS.md` aplicável lido.
- [ ] `PROJECT_CONTEXT.md` lido.
- [ ] `FEATURE_VALIDATION_AND_ROADMAP.md` lido.
- [ ] Documentos especializados da tarefa identificados e lidos.
- [ ] Código, Git, versão e worktree verificados.
- [ ] Divergências registradas.
- [ ] Estado entregue separado de backlog e exploração.
- [ ] Escopo e autorização confirmados.

---

## 13. Checklist de encerramento

- [ ] Implementação e validação registradas.
- [ ] Documento especializado atualizado quando necessário.
- [ ] Roadmap retroalimentado.
- [ ] Estado correto aplicado à frente.
- [ ] Resumo promovido ao `PROJECT_CONTEXT.md` quando validado.
- [ ] Commits, versão e evidências registrados.
- [ ] Nenhum conteúdo pessoal ou sensível copiado indevidamente para o repositório.
- [ ] Próxima sessão consegue retomar pelo mesmo ponto único de entrada.

---

## 14. Regra durável

A arquitetura documental deve permitir que Leonardo pare de reconstruir prompts longos.

Quando uma IA receber apenas a instrução para ler este arquivo, ela deve conseguir distribuir sozinha a leitura correta, reconstruir o contexto completo disponível, identificar o que falta, descer para a tarefa técnica e retornar pelas camadas documentais adequadas.
