# UpexNote Data Studio

> Frente aprovada em 25 de julho de 2026. Este documento define os limites arquiteturais do módulo. O histórico de implementação e validação permanece em `PROJECT_CONTEXT.md`.

## Objetivo

O Data Studio é uma prateleira administrativa do UpexNote para explorar e, em fases posteriores, consultar, relacionar e automatizar dados PostgreSQL sem depender de uma ferramenta externa durante o uso do produto.

Ele nasce dentro do UpexNote, mas utiliza nomes e contratos genéricos para preservar uma possível extração futura como produto UpexFlow.

## Navegação

O módulo pertence à hierarquia existente:

```text
Administration
├─ Users
├─ Activity
├─ Audit
├─ Telemetry
├─ Support
└─ Data Studio
```

Não usa abas horizontais como navegação principal. Dentro do workspace, abas contextuais podem alternar representações do mesmo objeto, como dados, estrutura, relações e índices.

## Fundação v0.25, SQL Editor v0.26 e Saved Queries v0.27

A fundação v0.25.0 entregou a exploração somente leitura:

- conexão central já configurada;
- catálogo separado por schema;
- tabelas, tabelas particionadas, views e materialized views;
- colunas, tipos, nullability, defaults e primary keys;
- foreign keys inclusive entre schemas;
- índices;
- pesquisa no catálogo;
- leitura paginada, no máximo 100 linhas por chamada;
- filtro parametrizado por uma coluna;
- campos reconhecidamente sensíveis protegidos antes de sair do worker;
- UI em PT/EN/ES, responsiva e compatível com temas.

O construtor visual v0.25.1 acrescenta:

- seleção de campos para `SELECT`;
- condições combinadas por `AND` ou `OR`;
- `INNER`, `LEFT`, `RIGHT` e `FULL JOIN` no mesmo schema ou entre schemas;
- formulários para `INSERT`, `UPDATE` e `DELETE`;
- criação de tabela e alteração para adicionar, renomear ou excluir coluna;
- prévia SQL não editável com valores parametrizados e ocultos;
- resultado tabular, confirmação de mutações por hash do plano, transação e auditoria;
- bloqueio de `UPDATE` e `DELETE` sem condição.

A revisão v0.25.2 define a jornada principal como tabela → filtros → ordenação → execução → resultado inline. Campos específicos e joins são refinamentos no mesmo workspace; detalhes SQL ficam recolhidos e aliases internos não são apresentados como conceitos necessários ao utilizador.

A v0.26 acrescentou o editor PostgreSQL manual com autocomplete baseado no catálogo,
oito temas, três estilos de formatação, fontes configuráveis, execução protegida e
resultado inline.

A v0.27 acrescenta:

- biblioteca de consultas nomeadas, pesquisáveis e categorizadas;
- criação e edição a partir do SQL Editor;
- parâmetros `:nome` vinculados pelo driver, sem interpolação;
- preview e confirmação obrigatória para mutações;
- execução inline com limite de 500 linhas e mascaramento de campos sensíveis;
- histórico operacional sem guardar os valores dos parâmetros;
- arquivamento, restauração e exclusão explícita;
- armazenamento isolado em `data_studio.saved_queries` e
  `data_studio.saved_query_runs`.

Ainda não fazem parte desta fase:

- scheduler, jobs, eventos ou entregas;
- API, Webhooks ou conectores externos.

## Corredor de segurança

```text
UI administrativa
  → sessão elevada por MFA
  → comando Tauri em whitelist
  → payload por stdin
  → validação da sessão administrativa na API
  → revalidação de role=admin no PostgreSQL
  → operação protegida e auditável
```

- Credenciais permanecem no Windows Credential Manager.
- Identificadores são resolvidos no catálogo e compostos com `psycopg2.sql.Identifier`.
- Valores de filtro usam parâmetros.
- Schemas de sistema não aparecem.
- Só aparecem objetos para os quais o utilizador PostgreSQL possui `SELECT`.
- Colunas com nomes associados a password, token, secret, credential, salt e chaves privadas são mascaradas.
- SQL salvo fica restrito ao proprietário. Resultados e valores de parâmetros não
  são persistidos; o histórico guarda apenas operação, sucesso, duração e contagem.

## Evolução prevista

1. v0.26: SQL Editor manual com autocomplete local e execução protegida — concluído.
2. v0.27: Saved Queries e parâmetros no schema inglês isolado `data_studio` — concluído.
3. Scheduler, jobs, eventos e entregas.
4. APIs, Webhooks, CRM, n8n e conectores.

Cada fase exige autorização e critério de aceite próprios. A visão comercial e possibilidades não aprovadas continuam em `FUTURE_PRODUCT_IDEAS.md`.
