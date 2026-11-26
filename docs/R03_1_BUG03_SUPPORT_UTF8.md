# R03.1 BUG-03 — Diagnóstico e correção da codificação no Suporte (26/11/2026)

**Estado: RESOLVIDO na base ativa em produção.** Não se trata de nova funcionalidade.

## Evidência e diagnóstico

O defeito havia sido identificado no R03: texto de teste com acento exibido como sequências de caracteres corrompidos. Ao retomar o R03.1, verificou-se que o caminho do desktop Tauri para o worker Python já estabelece explicitamente `PYTHONUTF8=1` e `PYTHONIOENCODING=utf-8`; o cliente da API converte JSON de saída para UTF-8 e decodifica respostas explicitamente como UTF-8.

A inspeção **somente leitura** ocorreu no serviço que atende de fato à produção: `upexflow_upexnote-api`, com 1/1 réplica, usando `PostgresSupportRepository` e uma sessão PostgreSQL marcada como read-only.

Resultado inicial: um chamado, uma descrição e um comentário na base consultada. Nenhum comentário apresentava o marcador de corrupção. **Uma descrição** (`support.ticket_descriptions.ticket_id=1`) já continha o defeito **no conteúdo persistido**. Não era erro do CSS da interface nem da resposta JSON atual.

## Correção de dados, pontual e reversível

1. A condição original exata foi verificada: `Isso Ã© um teste`, conversível de forma unívoca para `Isso é um teste` por reversão de interpretação Latin-1/UTF-8.
2. O valor original, o novo valor e respetivos hashes foram guardados **somente no Recovery privado**, no arquivo `R03.1-BUG03-SUPPORT-SNAPSHOT-2026-11-26.json`. Nenhum conteúdo de utilizador foi publicado no Git.
3. Uma transação PostgreSQL limitada ao chamado `UN-000001` guardou o estado anterior em `support.ticket_audit` (ação `historical_encoding_repair`, auditoria ID 3) e fez **um UPDATE condicionado ao valor exato anterior**.
4. A própria transação confirmou o novo valor. Em seguida, a leitura via `PostgresSupportRepository.ticket_detail(1)` confirmou o resultado já persistido após commit.

Após o UPDATE, uma segunda inspeção somente leitura contabilizou **zero comentários e zero descrições com os marcadores de corrupção** usados no diagnóstico, na base do serviço ativo. Nenhuma transcrição, nota, outra descrição ou comentário foi reescrito. A correção é idempotente e rejeita valores inesperados.

## Regressões e produção

- Dois testes no cliente do worker cobrem o JSON UTF-8 de envio e o retorno de comentários/descrições com acentos e travessões.
- Dois testes na API FastAPI, com repositório falso, cobrem request/response Unicode sem manipular produção.
- Suíte do worker: **46 testes aprovados**; novos testes da API: **2 aprovados**.
- API de produção: HTTPS `/health` respondeu `status=ok`, serviço com 1/1 réplica.
- O sistema **não aplica descodificação retroativa indiscriminada** a qualquer mensagem. Dados legítimos que contenham `Ã` devem permanecer intactos.

## Suporte no tema Nord (BUG-02)

O título do Suporte não se relaciona com o BUG-03. A correção CSS `.support-view > h2 { background: transparent; color: var(--text-dim); }` está no stylesheet de release; Nord usa tokens `--panel: #3b4252` e `--text-dim: #aeb8cc`. O seletor tem especificidade superior à regra genérica `.card h2`. **Validado estaticamente, sem aceite visual específico do proprietário**. Não apresentar isso como homologação visual.

## Limites

Este registo descreve o universo de dados da base ativa consultada em 26/11/2026, não auditoria de qualquer backup ou outra organização. O arquivo original de recuperação R03 e os demais checkpoints foram preservados. Nenhum segredo, token ou valor de autenticação foi incluído aqui.
