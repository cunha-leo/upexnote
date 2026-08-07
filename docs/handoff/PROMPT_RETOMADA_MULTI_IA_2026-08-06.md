# Prompt de retomada — versão universal para outras IAs (ChatGPT, ChatGPT Work, Codex, Gemini, DeepSeek)

Cada documento tem caminho local E caminho web definidos explicitamente. A IA testa local primeiro; se não conseguir, tenta o caminho web equivalente (Drive ou GitHub conforme o tipo de documento); se nenhum dos dois funcionar, ela para, nomeia exatamente o documento que falhou, e pede pra Leonardo anexar/colar esse documento específico — nunca os dois de uma vez, e nunca segue adiante sem ele.

---

```text
Você está assumindo o contexto de um projeto pessoal e profissional de Leonardo Cunha, do zero, nesta conversa.

PASSO 0 — Identifique suas dependências de acesso, uma por uma
Antes de tentar ler qualquer documento, verifique nesta ordem para CADA um: (1) você consegue acessar o caminho local no sistema de arquivos? (2) se não, você consegue acessar o caminho web equivalente (Google Drive ou GitHub, conforme indicado)? (3) se nenhum dos dois funcionar, essa é uma dependência bloqueada — pare, diga exatamente qual documento não conseguiu acessar e por qual dos dois caminhos tentou, e peça pra Leonardo anexar ou colar esse documento específico nesta conversa. Não continue para o próximo documento fingindo que resolveu. Não presuma conteúdo de um documento que você não conseguiu abrir por nenhum dos dois caminhos.

LEI ABSOLUTA DESTA SESSÃO — não é sugestão, é regra indiscutível:
Cada documento da lista abaixo precisa ser lido INTEIRO, do início ao fim, linha por linha (ou do primeiro ao último caractere, se for conteúdo colado por Leonardo), e absorvido de verdade — não é permitido abstrair, resumir por cima, pular seção, escolher só o que parece relevante, ou parar antes do fim porque o conteúdo é longo. Vale pra todos, sem exceção. É a prioridade real desta conversa, acima de qualquer pressa em responder.

Autodeclaração sozinha de "li tudo" não vale nada sem prova (ver PASSO 6). Isso já falhou antes: um modelo anterior disse ter lido tudo e, na prática, pulou documentos inteiros.

Se o conteúdo vier cortado em partes (paginação, limite de contexto, limite de upload), continue pedindo ou processando a próxima parte até cobrir 100% do documento, sem pular trechos e sem inventar o que não foi mostrado a você.

═══════════════════════════════════════════════════════
DOCUMENTOS — CAMINHO LOCAL + CAMINHO WEB (nesta ordem exata de leitura)
═══════════════════════════════════════════════════════

BLOCO 1 — Camada humana e decisória (LIFE)

1. AGENTS.md (protocolo LIFE)
   Local: G:\My Drive\DocumentsDesktop\03-Life\00- Manifesto&Decisions\AGENTS.md
   Web: https://drive.google.com/file/d/1hQmOyDQeGO8TstT2gSRMstzs67I4kqup/view
   Ação: leia inteiro e execute o protocolo de inicialização LIFE nele descrito — ele manda localizar a versão mais alta dos 3 documentos abaixo dentro da pasta canônica antes de assumir qualquer versão fixa.

2. Dossiê/Manifesto LIFE (versão mais alta na pasta — na data desta escrita é v1.1)
   Local: G:\My Drive\DocumentsDesktop\03-Life\00- Manifesto&Decisions\Dossie_Leonardo_Cunha_LIFE_v1.1.docx
   Web: https://drive.google.com/file/d/1w2kt-lkk9bEt9h0uW7xTqAOVMpGQh0Gb/view
   Antes de ler, confira na pasta (local ou web) se existe versão mais alta que v1.1; se existir, use essa. Leia inteiro: todas as seções e apêndices, até a última linha.

3. Contexto Vivo de Decisão (versão mais alta na pasta — na data desta escrita é v2.8)
   Local: G:\My Drive\DocumentsDesktop\03-Life\00- Manifesto&Decisions\Contexto_Vivo_Decisao_Portugal_Brasil_Leonardo_v2.8.docx
   Web: https://drive.google.com/file/d/1aNIFmzRScLos5h_qEsysnyK3n9ypIDr5/view
   Antes de ler, confira se existe versão mais alta que v2.8; se existir, use essa. Leia inteiro: todas as partes (I a VI), todos os registros de decisão (RDs) em sequência, matriz de cenários e catálogo de fontes — não localizar por busca de palavra-chave.

4. Fio Condutor — Objetivo Central LIFE (v1.0)
   Local: G:\My Drive\DocumentsDesktop\03-Life\00- Manifesto&Decisions\Fio_Condutor_Objetivo_Central_v1.0.md
   Web: https://drive.google.com/file/d/1kRZ70tVILUZK8PaZ1a8JM9cngtYhQQmH/view
   Documento curto — leia inteiro, sem exceção.

BLOCO 2 — Camada técnica UpexFlow/UpexNote (repositório de código)

Repositório: https://github.com/cunha-leo/upexnote (branch main). Se o repositório for privado e você não tiver acesso, diga isso explicitamente e peça pra Leonardo colar o conteúdo do arquivo ou dar acesso.

5. docs/CONTEXT_ORCHESTRATION.md
   Local: C:\Users\cunha\Projects\upexflow\upexnote\docs\CONTEXT_ORCHESTRATION.md
   Web: https://github.com/cunha-leo/upexnote/blob/main/docs/CONTEXT_ORCHESTRATION.md
   Leia inteiro e siga as coordenadas dele.

6. AGENTS.md da raiz do repositório
   Local: C:\Users\cunha\Projects\upexflow\upexnote\AGENTS.md
   Web: https://github.com/cunha-leo/upexnote/blob/main/AGENTS.md

7. docs/PROJECT_CONTEXT.md
   Local: C:\Users\cunha\Projects\upexflow\upexnote\docs\PROJECT_CONTEXT.md
   Web: https://github.com/cunha-leo/upexnote/blob/main/docs/PROJECT_CONTEXT.md

8. docs/FEATURE_VALIDATION_AND_ROADMAP.md
   Local: C:\Users\cunha\Projects\upexflow\upexnote\docs\FEATURE_VALIDATION_AND_ROADMAP.md
   Web: https://github.com/cunha-leo/upexnote/blob/main/docs/FEATURE_VALIDATION_AND_ROADMAP.md

Para os 4 itens do Bloco 2: leia inteiro, do início ao fim, sem pular nada.

BLOCO 3 — Documentação visual/funcional do UpexNote (Google Drive, pasta "Product Strategy & Validation")

Pasta: https://drive.google.com/drive/folders/1rc10BnDk2P_XgLXjvp5xJVHyki2951Ip
Local: G:\My Drive\DocumentsDesktop\03-Life\04-Active Ventures\UpexFlow\UpexNote\Product Strategy & Validation\

9. UpexNote_CONTINUIDADE_DOCUMENTACAO_VISUAL.md
   Local: G:\My Drive\DocumentsDesktop\03-Life\04-Active Ventures\UpexFlow\UpexNote\Product Strategy & Validation\UpexNote_CONTINUIDADE_DOCUMENTACAO_VISUAL.md
   Web: https://drive.google.com/file/d/1oBF228zJl7t86bZu6kDNRb39or3uhBDw/view

10. UpexNote_Documentacao_Funcional_Visual_v1.0_FINAL (o documento principal — mais importante dos dois, não pode ficar de fora)
    Local: G:\My Drive\DocumentsDesktop\03-Life\04-Active Ventures\UpexFlow\UpexNote\Product Strategy & Validation\UpexNote_Documentacao_Funcional_Visual_v1.0_FINAL
    Web: https://drive.google.com/file/d/115uL4fiWH8LM_TtYvcToEFmsVmeJALsy/view
    Confira se existe versão mais alta que v1.0_FINAL na mesma pasta antes de ler; se houver, leia a mais recente.

Para os 2 itens do Bloco 3: leia inteiro, sem pular nada — são o registro de continuidade visual/funcional do produto.

BLOCO 4 — Documentos de domínio obrigatórios da frente ativa (ADF-01/ADF-02)

Todos dentro do mesmo repositório do Bloco 2 (mesmo local/web base):

11. docs/UX_PRODUCT_STANDARD.md
    Local: C:\Users\cunha\Projects\upexflow\upexnote\docs\UX_PRODUCT_STANDARD.md
    Web: https://github.com/cunha-leo/upexnote/blob/main/docs/UX_PRODUCT_STANDARD.md

12. docs/ARCHITECTURE.md
    Local: C:\Users\cunha\Projects\upexflow\upexnote\docs\ARCHITECTURE.md
    Web: https://github.com/cunha-leo/upexnote/blob/main/docs/ARCHITECTURE.md

13. docs/PRODUCT.md
    Local: C:\Users\cunha\Projects\upexflow\upexnote\docs\PRODUCT.md
    Web: https://github.com/cunha-leo/upexnote/blob/main/docs/PRODUCT.md

14. docs/AI_MEDIA_EVOLUTION.md
    Local: C:\Users\cunha\Projects\upexflow\upexnote\docs\AI_MEDIA_EVOLUTION.md
    Web: https://github.com/cunha-leo/upexnote/blob/main/docs/AI_MEDIA_EVOLUTION.md

Os 4 são obrigatórios porque o próprio FEATURE_VALIDATION_AND_ROADMAP.md os lista como documentos obrigatórios da ADF-01 — não escolha só os que parecem mais óbvios. Se identificar que a tarefa toca outro documento especializado do repositório, peça esse também antes de responder.

═══════════════════════════════════════════════════════

PASSO 5 — Confronto com o estado real (se tiver acesso ao repositório)
Depois da leitura documental completa: veja `git status`, `git log --oneline -20`, estrutura de `apps/`, `services/`, `docs/`. Se não tiver acesso a git/terminal, pule esta etapa e diga isso.

PASSO 6 — Prova de leitura (obrigatória, documento por documento, itens 1 a 14)
Para cada documento, ao marcá-lo como lido apresente:
- tamanho aproximado (linhas, páginas ou caracteres);
- confirmação de que cobriu do início ao fim sem pular partes;
- uma citação literal curta (entre aspas) do início, uma do meio e uma do final do conteúdo.
Sem isso, o item fica como "não concluído", mesmo que você "ache" que processou.

PASSO 7 — Contexto operacional de onde este trabalho parou
1. A frente ativa no UpexNote é a ADF-01 — Structured Document Generation, status `Ready`, com decisões de UX, modelo de dados, fluxo de execução e benchmark de motores de formatação de IA (DeepSeek, Grok, OpenAI, Anthropic, Gemini) já fechadas em 05–06/08/2026. ADF-02 (Rich Study Workspace) está `Approved`, acoplada.
2. Pendente antes de codar: confirmar limite de contexto/tokens e rate limit por provedor de formatação, considerando reuniões longas (cenário-teste até 1h30–2h).
3. Fora do UpexNote: uma frente paralela de avaliação de cursos de "mini apps/micro-SaaS" já foi fechada nesse mesmo dia (curso A cancelado e concluído; curso B com compra decidida) — está registrada no Contexto Vivo, é contexto de vida, não exige ação técnica aqui.

PASSO 8 — Resposta final
Só depois do checklist do PASSO 6 completo, com prova, responda com: (a) quais das 14 dependências você acessou local, quais via web, e quais ficaram bloqueadas e precisaram ser pedidas a Leonardo (PASSO 0); (b) resumo objetivo de quem é Leonardo e do estado atual do projeto; (c) a frente ativa e seu status; (d) o pendente do PASSO 7.2. Pergunte só o que for material e ainda não resolvido. Não proponha nem implemente nada nesta primeira resposta — só confirme que está pronto, com as provas de leitura, e aguarde a próxima instrução.
```
