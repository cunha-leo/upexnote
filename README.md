# UpexNote

> Transcreva, organize e explore suas conversas.

UpexNote é o produto local-first de transcrição, contexto e estudo do ecossistema UpexFlow. A versão desktop atual é **0.28.0**.

## Estado atual

O produto já possui uma aplicação Windows instalada e validada, não apenas uma fundação ou protótipo. Estão entregues:

- transcrição de ficheiros de áudio e vídeo com múltiplos motores;
- preservação separada de transcript `raw` e conteúdo `clean` derivado;
- Biblioteca por utilizador, pesquisa, edição do clean, avisos, histórico e auditoria;
- identidade por e-mail/senha, Google e GitHub, recuperação de senha e MFA administrativo;
- administração hierárquica com Users, Activity, Audit, Telemetry, Support e Data Studio;
- telemetria opcional e anónima, sem conteúdo;
- suporte com chamados, comentários, estados, atribuições e evidências;
- Data Studio com catálogo, Visual Builder, SQL Editor, Saved Queries e diagramas ER;
- temas, densidade, tipografia, zoom e interface em PT/EN/ES.

O estado validado, o backlog imediato e o histórico de decisões vivem em [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md).

## Arquitetura resumida

```text
Desktop Tauri + React + TypeScript
              │ comandos Rust + eventos NDJSON
              ▼
Worker Python local empacotado como sidecar
  ├─ mídia, transcrição e armazenamento local
  ├─ Windows Credential Manager
  ├─ SQLite embutido
  └─ PostgreSQL administrativo por túnel SSH

API central FastAPI /v1 por HTTPS
  ├─ recuperação de senha e MFA
  ├─ tokens e telemetria consentida
  └─ suporte
              │
              ▼
PostgreSQL no EasyPanel/VPS
```

## Princípios obrigatórios

- Vídeo bruto permanece no local de origem e nunca é copiado automaticamente.
- Áudio só é enviado a um motor cloud após escolha explícita do utilizador.
- O transcript bruto é imutável; limpeza, edição, resumo, formatação e estudo são derivados identificados.
- Credenciais ficam no Windows Credential Manager ou em variáveis protegidas dos serviços; nunca no Git, em logs ou argumentos.
- Arquivos locais são preservados primeiro; falhas de serviços centrais não podem apagar ou bloquear o resultado local.
- Novos domínios PostgreSQL usam schemas separados e nomeados em inglês.
- UI/UX, acessibilidade, temas, estados e responsividade são requisitos arquiteturais.
- Administração usa menu lateral hierárquico, não abas horizontais como navegação principal.

## Estrutura

- `apps/desktop` — aplicação Tauri 2, React 19 e TypeScript.
- `services/worker` — sidecar Python, motores, identidade local, Biblioteca e Data Studio.
- `services/api` — API central FastAPI para identidade, MFA, telemetria, tokens e suporte.
- `ops/vps` — scripts versionados de backup, firewall e arquivo de evidências.
- `docs` — arquitetura, produto, UX, contexto vivo e ideias futuras.
- `storage` — conteúdo gerado pelo utilizador; ignorado pelo Git.

## Fonte de verdade e continuidade

Ler nesta ordem antes de alterar o projeto:

1. código e estado real do Git;
2. [`AGENTS.md`](AGENTS.md);
3. [`docs/PROJECT_CONTEXT.md`](docs/PROJECT_CONTEXT.md);
4. documentos arquiteturais específicos;
5. [`docs/UX_PRODUCT_STANDARD.md`](docs/UX_PRODUCT_STANDARD.md);
6. [`docs/FUTURE_PRODUCT_IDEAS.md`](docs/FUTURE_PRODUCT_IDEAS.md) e [`docs/AI_MEDIA_EVOLUTION.md`](docs/AI_MEDIA_EVOLUTION.md) apenas como possibilidades futuras.

Para continuidade entre contas ou agentes, consultar também [`docs/ACCOUNT_CONTINUITY_HANDOFF.md`](docs/ACCOUNT_CONTINUITY_HANDOFF.md).
