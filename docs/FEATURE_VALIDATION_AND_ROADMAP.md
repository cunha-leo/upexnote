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

**Status:** `In progress` (passo 1 — backend do worker — entregue em 07/08/2026, commit `0929d66`; UI/Settings/popup ainda fora deste passo, ver "Passo 1 entregue" abaixo).

**Prioridade:** máxima na evolução atual do produto.

**Problema:** o UpexNote já entrega transcript raw e clean com qualidade, rastreabilidade e segurança, mas a jornada ainda termina predominantemente no transcript. O utilizador precisa transformar a conversa em material organizado sem copiar o conteúdo para várias ferramentas externas.

**Objetivo:** transformar o transcript clean em um documento estruturado, legível e reutilizável, preservando o vínculo com a fonte.

**Jornada-base:**

```text
áudio ou vídeo
  → transcript raw imutável
  → transcript clean validado
  → validação de integridade raw ↔ clean (checagem de que nenhum contexto se perdeu na limpeza)
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

**Decisões fechadas (05/08/2026):**

- **Modelo interno do documento:** o usuário nunca vê Markdown cru. A interface é um editor rico, tipo "bloco de notas inteligente" (estilo Word), renderizado a partir de um modelo estruturado (blocos/seções com dados persistidos, não texto solto).
- **Formato de persistência:** não é apenas uma tabela nova — é um esquema novo, tratado como submódulo próprio (mesmo padrão de submenus expansíveis da Administration). SQLite local recebe o schema para o usuário pessoal; o Postgres central recebe o schema equivalente para o lado administrativo/multiusuário. Modelo hub-and-spoke por ID: uma tabela matriz de documento, com comentários, referências e glossário pendurados nela por ID, com exclusão em cascata ou soft-delete seguindo o padrão já usado no resto do sistema.
- **Entrada na UI:** na tela de Transcribe/Library, botões novos (ex.: "Documento formatado", "Estudo") levam à área de edição. Cada botão precisa de uma frase de incentivo/microcopy abaixo, no mesmo espírito visual do aviso de salvar no Google Drive/OneDrive — convidativa, não só funcional (ver `UX_PRODUCT_STANDARD.md` no desenho da tela).
- **Etapa de validação raw ↔ clean:** antes de qualquer geração de documento formatado, o sistema cruza raw e clean para confirmar que nenhum contexto foi perdido na limpeza. Só depois dessa validação passar o clean segue para a formatação.
- **Perfis iniciais de transformação:** a base sempre nasce do clean (nunca do raw). A partir daí, variantes via botão — resumo técnico, versão detalhada, formatação de estudo — lista extensível, não fechada nesta fase.
- **Contrato entre clean, documento e referências:** referência por bloco. Cada seção do documento é um container editável com ID de bloco estável, ponto de ancoragem para comentários, balões e futuras funcionalidades (adicionar, remover, etc.). Preferido a âncora por palavra (frágil a texto repetido e a edição) ou por busca textual.
- **Motor inicial e benchmark:** este é um benchmark novo, distinto do benchmark de transcrição áudio→texto já feito — aqui o motor recebe texto (clean) e produz documento estruturado. Candidatos comparados: AssemblyAI e Deepgram (versões/modelos novos, inclusive os de voz), GPT, Claude, Gemini, DeepSeek, Grok. Critério: baixo custo e velocidade, com o mesmo rigor usado quando o motor de transcrição principal foi escolhido.
- **Comportamento diante de conteúdo ambíguo ou incompleto:** o clean já trata ruído, tempo morto e repetição preservando contexto — isso não muda. A camada nova é de reorganização temática: título, objetivo em uma frase, quebra por seção/tema (não necessariamente cronológica — a mesma ideia pode reaparecer espalhada ao longo da reunião e precisa ser agrupada), sinalizando densidade de jargão técnico, sem perder a essência do conteúdo original.
- **Transparência de custo na UI:** na tela onde o usuário escolhe o motor — tanto na etapa de transcrição (áudio→texto) quanto na etapa de formatação (clean→documento estruturado) — cada opção deve mostrar nome do modelo e custo médio estimado por hora de transcript processado (R$/hora), não só o nome do fornecedor. Objetivo: o usuário decide com fidelidade e custo visíveis lado a lado, sem precisar ir até a tela de configuração de chaves de API pra entender o que está escolhendo.
- **Fluxo de execução na tela de Transcribe (06/08/2026):** a escolha do motor de formatação acontece no mesmo momento em que o usuário escolhe o motor de transcrição, não depois. A tela de Transcribe ganha uma segunda seção, logo abaixo da seção de seleção de motor de transcrição, para seleção de motor de formatação. Ao executar, o sistema já roda as duas etapas em sequência (transcrição → validação raw↔clean → formatação) e entrega o documento estruturado pronto de uma vez, sem uma segunda ida do usuário à tela.
  - **Opção "somente transcrição":** a seção de formatação precisa ter uma opção explícita de pular a formatação (ex.: toggle "Formatar depois" ou motor "Nenhum"), pra quem só quer o transcript limpo agora e decide formatar depois.
  - **Formatação retroativa (tela de edição/biblioteca, não a tela de Transcribe):** cenário separado — usuário tem um transcript já existente (gerado antes, ou que ficou sem formatação) e quer só rodar a etapa de formatação nele. Isso não acontece na tela de Transcribe; é uma ação na tela de edição/biblioteca, permitindo selecionar/subir um transcript existente e escolher o motor de formatação sobre ele, reaproveitando os mesmos botões "Documento formatado"/"Estudo" já decididos para essa tela.
  - **Motor padrão de formatação e fricção zero (06/08/2026):** o motor/chave de formatação é configurado uma única vez em Configurações (categorizado por finalidade, ver decisão de arquitetura acima). A partir daí, qualquer ação de formatar em qualquer lugar do app (pós-transcrição ou retroativa) executa direto, sem pedir chave/engine de novo a cada clique.
  - **Botão pós-transcrição quando "só transcrição" foi escolhida:** ao terminar de transcrever sem formatação, aparece um botão fixo (não popup) — "Formatar" como verbo de ação, com "Estudo" como um dos perfis/destinos dentro dele (reaproveitando os perfis "Documento formatado"/"Estudo" já decididos). Clicar executa na hora com o motor padrão já configurado.
  - **Popup só na primeira vez:** um modal explicativo (o que é cada perfil, qual motor, custo estimado, opção de marcar como padrão) só aparece na primeiríssima vez que o usuário aciona formatação sem ter um motor padrão configurado ainda. Depois disso, nunca mais — vira automático.

**Resultados do benchmark de formatação (06/08/2026), transcript de teste com ~5,3 min de áudio (voz única):**

| Motor | Modelo | Custo por hora de transcript |
| --- | --- | --- |
| DeepSeek | `deepseek-chat` (V4-Flash) | R$ 0,04/hora |
| Grok | `grok-4-fast` | R$ 0,05/hora |
| OpenAI | `gpt-5-mini` | R$ 0,28/hora |
| Claude | Haiku 4.5 | R$ 0,54/hora |
| Gemini | `gemini-3.6-flash` | R$ 1,48/hora |
| Claude | Sonnet 5 | R$ 1,62/hora |

Nenhum motor alucinou ou perdeu informação do transcript nesse teste. AssemblyAI (LeMUR descontinuado, substituto exige upgrade pago) e Deepgram Read (só inglês, não gera documento estruturado) foram descartados. Falta rodar a mesma bateria com um transcript de múltiplas vozes antes de fechar o motor padrão.

**Achado adicional (06/08/2026):** Gemini e Grok evoluíram em 2026 para suportar transcrição de áudio nativamente nas próprias APIs (Gemini via `generateContent` multimodal; Grok via Voice/STT API dedicada, com diarização e timestamp por palavra already embutidos). Isso os torna candidatos também para a etapa de transcrição (não só formatação), o que pode simplificar o pipeline (potencialmente unir transcrição + estruturação num motor só). Claude e DeepSeek não têm API de áudio — seguem só como motores de formatação de texto. Ainda não testados como motores de transcrição — pendente.

**Teste de transcrição multi-falante (06/08/2026), 2 min de reunião real com ruído e mistura PT/EN:**

- **Grok STT**: 2,7s, diarização nativa por palavra, R$ 0,51/hora. Qualidade duvidosa nesse áudio ruidoso — alucinou um trecho inteiro sem sentido (pareceu húngaro, provável confusão com ruído de fundo) e a diarização ficou desequilibrada.
- **Gemini (multimodal)**: 22,3s, sem diarização estruturada mas identificou falantes por prompt de forma coerente com a conversa, texto mais legível e sensato. R$ 2,82/hora (~5,5x mais caro que o Grok).
- Os dois textos divergem entre si em números e nomes — validação de fidelidade real exige o usuário ouvir o áudio e comparar, não dá pra decidir só por velocidade/custo.

**Comparação com AssemblyAI como referência (06/08/2026), mesmo trecho de 2 min:** rodado o motor já em produção (AssemblyAI, com diarização) no mesmo áudio pra servir de baseline de fidelidade.

- **Grok**: alucinação óbvia e grosseira — inventou uma abertura inteira que não existe no áudio, inventou uma frase completa no meio da fala, e transformou um trecho real em texto sem sentido (pareceu húngaro). Fácil de detectar por ser nonsense evidente.
- **Gemini**: alucinação mais perigosa — texto fluente e coerente, mas com nomes próprios inventados que não existem na referência (pessoas, times, siglas plausíveis mas fabricadas). Mais arriscado que o do Grok justamente por parecer confiável.
- **AssemblyAI**: confirmado pelo usuário como essencialmente 100% fiel nesse teste — os trechos mais confusos do texto não são erro do motor, e sim uma ligação de telefone real sobreposta no meio da gravação (áudio genuinamente difícil, não falha de transcrição). Não inventou nomes nem frases.

**Conclusão:** Grok e Gemini não passaram no teste de validade para a etapa de transcrição — alucinaram em áudio real. A transcrição permanece com o motor atual (AssemblyAI), sem adicionar outros motores a essa etapa.

**Benchmark de formatação com transcript real e completo (06/08/2026)**, ~20 min de reunião, 4 falantes, muita conversa paralela misturada com conteúdo técnico — teste de estresse real, não sintético:

| Motor | Custo por hora de transcript |
| --- | --- |
| DeepSeek | R$ 0,02/hora |
| Grok | R$ 0,03/hora |
| OpenAI (`gpt-5-mini`) | R$ 0,10/hora |
| Claude Haiku 4.5 | R$ 0,21/hora |
| Gemini (`gemini-3.6-flash`) | R$ 0,51/hora |
| Claude Sonnet 5 | R$ 0,73/hora (preço promocional até 31/08/2026) |

Todos os seis extraíram corretamente a história principal (tabela de taxas, processo "voada", Apex, responsáveis, reunião marcada) sem inventar fatos novos. Diferenciador é profundidade/organização, não fidelidade — Claude Sonnet foi o mais completo (separou explicitamente conteúdo de trabalho de conversa pessoal), Claude Haiku usou até tabela markdown pra responsabilidades, Grok foi o mais enxuto (cortou parte da conversa pessoal).

**Decisão corrigida (06/08/2026): não escolher um único motor padrão de formatação.** Os seis motores passaram no teste e ficam todos disponíveis na aplicação — o usuário escolhe qual usar na hora (com nome do modelo + custo/hora visível, conforme a decisão de transparência de custo já registrada acima). Não há hierarquia fixa de "padrão vs. alternativa"; a única curadoria é informativa (ex.: destacar o mais barato e o mais completo como sugestão, não como obrigação).

**Decisão de arquitetura (06/08/2026) — configuração de chaves por finalidade:** a tela de configuração de chaves de API deve categorizar cada chave pela função (motor de transcrição áudio→texto vs. motor de formatação texto→documento), não só pelo fornecedor. Um mesmo fornecedor (ex.: OpenAI, Anthropic, Gemini) pode aparecer nas duas categorias se suportar as duas funções; DeepSeek e Claude só aparecem em formatação (sem API de áudio); AssemblyAI e Deepgram só aparecem em transcrição. Uma vez a chave configurada, o pipeline já sabe pra que serve sem perguntar de novo. Fluxo confirmado: áudio → motor de transcrição (raw) → clean → validação raw↔clean → motor de formatação escolhido pelo usuário → documento estruturado.

**Pendente antes de codar (RESOLVIDO 07/08/2026):** a preocupação com limite/quota por execução deixou de se aplicar — decisão fechada de não fazer chunking/fragmentação nesta etapa; transcripts reais testados (~5 a ~20 min) ficam muito abaixo da janela de contexto de qualquer um dos 6 provedores. Sem chunking, sem necessidade de checar rate limit por enquanto.

**Disciplina de entrega:** implementar em fatias pequenas — uma ou duas funcionalidades complementares por vez, build, versão nova, commit e push, seguindo o mesmo padrão incremental já visível no histórico do `PROJECT_CONTEXT.md`. Não acumular funcionalidades grandes numa única versão não lançada.

**Passo 1 entregue (07/08/2026) — backend do worker, commit `0929d66`:**

- **Formatação (`transcription/formatting.py`):** os 6 motores decididos acima implementados e chamáveis (DeepSeek, Grok, `gpt-5-mini`, Claude Haiku 4.5, Claude Sonnet 5, Gemini), com prompt/parsing comuns para o documento em blocos (title/objective/blocks/jargon). Sem motor padrão, como decidido.
- **Gate raw↔clean (`transcription/doc_validation.py`):** heurística v1 por razão de palavras (documentada como heurística, não diff semântico) — bloqueia formatação se o clean perdeu conteúdo além do esperado por remoção de ruído/repetição.
- **Chaves por finalidade (`transcription/credentials.py`):** `DEEPSEEK_API_KEY`, `GROK_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY` novas, todas categorizadas em `KEY_PURPOSES` (transcrição/formatação/ambas) — pré-requisito direto da futura tela de Configurações por finalidade decidida acima.
- **Persistência (`transcription/db.py`):** schema hub-and-spoke novo (`structured_documents` + satélites `document_blocks`/`document_glossary`/`document_metrics` + `documents_history`), SQLite e Postgres, espelhando o padrão de `transcriptions`. Motores de formatação entraram na mesma dimensão `engines` (coluna `kind`).
  - **⚠ Desvio de arquitetura encontrado e CORRIGIDO (07/08/2026, commit `3f341fc`):** a decisão de 05/08/2026 acima diz explicitamente "é um esquema novo" (Postgres) para este submódulo, no mesmo espírito de `support`/`data_studio`. As tabelas tinham nascido em `public`; o utilizador autorizou a migração. `db.py` agora cria/referencia `documents.structured_documents` + satélites (SQLite local sem mudança — sem conceito de schema). Nova função idempotente `migrate_documents_schema()` + comando `db-migrate-documents-schema` movem (`ALTER TABLE ... SET SCHEMA`) as tabelas já existentes sem perder dados. Validado ponta a ponta em SQLite antes do commit. **Falta rodar uma vez contra a VPS real** (fora do alcance de rede do ambiente onde o código foi escrito) para mover os documentos #1–#9 já existentes — comando: `python -m transcription.cli db-migrate-documents-schema`.
- **CLI (`transcription/cli.py`):** `format-engines` (lista motores), `format --engine --profile` (chama um motor isolado, sem persistir), `document-generate --transcription-id --engine --profile` (formatação retroativa — carrega raw/clean já existentes, valida, formata, salva; é o mecanismo por trás do botão retroativo da Biblioteca decidido acima), `transcribe --format-engine --format-profile` (encadeia transcrição + validação + formatação numa só chamada — é o mecanismo por trás do fluxo decidido em 06/08/2026 para a tela de Transcribe). Novo evento NDJSON `format_error`: uma falha na formatação nunca desfaz/invalida a transcrição já gravada com sucesso.
- **Evidência/teste:** os 6 motores testados pelo utilizador na própria máquina, com chaves e transcripts reais (não sintéticos) — um vídeo técnico de ~18 min (lógica de negócio de emissão de passagens) e uma aula de curso próprio de ~12 min. Sem alucinação detectada em nenhum motor. Achado real durante o teste: `gpt-5-mini` rejeita `temperature` custom (só aceita o default 1) — corrigido tornando `temperature` opcional em `_run_openai_compatible`. Também confirmado nos testes reais de 07/08/2026 que `grok-4-fast` e `deepseek-chat` continuam ativos (contrariando o risco de descontinuação anotado antes). Fluxo encadeado `transcribe --format-engine` testado ponta a ponta com áudio real, documento salvo no Postgres da VPS.
- **Fora deste passo (próximo trabalho):** UI (botões "Documento formatado"/"Estudo" na Biblioteca e na tela de Transcribe), popup de primeira vez, tela de Configurações para motor padrão de formatação por finalidade. **Pendência operacional (não é feature nova):** rodar `db-migrate-documents-schema` uma vez contra a VPS real.

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

**Cenários de camada (ainda hipótese, não decisão fechada):**

- **Solo / Local-First / BYOK:** usuário baixa o executável, configura a própria chave de API, banco SQLite local, licença única ou anual. Custo de infraestrutura para quem vende é praticamente zero.
- **Família / Equipe Pequena:** executável conectando a um banco leve compartilhado ou gerenciado, para poucos usuários relacionados.
- **Corporativa / Managed Enterprise:** infraestrutura instalada na nuvem do cliente (VPS, Docker, PostgreSQL, painel administrativo), com fee mensal de sustentação.

Um quarto pacote foi cogitado (derivado da camada corporativa) mas ainda não foi definido; retomar quando houver clareza.

**Nota de posicionamento (GTM, não feature):** as camadas acima não são mutuamente exclusivas. É possível manter uma oferta low ticket (licença solo) e, ao mesmo tempo, perseguir contratos high ticket vendendo o produto como segurança e soberania de dados — chave de API e transcript nunca saem da máquina do usuário — para público que paga caro por sigilo (advocacia, saúde, consultorias, estudantes em ambiente de estudo seguro). Isso é uma decisão de mensagem/pitch (`PRODUCT.md`), não uma frente de implementação, e deve ser tratada como hipótese até validação de mercado.

---

### EP-06 — Link/URL Ingestion for Transcription

**Status:** `Exploring`

**Objetivo:** permitir que o usuário cole um link (YouTube, Vimeo, entre outras plataformas de vídeo) e o sistema obtenha o conteúdo para transcrição, sem exigir download manual prévio.

**Caminhos possíveis a explorar:**

- extração do áudio a partir do link para processar pela mesma cadeia de transcrição já existente;
- em plataformas que expõem transcript próprio (ex.: aba de transcript do YouTube, disponível publicamente para qualquer vídeo), avaliar leitura direta e segura desse texto como atalho, em vez de reprocessar áudio;
- suporte pode variar por plataforma; não presumir que todo provedor permite as duas rotas.

**Riscos a validar antes de qualquer implementação:**

- termos de serviço de cada plataforma (extração de áudio ou scraping de transcript pode violar ToS dependendo do provedor);
- direitos autorais do conteúdo de terceiros;
- estabilidade de qualquer integração não-oficial (pode quebrar sem aviso).

Permanece possibilidade exploratória; não é backlog imediato nem promessa de implementação.

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
