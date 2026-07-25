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

## Fundação v0.25.0

A primeira entrega é estritamente somente leitura:

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

Não fazem parte desta versão:

- SQL livre;
- criação do schema `data_studio`;
- consultas salvas;
- escrita, `UPDATE`, `DELETE` ou DDL;
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
  → operação somente leitura
```

- Credenciais permanecem no Windows Credential Manager.
- Identificadores são resolvidos no catálogo e compostos com `psycopg2.sql.Identifier`.
- Valores de filtro usam parâmetros.
- Schemas de sistema não aparecem.
- Só aparecem objetos para os quais o utilizador PostgreSQL possui `SELECT`.
- Colunas com nomes associados a password, token, secret, credential, salt e chaves privadas são mascaradas.
- Nenhuma consulta ou resultado é gravado nesta fase.

## Evolução prevista

1. SQL Editor somente leitura com autocomplete local.
2. Saved Ad Hocs e parâmetros no schema inglês isolado `data_studio`.
3. Visual Builder com relações e joins entre schemas.
4. Escrita controlada, transações e auditoria.
5. Scheduler, jobs, eventos e entregas.
6. APIs, Webhooks, CRM, n8n e conectores.

Cada fase exige autorização e critério de aceite próprios. A visão comercial e possibilidades não aprovadas continuam em `FUTURE_PRODUCT_IDEAS.md`.
