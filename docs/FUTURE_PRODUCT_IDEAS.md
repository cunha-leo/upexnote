# UpexFlow — ideias e possibilidades futuras

> **Natureza deste documento:** registro exploratório de ideias, hipóteses e direções possíveis.  
> **Não representa:** backlog aprovado, compromisso de implementação, cronograma, preço definido ou decisão arquitetural vigente.  
> O estado real do UpexNote continua documentado em `PROJECT_CONTEXT.md`.

## 1. Intenção

O UpexNote nasceu de uma necessidade pessoal real: transformar reuniões, aulas, vídeos e áudios em material que possa ser consultado, compreendido e reutilizado. A experiência profissional do seu criador em ambientes corporativos complexos mostrou que muitas ferramentas resolvem partes isoladas do problema, mas deixam para a pessoa o esforço de organizar o fluxo completo.

O projeto pode continuar como uma aplicação pessoal, construída para necessidades próprias, sem obrigação de se tornar um negócio. Ao mesmo tempo, deve preservar a possibilidade de evoluir para um produto comercial caso o uso por outras pessoas demonstre procura real.

O princípio para esta fase é:

> Construir primeiro uma ferramenta pessoal excelente, mantendo aberta — e não presumida — a possibilidade de produto.

## 2. Possível posicionamento do UpexNote

Uma ferramenta generalista de IA pode transcrever, resumir ou explicar conteúdos mediante arquivos e prompts. A possível diferenciação do UpexNote não está apenas no uso de IA, mas na transformação dessas tarefas numa jornada permanente e especializada:

```text
arquivo
  → transcrição
  → biblioteca
  → leitura e organização
  → contexto e pontos importantes
  → estudo, quiz e chat ancorado
  → histórico, pesquisa e exportação
```

Possíveis valores do produto:

- aplicação desktop instalada e controlada pela pessoa;
- operação local-first;
- material bruto preservado;
- nada enviado automaticamente a serviços externos;
- escolha explícita de motores locais ou cloud;
- uso opcional de chaves próprias;
- biblioteca permanente, em vez de respostas dispersas em conversas;
- conteúdos derivados claramente separados do transcript original;
- armazenamento no computador ou Drive escolhido;
- organização para trabalho, reuniões, ensino e estudo;
- exportação e portabilidade, evitando aprisionamento.

Quando um motor cloud for escolhido, o produto deve informar claramente qual conteúdo será enviado, para qual serviço e com que possível impacto de custo e privacidade.

## 3. Comercialização como possibilidade, não obrigação

Não há decisão de comercializar o UpexNote. Algumas possibilidades discutidas permanecem registradas apenas para avaliação futura.

### 3.1. Assinatura de baixo valor

- planos mensal, trimestral, semestral ou anual;
- desconto progressivo por pagamento antecipado;
- processamento variável por chaves próprias ou créditos separados;
- produto autônomo, com onboarding e diagnóstico suficientes para reduzir suporte repetitivo.

### 3.2. Licença permanente

- pagamento único;
- aplicação continua utilizável na versão adquirida;
- correções da linha comprada;
- novas versões ou período adicional de atualizações poderiam ser opcionais e pagos;
- instalação de uma nova versão preserva dados e configurações.

### 3.3. Modelo híbrido

- aplicação base por pagamento único;
- funcionalidades ou serviços Pro opcionais;
- créditos de processamento cloud;
- renovação opcional de atualizações;
- configuração assistida, onboarding e sessões de produtividade cobrados separadamente.

Qualquer preço discutido foi apenas ilustrativo. Preço, planos e canal de venda só devem ser definidos depois de validar utilização e disposição real de pagamento.

## 4. Suporte compatível com produto de baixo valor

Se houver comercialização, o produto deve minimizar dependência de atendimento humano por meio de:

- instalação e atualização simples;
- onboarding retomável;
- mensagens de erro úteis;
- diagnóstico consentido;
- vídeos curtos e central de ajuda;
- guias por objetivo;
- recuperação de conta e cobrança automatizadas;
- solução das causas recorrentes diretamente no produto.

O suporte básico a bugs, conta, cobrança, privacidade e segurança não deve ser confundido com serviços pagos. Serviços opcionais podem incluir:

- configuração assistida;
- orientação sobre motores e custos;
- organização inicial do ambiente;
- aula individual;
- consultoria de produtividade.

Credenciais e chaves continuam pertencendo exclusivamente ao utilizador. Mesmo numa sessão assistida, a própria pessoa deve criar e inserir os segredos sem os entregar ao atendente.

## 5. UpexFlow como possível família de produtos

UpexFlow pode futuramente reunir produtos independentes originados de necessidades reais. Essa visão não significa que todos devam ser construídos nem desenvolvidos em paralelo.

Possibilidades levantadas:

- **UpexNote:** transcrição, compreensão, organização e estudo;
- **UpexFlow Data Studio:** consulta, relacionamento, transformação e automação de dados;
- **plataforma de aprendizagem imersiva:** conteúdos baseados em vídeo, diálogos, filmes, música, atividades e múltiplas formas de aprendizagem;
- ferramentas futuras para problemas operacionais de profissionais e pequenos negócios.

O valor da marca-pai seria permitir que produtos compartilhassem princípios, identidade e componentes sem perder limites de domínio.

## 6. Data Studio — laboratório entregue dentro do UpexNote

> Atualização: o laboratório foi entregue da v0.25 à v0.28. Visual Builder, SQL Editor, Saved Queries e ER Diagram já existem. O escopo vigente está em `DATA_STUDIO_ARCHITECTURE.md`; somente as expansões posteriores continuam exploratórias.

O Data Studio é uma prateleira hierárquica de `Administration`. Ele permite consultar e administrar o PostgreSQL sem abrir ferramentas externas ou expor outras conexões profissionais durante reuniões.

Navegação entregue:

```text
Administration
├─ Users
├─ Activity
├─ Audit
├─ Telemetry
├─ Support
└─ Data Studio
```

O laboratório segue o visual, os temas, a acessibilidade e os padrões de UX do UpexNote. A interface permanece em Tauri e React e utiliza o corredor protegido do worker para acessar o PostgreSQL.

## 7. Três caminhos de consulta

### 7.1. Visual Builder

Entregue: construção intuitiva por seleções, sem exigir SQL, com:

- catálogo por schema e seleção de tabelas do mesmo schema ou de schemas diferentes;
- escolher colunas;
- relacionar campos;
- definir `INNER`, `LEFT`, `RIGHT` ou `FULL JOIN`;
- criar relações de consulta mesmo sem foreign key;
- combinar condições por `AND` ou `OR` e definir ordenação;
- gerar prévia SQL não editável com valores parametrizados;
- executar `SELECT` e mutações protegidas com resultado inline;
- criar tabela e adicionar, renomear ou excluir coluna.

Agregações, agrupamentos, `CROSS JOIN` e exportações tabulares além da cópia atual continuam possibilidades posteriores, não capacidades entregues.

### 7.2. SQL Editor

Entregue: editor CodeMirror PostgreSQL com:

- uma instrução por execução;
- formatação, realce de sintaxe, folding e correspondência de parênteses;
- autocomplete local baseado no catálogo permitido;
- fontes, tamanhos e temas próprios do editor;
- timeout e limite de resultados;
- execução protegida de leitura e mutações;
- resultados tabulares inline.

O autocomplete não usa IA nem API externa. Ele utiliza CodeMirror e o catálogo PostgreSQL já filtrado para sugerir schemas, tabelas, colunas e palavras-chave.

Múltiplas instruções/scripts, execução de seleção parcial, cancelamento, exportações e integrações continuam possibilidades futuras.

### 7.3. Saved Queries

Entregue na v0.27: consultas personalizadas podem ser salvas como ativos executáveis com:

- nome e descrição;
- SQL editável;
- parâmetros seguros na notação `:nome`;
- proprietário;
- categoria;
- estado ativo ou arquivado;
- pesquisa, restauração e exclusão explícita;
- histórico operacional sem valores de parâmetros nem resultados persistidos.

Ações fundamentais:

```text
Executar | Editar | Excluir/Arquivar
```

Duplicação, favoritos, pastas, versionamento e exportações permanecem possibilidades futuras.

As consultas parametrizadas geram campos para os parâmetros identificados:

```sql
SELECT *
FROM support.tickets
WHERE created_at BETWEEN :start_date AND :end_date
  AND status = :status;
```

```text
Data inicial  [          ]
Data final    [          ]
Status        [Todos  ▼]

[Executar]
```

Os valores devem ser vinculados como parâmetros, nunca concatenados diretamente no SQL.

## 8. Exploração e gestão de dados — estado atual

Já estão entregues:

- navegador de schemas, tabelas, views, colunas, índices e relações;
- relações e chaves estrangeiras;
- dados paginados;
- filtros, busca e ordenação;
- seleção de colunas;
- visualização de uma ou várias tabelas relacionadas;
- inserção e edição de registros;
- criação de tabelas e alterações de coluna permitidas;
- preview do SQL antes de alterações;
- transações para mutações;
- confirmação reforçada para operações destrutivas.

A v0.25.0 começou somente leitura. Escrita, DDL e deleção foram acrescentadas depois com sessão MFA, revalidação administrativa, parâmetros, preview, hash de confirmação, transação e auditoria sem valores privados. Criação de índices/constraints, exportações CSV/JSON/XLSX e modelagem visual com geração de SQL continuam futuras.

## 9. Scheduler, jobs e eventos

Uma Saved Query pode futuramente receber agendamentos:

- execução única, diária, semanal ou mensal;
- fuso horário;
- parâmetros fixos ou relativos;
- próxima e última execução;
- duração, quantidade de linhas e resultado;
- retry e histórico de erro;
- exportação e entrega.

Exemplo:

```text
Resumo semanal de suporte
Toda segunda-feira às 08:00
America/Sao_Paulo
Exportar XLSX
Enviar para destinatários autorizados
```

O scheduler não deve depender de o desktop estar aberto. A aplicação configura e monitora; um serviço central executa continuamente.

Conceitos distintos:

- **job:** execução por horário ou recorrência;
- **evento:** execução em resposta a algo ocorrido no sistema;
- **trigger PostgreSQL:** reação dentro do banco.

Triggers não devem enviar e-mails nem executar tarefas pesadas diretamente. O padrão futuro deve registrar trabalho numa fila para processamento controlado.

## 10. APIs, Webhooks e automações externas

O desenvolvimento de Webhooks pode permanecer posterior ao Data Studio, porque consultas, eventos, parâmetros e automações fornecerão contratos mais concretos para integrações.

Possível organização futura:

```text
Data Studio
├─ Explorer
├─ Visual Builder
├─ SQL Editor
├─ Saved Queries
├─ Automations
│  ├─ Schedules
│  ├─ Events
│  └─ Jobs
└─ Integrations
   ├─ API
   ├─ Incoming Webhooks
   ├─ Outgoing Webhooks
   ├─ Field Mappings
   └─ Delivery Logs
```

Fluxos possíveis:

```text
site/CRM → Webhook/API → validação → mapeamento → fila → dados
dados/Saved Query → transformação → Webhook/API → CRM/n8n/outro sistema
```

Integrações futuras devem prever autenticação, contratos versionados, idempotência, assinaturas, retry, limites, dead-letter queue, histórico e proteção de payloads.

## 11. Possível evolução para UpexFlow Data Studio

O laboratório pode futuramente ser extraído do UpexNote e tornar-se serviço ou aplicação comercial independente:

```text
UpexFlow Data Studio
├─ bancos de dados
├─ CRMs
├─ sites e formulários
├─ APIs e Webhooks
├─ n8n e outras plataformas
├─ e-mail
└─ aplicações UpexFlow
        ↓
catálogo e dados relacionados
        ↓
consultas, dashboards e relatórios
        ↓
jobs, eventos e automações
        ↓
entregas e integrações
```

O produto poderia:

- conectar CRMs e bancos;
- receber leads e eventos de sites;
- alimentar sistemas externos;
- consolidar dados de marketing e operações;
- gerar dashboards;
- automatizar relatórios;
- enviar e-mails;
- integrar-se ao n8n e ferramentas semelhantes;
- servir como camada de dados para pequenos e médios negócios.

Para preservar essa opção, um núcleo futuro deve usar modelos genéricos e evitar acoplamento direto a transcripts ou suporte:

```text
Data Studio Core
├─ Connections
├─ Catalog
├─ Query Engine
├─ Visual Query Builder
├─ Saved Queries
├─ Execution Engine
├─ Scheduler
├─ Events
├─ Automations
├─ Connectors
└─ Deliveries
```

O UpexNote seria um adaptador/consumidor desse núcleo, não sua única razão de existir.

## 12. Isolamento e segurança — base entregue e extensões futuras

O corredor atual já aplica:

- schema PostgreSQL próprio e em inglês, `data_studio`;
- somente administradores elevados por MFA acessam operações administrativas;
- escrita e DDL apenas pelas operações explicitamente permitidas;
- timeout e limites padrão;
- operações visuais usam parâmetros;
- alterações destrutivas mostram preview e exigem confirmação;
- credenciais nunca aparecem na interface, SQL, logs ou histórico;
- Audit registra ator, alvo, tipo e resultado sem copiar conteúdo privado;
- resultados e valores de parâmetros não são persistidos no histórico.

Extensões futuras devem manter as mesmas garantias e acrescentar:

- cancelamento controlado de execuções longas;
- entregas externas exigem destino e consentimento explícitos.

Objetos existentes e possíveis extensões:

```text
data_studio.saved_queries             # entregue
data_studio.saved_query_runs          # entregue
data_studio.query_versions
data_studio.query_parameters
data_studio.query_folders
data_studio.schedules
data_studio.schedule_runs
data_studio.delivery_targets
data_studio.delivery_history
data_studio.event_bindings
data_studio.automation_queue
```

## 13. Critério para transformar ideias em produto

Estas ideias não devem entrar automaticamente no backlog. Uma possibilidade só se torna frente aprovada quando houver:

- necessidade pessoal ou problema externo claramente observado;
- jornada e utilizador definidos;
- limites de privacidade e segurança;
- escopo inicial pequeno;
- critério de aceite;
- autorização explícita para implementação.

Para uma eventual comercialização:

- utilização recorrente por pessoas além do criador;
- benefício percebido;
- disposição real de pagamento;
- custos e suporte sustentáveis;
- ausência de conflito contratual ou uso de informação protegida;
- decisão consciente entre produto pessoal, licença, assinatura ou serviço.

## 14. Direção atual

No presente, UpexNote pode permanecer uma aplicação pessoal. O desenvolvimento deve priorizar aquilo que melhora diretamente o trabalho e o estudo do seu criador.

As possibilidades comerciais e os produtos futuros ficam preservados neste documento como visão, sem pressionar o projeto a executá-los. A regra é manter opcionalidade:

> Se outras pessoas demonstrarem a mesma necessidade, a base estará preparada para evoluir. Se isso não acontecer, o UpexNote continuará tendo valor como ferramenta pessoal.

## 15. IA, leitura e mídia

As capacidades futuras de Formatação, Estudo, leitura em voz alta, velocidades de reprodução, vozes, idiomas, sincronização por palavra, inteligência de conteúdo e modo ao vivo estão consolidadas em `AI_MEDIA_EVOLUTION.md`.

Esse documento deve ser consultado antes de implementar formatação, leitura/edição, player de áudio, text-to-speech, timestamps por palavra, Action Items, novos idiomas ou agentes de voz.
