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

## 6. Data Studio — laboratório possível dentro do UpexNote

> Atualização: a fundação foi entregue na v0.25.0 e o construtor visual protegido na v0.25.1. O SQL Editor manual foi reservado à v0.26. O escopo vigente está em `DATA_STUDIO_ARCHITECTURE.md`; as demais expansões continuam exploratórias até autorização específica.

O Data Studio foi imaginado inicialmente como nova prateleira hierárquica dentro de `Administration`, abaixo dos módulos existentes. Ele atenderia à necessidade de consultar e administrar o PostgreSQL sem abrir ferramentas externas ou expor outras conexões profissionais durante reuniões.

Possível navegação:

```text
Administration
├─ Users
├─ Activity
├─ Audit
├─ Telemetry
├─ Support
└─ Data Studio
```

O laboratório no UpexNote deve seguir o visual, os temas, a acessibilidade e os padrões de UX existentes. PyQt ou PySide não são necessários: a interface pode permanecer em Tauri e React, utilizando o worker e serviços controlados para acessar o PostgreSQL.

## 7. Três caminhos de consulta

### 7.1. Visual Builder

Construção intuitiva por seleções, sem exigir SQL:

- escolher um ou vários schemas;
- selecionar tabelas do mesmo schema ou de schemas diferentes;
- escolher colunas;
- relacionar campos;
- definir `INNER`, `LEFT`, `RIGHT`, `FULL` ou `CROSS JOIN`;
- criar relações temporárias mesmo sem foreign key;
- adicionar filtros, grupos, agregações e ordenação;
- gerar e exibir o SQL correspondente;
- executar e exportar resultados.

Os controles devem se adaptar aos tipos dos campos: datas, números, textos, booleanos e relações.

### 7.2. SQL Editor

Editor interno para construir consultas manualmente:

- SQL livre;
- múltiplas consultas;
- execução da seleção ou script;
- formatação e realce de sintaxe;
- parâmetros;
- histórico e favoritos;
- cancelamento, timeout e limite;
- resultados tabulares;
- `EXPLAIN`;
- exportação.

O autocomplete não precisa de IA nem de API externa. Pode utilizar Monaco Editor ou CodeMirror e o catálogo PostgreSQL carregado localmente para sugerir schemas, tabelas, colunas, aliases, relações, funções e palavras-chave.

Consultas visuais podem ser abertas no editor. Quando uma alteração manual não puder mais ser representada integralmente pelo construtor visual, a interface deve informar isso sem modificar ou perder o SQL.

### 7.3. Saved Ad Hocs

Consultas personalizadas e recorrentes podem ser salvas como ativos executáveis:

- nome e descrição;
- SQL versionado;
- origem visual ou manual;
- schemas e tabelas envolvidos;
- parâmetros;
- autor;
- categoria ou pasta;
- favorito;
- estado: rascunho, ativo, pausado ou arquivado;
- última edição e execução.

Ações fundamentais:

```text
Executar | Editar | Excluir/Arquivar
```

Também podem existir duplicação, histórico, exportação, atalhos e versões anteriores.

Consultas parametrizadas podem gerar formulários automaticamente:

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

## 8. Exploração e gestão de dados

Possibilidades do Data Studio:

- navegador de conexões, schemas, tabelas, views, colunas, índices e constraints;
- relações e chaves estrangeiras;
- dados paginados;
- filtros, busca e ordenação;
- seleção de colunas;
- visualização de uma ou várias tabelas relacionadas;
- exportação CSV, JSON, XLSX e outros formatos futuros;
- inserção e edição de registros;
- criação de tabelas, colunas, índices e constraints;
- preview do SQL antes de alterações;
- transações e rollback quando possível;
- confirmação reforçada para operações destrutivas.

A primeira versão, caso autorizada, deve começar somente leitura. Escrita, DDL e deleção exigem desenho adicional de permissões, confirmação e auditoria.

## 9. Scheduler, jobs e eventos

Um Ad Hoc pode futuramente receber agendamentos:

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
├─ Saved Ad Hocs
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
dados/Ad Hoc → transformação → Webhook/API → CRM/n8n/outro sistema
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
├─ Saved Ad Hocs
├─ Execution Engine
├─ Scheduler
├─ Events
├─ Automations
├─ Connectors
└─ Deliveries
```

O UpexNote seria um adaptador/consumidor desse núcleo, não sua única razão de existir.

## 12. Isolamento e segurança

Caso o Data Studio seja desenvolvido:

- domínio novo usa schema PostgreSQL próprio e em inglês, possivelmente `data_studio`;
- somente administradores elevados por MFA acessam operações administrativas;
- modo inicial somente leitura;
- escrita liberada explicitamente e por sessão;
- timeout, cancelamento e limites padrão;
- operações visuais usam parâmetros;
- alterações destrutivas mostram preview e exigem confirmação;
- credenciais nunca aparecem na interface, SQL, logs ou histórico;
- Audit registra ator, alvo, tipo e resultado sem copiar conteúdo privado;
- resultados completos não são persistidos indiscriminadamente;
- entregas externas exigem destino e consentimento explícitos.

Possível estrutura futura:

```text
data_studio.saved_queries
data_studio.query_versions
data_studio.query_parameters
data_studio.query_folders
data_studio.execution_history
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
