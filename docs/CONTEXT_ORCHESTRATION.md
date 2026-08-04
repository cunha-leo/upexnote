# UpexNote — Context Orchestration

> **Papel:** porta única e obrigatória de entrada para qualquer IA, agente, conta, ambiente ou sessão que precise compreender Leonardo, suas decisões e o projeto UpexFlow/UpexNote antes de propor ou executar trabalho.
>
> **Uso esperado:** Leonardo pode instruir apenas: **“Leia `docs/CONTEXT_ORCHESTRATION.md` e siga integralmente suas coordenadas antes de agir.”**
>
> **Regra principal:** este documento coordena a ordem, a necessidade e a profundidade da leitura. Ele não substitui as fontes referenciadas e não autoriza implementação por si só.
>
> **Regra de eficiência:** documentos extensos que já estejam disponíveis na sessão na mesma versão não devem ser relidos integralmente. A IA deve verificar presença e versão, reler apenas quando necessário e registrar o que reutilizou.

---

## 1. Objetivo

Este documento elimina a necessidade de Leonardo reconstruir manualmente, em cada IA ou sessão, quais fontes devem ser lidas, em que ordem, com qual autoridade e quando podem ser reutilizadas.

A contextualização deve reconstruir quatro camadas distintas e conectadas:

1. **Leonardo:** identidade operacional, método, critérios e forma de colaboração;
2. **decisões vivas:** momento pessoal e profissional, ramificações abertas, fechadas ou adormecidas;
3. **UpexFlow/UpexNote:** estado técnico e de produto consolidado;
4. **execução atual:** frentes aprovadas, validações, backlog, documentos especializados e retorno documental.

A IA somente estará contextualizada quando tiver percorrido as camadas aplicáveis, distinguido fatos de hipóteses e confrontado a documentação técnica com o estado real do repositório.

---

## 2. Ponto único de entrada

Toda nova sessão relevante deve começar por este arquivo, mas a leitura das fontes seguintes é **condicional à presença, versão e atualidade**.

```text
CONTEXT_ORCHESTRATION.md
  → verificar presença e versão do Dossiê
  → verificar presença e versão do Contexto Vivo
  → ler ou reutilizar cada um conforme a regra de atualização
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

Os dois documentos vivos estão localizados em:

```text
Google Drive
└─ My Drive
   └─ Documentos Desktop
      └─ Life
```

Ordem lógica obrigatória:

1. `Dossie_Leonardo_Cunha_LIFE_v1.0.docx`
2. `Contexto_Vivo_Decisao_Portugal_Brasil_Leonardo_v2.3.docx`

A ordem permanece obrigatória quando houver leitura ou releitura. O Dossiê estabelece o método e a forma de colaboração; o Contexto Vivo aplica esse método às decisões humanas e profissionais atuais.

### 3.1. Dossiê Leonardo Cunha

**Versão de referência na criação desta regra:** `v1.0`.

**Função:** explicar como Leonardo pensa, investiga, decide, trabalha, valida e colabora com IA.

A leitura deve preservar, entre outros pontos:

- Leonardo como integrador de sistemas e arquiteto de contexto, não reduzido a uma função técnica isolada;
- autoria humana de intenção, arquitetura, critérios, priorização e aceite;
- uso da IA como acelerador de investigação e implementação;
- método de partir da pergunta concreta, abrir variáveis e hipóteses, buscar evidências, confrontar a realidade, abstrair, podar e decidir;
- divergência para compreender, convergência para agir e documentação para reutilizar;
- preferência por continuidade, precisão, validação real e separação entre fato, hipótese e promessa.

### 3.2. Contexto Vivo

**Versão de referência na criação desta regra:** `v2.3`.

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

## 4. Protocolo de presença, versão e releitura

O objetivo deste protocolo é manter o contexto atualizado sem desperdiçar janela de contexto, tokens, tempo ou processamento.

A IA deve avaliar **cada documento separadamente**.

### 4.1. Pode reutilizar sem releitura integral quando

Todos os pontos abaixo forem verdadeiros:

- o documento já foi lido integralmente nesta mesma sessão ou conversa persistente;
- o nome completo e a versão lida estão identificáveis no contexto da sessão;
- a versão disponível no Drive é igual à versão já lida;
- não existe indicação de que o conteúdo tenha sido alterado sem mudança de versão;
- o resumo contextual preservado é suficiente para a tarefa atual;
- não há dúvida material sobre uma seção específica.

Nesse caso, a IA deve:

1. registrar internamente ou na resposta de inicialização qual versão está reutilizando;
2. não reler o documento inteiro;
3. seguir para a próxima camada;
4. reler apenas trechos específicos se a tarefa exigir precisão adicional.

Exemplo:

```text
Dossiê v1.0 já lido e presente nesta sessão; versão atual permanece v1.0.
Reutilizar contexto existente e não reler integralmente.
```

### 4.2. Releitura integral obrigatória quando

Qualquer ponto abaixo for verdadeiro:

- o documento não está presente ou não foi lido nesta sessão;
- a IA não consegue identificar com segurança a versão já lida;
- a versão disponível é superior ou diferente da versão registrada na sessão;
- o nome do arquivo mudou de modo a sugerir nova edição;
- existe indicação de atualização relevante, mesmo sem mudança de versão;
- houve troca de conta, agente ou ambiente sem continuidade verificável;
- o contexto preservado está incompleto, contraditório ou insuficiente;
- Leonardo pede expressamente nova leitura integral.

Exemplos:

```text
Sessão contém Dossiê v1.0; Drive contém v1.1.
Ler integralmente v1.1 antes de continuar.
```

```text
Sessão não identifica qual versão do Contexto Vivo foi lida.
Ler a versão atual integralmente.
```

### 4.3. Releitura parcial permitida quando

- a versão permanece igual;
- o documento já foi lido integralmente;
- a tarefa exige apenas uma seção específica;
- existe dúvida localizada;
- foi informada alteração pontual sem nova versão.

A releitura parcial deve ser suficiente para reconciliar o ponto afetado, sem consumir novamente o documento inteiro.

### 4.4. Comparação de versão

A versão do nome do arquivo é o primeiro indicador de atualização:

- `v1.1` é posterior a `v1.0`;
- `v2.4` é posterior a `v2.3`;
- versões diferentes exigem leitura da mais recente;
- versões iguais permitem reutilização somente se não houver outro indício de alteração.

A IA não deve assumir que o número no nome é garantia absoluta. Quando disponível, deve também considerar data de modificação, metadados, manifesto, histórico de decisões ou aviso explícito de Leonardo.

### 4.5. Registro mínimo de contexto carregado

Ao concluir a inicialização, a IA deve conseguir declarar algo equivalente a:

```text
Contexto humano reutilizado: Dossiê v1.0 já presente na sessão.
Contexto decisório atualizado: Contexto Vivo v2.4 relido porque superava v2.3.
Contexto técnico: PROJECT_CONTEXT e roadmap verificados no estado atual do repositório.
```

Não é necessário repetir o conteúdo dos documentos; basta declarar versão, ação tomada e eventuais limitações.

---

## 5. Manifesto e decisões como indicadores de atualização

Quando a pasta `Life` possuir manifesto, índice, changelog ou arquivo de decisões que identifique versões e atualizações, ele deve ser consultado antes de abrir os documentos extensos.

Esse indicador deve responder, quando disponível:

- nome canônico do documento;
- versão atual;
- data de atualização;
- resumo das mudanças;
- necessidade de releitura integral ou parcial.

O manifesto reduz custo de verificação, mas não substitui a leitura quando as regras da seção 4 determinarem releitura obrigatória.

Se não houver manifesto acessível, comparar os nomes completos, versões, datas disponíveis e o contexto da sessão.

---

## 6. Indisponibilidade dos documentos pessoais

Quando o ambiente não puder acessar o Google Drive ou os arquivos não forem fornecidos:

1. registrar explicitamente a limitação;
2. não inventar o contexto pessoal ou decisório;
3. solicitar acesso, anexação ou conteúdo somente quando isso for material para a tarefa;
4. para trabalho técnico seguro e já delimitado, continuar com o contexto do repositório, marcando a camada humana como não verificada;
5. não tomar decisões estratégicas, comerciais ou pessoais como se os documentos tivessem sido consultados;
6. reler e reconciliar assim que o acesso for restaurado.

Conteúdo pessoal, decisões sensíveis e documentos do Drive não devem ser copiados integralmente para Git, logs, issues ou commits.

---

## 7. Camada UpexFlow/UpexNote — sequência obrigatória

Depois de ler ou reutilizar validamente a camada humana e decisória, descer para o repositório.

### 7.1. Regras locais

1. localizar e ler o `AGENTS.md` da raiz;
2. localizar qualquer `AGENTS.md` mais próximo dos arquivos afetados;
3. cumprir a regra mais específica aplicável ao caminho modificado.

### 7.2. Matriz consolidada

Ler `docs/PROJECT_CONTEXT.md` para compreender:

- estado real consolidado;
- versão e último estado validado;
- capacidades entregues;
- decisões vigentes;
- arquitetura e regras não negociáveis;
- histórico técnico e de produto;
- referências para documentos especializados.

O `PROJECT_CONTEXT.md` não é área livre de exploração. Ele recebe a verdade consolidada depois da entrega e validação.

### 7.3. Submatriz operacional

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

### 7.4. Documentos especializados

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

Documentos técnicos menores também podem ser reutilizados quando a mesma versão ou conteúdo já estiver presente na sessão, mas devem ser reabertos sempre que o código, a branch, o commit ou a tarefa puder ter alterado seu estado.

---

## 8. Confronto com a realidade técnica

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

## 9. Autorização e execução

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

## 10. Caminho de retorno documental

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

## 11. Contexto mínimo que a IA deve conseguir reconstruir

Antes de começar trabalho relevante, a IA deve conseguir explicar sem inventar:

- quais versões do Dossiê e do Contexto Vivo foram lidas ou reutilizadas;
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

## 12. Prompt mínimo reutilizável

```text
Leia primeiro `docs/CONTEXT_ORCHESTRATION.md` e siga integralmente suas coordenadas. Antes de reler documentos extensos, verifique se eles já estão presentes nesta sessão e compare a versão já lida com a versão atual. Reutilize o contexto quando a versão for a mesma e não houver indício de alteração; releia quando o documento estiver ausente, a versão for diferente ou superior, houver dúvida de atualidade ou eu solicitar. Depois confronte o contexto aplicável com o estado real do repositório. Não proponha nem implemente antes de concluir essa verificação e execute somente o escopo autorizado.
```

Quando os documentos pessoais forem anexados diretamente à conversa, a mesma ordem permanece: Dossiê primeiro, Contexto Vivo depois, observando a regra de versão.

---

## 13. Checklist de inicialização

- [ ] `CONTEXT_ORCHESTRATION.md` lido integralmente.
- [ ] Versão do Dossiê disponível identificada.
- [ ] Versão do Dossiê já presente na sessão identificada, quando houver.
- [ ] Decisão registrada: reutilizar, reler parcialmente ou reler integralmente o Dossiê.
- [ ] Versão do Contexto Vivo disponível identificada.
- [ ] Versão do Contexto Vivo já presente na sessão identificada, quando houver.
- [ ] Decisão registrada: reutilizar, reler parcialmente ou reler integralmente o Contexto Vivo.
- [ ] Indisponibilidades registradas honestamente.
- [ ] `AGENTS.md` aplicável lido.
- [ ] `PROJECT_CONTEXT.md` verificado.
- [ ] `FEATURE_VALIDATION_AND_ROADMAP.md` verificado.
- [ ] Documentos especializados da tarefa identificados e lidos quando necessários.
- [ ] Código, Git, versão e worktree verificados.
- [ ] Divergências registradas.
- [ ] Estado entregue separado de backlog e exploração.
- [ ] Escopo e autorização confirmados.

---

## 14. Checklist de encerramento

- [ ] Implementação e validação registradas.
- [ ] Documento especializado atualizado quando necessário.
- [ ] Roadmap retroalimentado.
- [ ] Estado correto aplicado à frente.
- [ ] Resumo promovido ao `PROJECT_CONTEXT.md` quando validado.
- [ ] Commits, versão e evidências registrados.
- [ ] Nenhum conteúdo pessoal ou sensível copiado indevidamente para o repositório.
- [ ] Próxima sessão consegue identificar quais versões contextuais foram usadas.
- [ ] Próxima sessão consegue retomar pelo mesmo ponto único de entrada.

---

## 15. Regra durável

A arquitetura documental deve permitir que Leonardo pare de reconstruir prompts longos sem obrigar cada sessão a reler conteúdos extensos desnecessariamente.

Quando uma IA receber apenas a instrução para ler este arquivo, ela deve conseguir:

1. distribuir sozinha a leitura correta;
2. verificar presença e versão das fontes extensas;
3. reutilizar contexto válido;
4. reler apenas o que mudou ou estiver ausente;
5. reconstruir o contexto completo aplicável;
6. identificar o que falta;
7. descer para a tarefa técnica;
8. retornar pelas camadas documentais adequadas.
