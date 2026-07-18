# UpexNote — Contexto Vivo do Projeto

> **Objetivo deste documento:** manter uma fonte de verdade legível por pessoas e IAs. Deve ser atualizado a cada decisão, teste relevante, alteração estrutural ou mudança de estado. Não contém chaves, vídeos, áudios privados nem transcrições sensíveis.

**Última atualização:** 18 de julho de 2026 (v0.14.0 — identidade completa: tabela users + login social, item 13-C)  
**Produto:** UpexNote  
**Ecossistema:** UpexFlow  
**Repositório:** `https://github.com/cunha-leo/upexnote` (privado) — **fonte de verdade e sincronização**  
**Raiz local de desenvolvimento:** `C:\Users\cunha\Projects\upexflow\upexnote` (disco local; ver Registro 2026-07-12 (c) sobre a saída do Google Drive)

---

## 1. Resumo executivo

UpexNote é uma aplicação local-first que transforma vídeos e áudios em transcripts, contexto estruturado e material de estudo. Ela nasceu para substituir um fluxo manual de scripts de terminal usado para transcrever reuniões com português de Portugal, português do Brasil e inglês técnico misturados.

O protótipo anterior comprovou a qualidade dos motores de transcrição e dos mecanismos de validação. O projeto atual começa a transformação desse protótipo numa aplicação visual, acessível, moderna e evolutiva.

O foco imediato é **transcrição de ficheiros** (vídeo/áudio já existente). Captura de áudio ao vivo e tradução simultânea são fases posteriores.

---

## 2. Marca e produto

- **UpexFlow**: ecossistema de automações e desenvolvimento do proprietário.
- **UpexNote**: produto de transcrição, contexto e estudo.
- **Frase inicial:** “Transcreva, organize e explore suas conversas.”
- O nome deve sempre ser escrito como `UpexNote`, sem espaço.

Evolução prevista de capacidades:

1. Transcrição de arquivo.
2. Biblioteca, leitura e edição de transcript.
3. Resumo, contexto, decisões, ações e riscos.
4. Material de estudo, fluxos, tabelas, infográficos e quiz.
5. Chat ancorado no material e pesquisa explícita quando solicitada.
6. Reprodução do áudio e síntese de voz de conteúdos derivados.
7. Captura ao vivo com microfone + loopback do sistema.
8. Tradução e experiências multilíngues em tempo real.

---

## 3. Problema que o produto resolve

O utilizador participa em reuniões e trabalha com vídeos que podem misturar PT-PT, PT-BR e inglês técnico. O transcript nativo de ferramentas de reunião tem qualidade insuficiente nesse cenário. Produtos prontos resolvem parte do problema, mas incluem funcionalidades desnecessárias e mensalidade elevada.

O produto precisa preservar o transcript real para consulta, exportação e uso em outras IAs, sem impedir que o mesmo conteúdo seja transformado em resumos, contexto e materiais mais agradáveis para leitura/estudo.

---

## 4. Princípios não negociáveis

1. **O transcript bruto é o artefacto de referência.** Camadas de resumo, limpeza, contexto ou estudo nunca podem substituir ou alterar silenciosamente o original.
2. **Vídeo bruto permanece local.** Nunca deve ser copiado automaticamente para Google Drive, GitHub, VPS ou APIs.
3. **Áudio também é sensível por defeito.** Só é enviado a um serviço cloud quando o utilizador escolhe expressamente um motor cloud.
4. **Chaves ficam no Windows Credential Manager.** Nunca em `.env` publicado, Git, logs, screenshots ou texto de chat.
5. **Custos e privacidade devem ser visíveis antes de processar.**
6. **Resultados de IA precisam de validação real.** Não adotar recomendações apenas por documentação ou promessa de fornecedor; testar em arquivos representativos.
7. **Acessibilidade e dark/light mode são requisitos de produto**, não acabamento tardio.

---

## 5. Testes de transcrição já realizados

### Cenários avaliados

- Vídeo de aproximadamente 20 minutos com PT-PT, PT-BR, inglês técnico e conversa por dispositivo de sala.
- Vídeo de aproximadamente 24 minutos, reunião Teams predominantemente em português, vários participantes e microfones individuais.

### Conclusões por motor

| Motor | Resultado consolidado | Papel atual |
|---|---|---|
| **AssemblyAI Universal-3.5 Pro** | Melhor resultado nos dois vídeos: boa fluidez, code-switching PT/EN, nomes/números, diarização, zero loops e melhor custo observado. | Motor principal para arquivos. |
| **OpenAI whisper-1** | Muito rápido, barato e robusto em conteúdo predominantemente monolingue após pipeline v2; tem limitação arquitetural de idioma por trecho e pode errar inglês inserido em reunião PT. | Alternativa económica/monolingue. |
| **Deepgram Nova-3** | Bom candidato para baixa latência e code-switching, mas qualidade geral/diarização menos consistente que AssemblyAI nos testes. | Alternativa e candidato para futuro ao vivo. |
| **Whisper local large-v3** | Privado e sem custo marginal; melhor configuração local foi `large-v3`, CPU, `beam_size=1`, VAD. Não atingiu tempo real no hardware testado. | Modo privado/offline. |
| **gpt-4o-transcribe** | Pode entender bem trechos curtos PT/EN, mas apresentou loops graves e perda de conteúdo em transcrições longas. | Não usar como motor principal; possível revisor de trechos curtos no futuro. |

### Proteções construídas no protótipo

- chunking de áudio em pontos de silêncio;
- mapa de timestamps de áudio compactado de volta para a linha de tempo original;
- preservação de transcript `raw` e `clean`;
- validação de timestamps crescentes, cobertura e conteúdo;
- deteção de repetições e frases conhecidas de alucinação;
- correção importante: repetição curta plausível em despedidas de reuniões não é necessariamente alucinação; loops só são marcados quando a repetição é fisicamente implausível ou excessiva;
- blocos de 300 segundos foram o ponto ótimo empírico para `whisper-1`; 60 e 180 segundos pioraram a estabilidade.

---

## 6. Arquitetura alvo

### Decisão: local-first com interface web moderna

UpexNote não será apenas uma página cloud nem um executável Tkinter simples. A direção é uma interface visual baseada em tecnologias web modernas, com um worker nativo local.

```text
Interface moderna (Tauri + React/TypeScript)
                |
Worker local (Python, inicialmente)
  ├─ escolha e leitura de arquivos do computador
  ├─ extração temporária de áudio
  ├─ pipelines de transcrição testados
  ├─ armazenamento de credenciais via Windows Credential Manager
  └─ futura captura WASAPI: microfone + áudio do sistema
                |
Google Drive opcional / Postgres VPS posterior
```

O navegador sozinho pode pedir microfone e compartilhamento de tela/aba, mas não serve como base confiável para capturar de forma automática o Teams ou todo o áudio do sistema. A futura transcrição ao vivo exige componente local com WASAPI loopback.

### Por que não usar apenas web/cloud?

- O arquivo de vídeo bruto pode conter conteúdo corporativo e não deve sair da máquina.
- A captura ao vivo precisa acessar microfone e loopback de áudio do Windows.
- Interface web continua sendo desejada por estética, leitura, acessibilidade e velocidade de evolução; ela roda localmente dentro do app/shell.

---

## 7. Política de dados e armazenamento

| Tipo de dado | Local | Google Drive | VPS/Postgres | GitHub |
|---|---|---|---|---|
| Código e documentação técnica | Sim | Pasta de trabalho sincronizada | Não | Sim, repositório privado |
| Vídeo bruto | Sim, local de origem | Não por padrão | Não | Nunca |
| Áudio temporário | Cache local, removível | Não por padrão | Não | Nunca |
| Áudio para motor cloud | Só por ação explícita | Não obrigatório | Não | Nunca |
| Transcript bruto | Sim | Sim, se utilizador optar | Posteriormente, opcional | Nunca |
| Contexto, notas e exportações | Sim | Sim, se utilizador optar | Posteriormente, metadados/sync | Nunca |
| Credenciais | Windows Credential Manager | Nunca | Nunca | Nunca |

### Estrutura local atual

```text
C:\Users\cunha\Projects\upexflow\upexnote
├─ apps/desktop/        interface do UpexNote (Tauri + React)
├─ services/worker/     pipelines locais e integração de mídia (Python)
├─ docs/                documentação de produto e engenharia
├─ storage/             conteúdo gerado pelo utilizador (ignorado pelo Git)
├─ README.md
└─ .gitignore
```

O seletor de arquivos deverá aceitar qualquer caminho do Windows. Selecionar um vídeo de um Drive corporativo/pessoal não significa copiá-lo para a pasta do projeto.

### Organização do storage (transcripts)

Convenção (a partir de 2026-07-12, ver Registro (e)):

```text
storage/transcripts/<AAAA-MM-DD>/<motor>/<origem>__<AAAA-MM-DD>__<motor>__<kind>.txt
```

- Pasta por **dia** (topo), depois por **motor** — fácil de encontrar pelo dia; motores nunca se misturam.
- O **nome do ficheiro** carrega origem + data + motor + tipo (`clean`/`raw`), para se identificar sozinho mesmo fora da pasta.
- **Sem compressão/zip.** Transcripts são texto (~20 KB cada); 10.000 transcrições ≈ 500 MB. O espaço nunca é o problema — só a organização. Zipar prejudicaria a busca e não pouparia nada relevante.
- **Espaço:** os vídeos brutos (centenas de MB cada) NUNCA entram no storage; só o texto. O espaço não é motivo para banco de dados.
- **Histórico/dashboards e durabilidade (decisão revista 2026-07-12, ver Registro (f)):** usar o **Postgres já existente na VPS** (Docker), NÃO um SQLite local. Motivos: reutilizar ambiente (evitar segunda tecnologia), durabilidade fora da máquina (se o portátil morre, os dados não morrem — os scripts já estão no GitHub) e análise (custo por motor, motor mais usado, tempo de processamento, atividade). Guardrails: o ficheiro local continua a ser o artefacto primário (gravado primeiro; a escrita no Postgres é best-effort e sincroniza depois se a VPS estiver em baixo); o próprio Postgres precisa de dump/backup (uma VPS também é ponto único de falha). **Pendente de decisão do utilizador:** se o TEXTO do transcript vai para a VPS ou só os metadados (privacidade de conteúdo sensível), e o caminho de rede (túnel SSH vs porta exposta com firewall/TLS). Password do Postgres no Windows Credential Manager, como as chaves API.

---

## 8. Infraestrutura existente

### Disco local (desenvolvimento)

- Raiz de desenvolvimento: `C:\Users\cunha\Projects\upexflow\upexnote` (disco local, fora de qualquer sincronização em nuvem).
- **O código NÃO fica no Google Drive.** A partir de 2026-07-12, o desenvolvimento saiu do Drive (ver Registro (c)): o Google Drive File Stream não suporta as escritas do `node_modules`/build e o `git`+GitHub já é a sincronização real.
- Opcionalmente, derivados finais (TXT, Markdown, JSON, exportações) podem ser copiados para o Drive à parte, mas nunca a pasta de trabalho com toolchain de build.

### GitHub

- Conta: `cunha-leo`.
- Repositório privado: `cunha-leo/upexnote`.
- Branch principal: `main`.
- Primeiro commit publicado: `b9aee90 — Initialize UpexNote foundation`.
- O `.gitignore` exclui mídias, dados gerados, segredos, builds e caches.

### VPS

- Hostinger KVM 2, Ubuntu 24.04 com EasyPanel.
- 2 vCPU, 8 GB RAM, 100 GB de disco, aproximadamente 90 GB livres no levantamento inicial.
- Há PostgreSQL existente, acessível via DBeaver.
- Uso futuro previsto: metadados, histórico sincronizado, API leve, filas e futuro portal web.
- Não usar para guardar biblioteca crescente de vídeo nem para transcrição pesada.
- Quando UpexNote usar Postgres, criar banco/schema próprio e proteger a exposição externa com firewall/TLS/túnel/acesso restrito.

### Acesso SSH à VPS — runbook para qualquer IA (escrito 2026-07-14)

O utilizador trabalha com várias IAs e várias máquinas possíveis. Este runbook permite a qualquer IA diagnosticar e restabelecer o acesso à VPS **sem conhecimento prévio**. Regra de ouro: **nunca pedir, usar ou manusear a password da VPS** — o acesso é sempre por chave SSH instalada pelo próprio utilizador.

**Estado normal (máquina já autorizada):**
- Chave privada em `~/.ssh/upexnote_vps` (Windows: `C:\Users\<user>\.ssh\upexnote_vps`). NUNCA vai para Git, Drive, chat ou logs.
- Ligar: `ssh -i ~/.ssh/upexnote_vps root@vps.upexflow.com`
- Teste rápido: `ssh -i ~/.ssh/upexnote_vps -o BatchMode=yes root@vps.upexflow.com "echo ok"` → deve responder `ok`.

**Se der `Permission denied (publickey,password)` — a máquina NÃO tem privilégios. Recuperar assim:**
1. Verificar se a chave existe (`~/.ssh/upexnote_vps`). Se não existir, gerar (sem passphrase, nome neutro da máquina):
   `ssh-keygen -t ed25519 -f ~/.ssh/upexnote_vps -N '' -C "upexnote-dev-<maquina>-<AAAAMMDD>"`
2. Mostrar ao utilizador o conteúdo da chave PÚBLICA (`~/.ssh/upexnote_vps.pub`) e dar-lhe esta instrução, simples e completa:
   > Abre o painel da **Hostinger** → a tua VPS → **Browser terminal** (funciona mesmo sem SSH) e cola:
   > `mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo '<CONTEÚDO DO .pub>' >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys && echo INSTALADA`
3. Quando o utilizador confirmar, repetir o teste do passo "Estado normal". Só avançar com trabalho na VPS depois do `ok`.

**Se a máquina de desenvolvimento morrer (plano B):** nada essencial vive só nela — código no GitHub (`cunha-leo/upexnote`), dados no Postgres da VPS + dumps diários, chaves API recuperáveis nos dashboards dos fornecedores, transcripts na pasta escolhida pelo utilizador. Numa máquina nova: clonar o repo, ler este documento, e usar o procedimento acima para autorizar a máquina nova na VPS (o painel Hostinger é a porta de entrada que nunca morre). Chaves antigas de máquinas perdidas devem ser removidas do `~/.ssh/authorized_keys` da VPS.

---

## 9. Requisitos de experiência e acessibilidade

- Tema claro, escuro e opção de seguir o sistema.
- Preferência de tema persistente.
- Contraste adequado, fonte confortável, escala tipográfica clara e espaçamento generoso.
- Navegação completa por teclado e foco visível.
- Estados de progresso compreensíveis: etapa atual, tempo decorrido, duração, custo e avisos não podem depender apenas de cor.
- Interface inicial prevista: Biblioteca, Transcrever, Transcript, Contexto, Estudo, Chat do material e Configurações.

---

## 10. Estado atual

### Concluído

- Investigação, testes reais e escolha do motor principal de transcrição.
- Protótipo Python/Tkinter funcional no projeto anterior.
- Credenciais guardadas em Windows Credential Manager no protótipo.
- Nome e marca definidos: UpexNote / UpexFlow.
- Fundação do novo projeto criada no Google Drive.
- Git local inicializado na branch `main`.
- Repositório privado GitHub criado e primeiro commit publicado.
- Documentos iniciais: `README.md`, `ARCHITECTURE.md`, `PRODUCT.md` e este contexto vivo.
- Pipelines de transcrição migrados de `C:\Users\cunha\Project\scripts\` para `services/worker/transcription/`, sem alterar a lógica de nenhum motor (ver Registro 2026-07-12 abaixo).
- Ponto de entrada do worker criado: CLI NDJSON (`transcription.cli`) com comandos `engines`, `transcribe`, `set-key`, `check-key` — pronta para o shell Tauri lançar como sidecar.
- Interface iniciada: scaffold Tauri 2 + React/TS em `apps/desktop`. Toolchain (Rust/C++/Node 24) instalado e validado.
- Desenvolvimento movido do Google Drive para disco local (`C:\Users\cunha\Projects\upexflow\upexnote`); GitHub é a sincronização.
- **Primeira interface funcional:** transcrição de ponta a ponta feita dentro da app (React↔Rust↔worker), com progresso ao vivo e vista de resultado. Validado com gravação real (ver Registro (d)).
- Seletor de ficheiro nativo; organização do storage por dia/motor (ver Registro (e)).
- **Durabilidade/histórico no Postgres da VPS** (serviço dedicado `upexnote-db`), escrita best-effort a cada transcrição (ver Registros (f)/(g)/(h)).
- **App de produção (`.exe`)** com atalho no ambiente de trabalho; **ecrã de Definições** para gerir as chaves na app (sem terminal); menu lateral; bugs da WebView2 corrigidos (ver Registro (i)).
- **`devtools` removido** do `Cargo.toml` e build de produção limpo regerado (ver Registro 2026-07-13 (a)).
- **Worker Python empacotado como sidecar** (PyInstaller onedir): a app usa `worker\upexnote-worker.exe` ao lado do próprio `.exe`, com fallback de dev para o repo. Deixou de depender do caminho fixo desta máquina e do Python do sistema (ver Registro 2026-07-13 (b)).
- **Sistema de Aparência completo (item 5 do backlog, v0.6.0-v0.8.0):** galeria de 12 temas por variáveis CSS (`[data-theme]` no App.css + registo `THEMES` no App.tsx — tema novo = 1 bloco + 1 linha), densidade Compacto (default)/Confortável (`[data-density]`), **titlebar custom** (decorations:false, arrastar/min/max/fechar próprios, setas voltar/avançar), ícones Lucide (NUNCA emojis — regra do utilizador), tipografia Segoe UI Variable. Preferências em localStorage.
- **Biblioteca com cache local (v0.8.1):** abre instantaneamente com a última sessão (localStorage, metadados sem textos) e atualiza em fundo pelo túnel (stale-while-revalidate); overlay de carga só na primeira execução de sempre.

### Próximo trabalho (deixados em aberto)

1. **Roteiro de produto (fases 3-6):** contexto/decisões/ações/riscos, material de estudo (fluxos/tabelas/quiz), chat ancorado no material. A Biblioteca (fase 2) está feita — ver Registro 2026-07-14 (d).
2. Menor: considerar cópia periódica dos dumps para fora da VPS (a VPS é ponto único de falha). ~~Reboot pendente do Ubuntu~~ FEITO a 2026-07-15 (ver Registro). Hardening a considerar: reaplicar o firewall também a cada restart do Docker (hoje só no boot — as regras DOCKER-USER podem ser limpas quando o Docker reinicia; a 2026-07-15 sobreviveram ao upgrade do docker-ce, mas por sorte).

### Backlog de melhorias da Biblioteca (levantado 2026-07-14, IDEIAS — não agendado, não implementar sem confirmar)

1. ~~Aviso ("Com avisos") explorável.~~ **FEITO em v0.4.2 (2026-07-15).** Badge clicável → painel com os `problems`; ações "Corrigir texto" (abre o editor existente) e "Marcar como revisto"/"Reabrir" (nova coluna `warnings_ack`, sem histórico — é status, não conteúdo). Dot da lista ganhou 3º estado (cinzento = revisto).
2. ~~Mostrar o `#id` na app.~~ **FEITO em v0.4.1 (2026-07-15).** Badge `#id` clicável (copia) no cabeçalho do detalhe e prefixo `#id ·` na lista. Sem alterações no worker/schema — só `App.tsx`/`App.css`.
3. **`problems` → `reason_code` + tabela de referência.** Substituir/complementar o texto livre de `problems` por códigos estruturados (ex.: `HALLUCINATION_FOREIGN_LANG`, `COVERAGE_GAP`, `LOOP_REPETITION`) + tabela `problem_reasons` (code, label, descrição, severidade). Torna pesquisável e alimenta dashboards. **Mexe na lógica de validação do worker** (é onde os problemas nascem) — mais substancial. Observação motivadora: numa transcrição real, o aviso foi por `COVERAGE_GAP` (último ts 2915s vs duração 3666s) e a alucinação óbvia em língua estrangeira pode nem ter sido marcada — os reason codes dariam precisão sobre o quê/porquê. **Nota:** este ponto passa a ser implementado dentro do item 4 (o ramo `transcription_problems` + dimensão `problem_reasons`).

4. ~~Restruturação do schema — hub-and-spoke.~~ **FEITO em v0.5.0 (2026-07-15, ver Registro).** Migrado na produção (8 linhas, backup guardado). Adiante ficam sub-itens: surface do reason_code na UI, e (mais tarde) satélites de proveniência/actor quando fizerem sentido. Preocupação/visão do utilizador (2026-07-14): a `transcriptions` ficou "mais textual do que de índices", fora dos padrões modernos e pouco reutilizável. O utilizador (experiente em arquitetura de dados) quer um **hub central ("matrix") + satélites especializados** — enquadramento correto: hub-and-spoke / espírito Data Vault. **Foco explícito: arquitetura, gestão, reaproveitamento e consultas isoladas — NÃO performance** (o utilizador já reconhece que o Postgres aguenta; não repetir o argumento TOAST).

   **Esqueleto-alvo (visão do utilizador + refinamentos meus):**
   - **hub `transcriptions`** (matrix, identidade IMUTÁVEL): id surrogate, código público, ref de origem, `service_type_id`. Nunca se apaga (apagar = flag).
   - **conteúdo `transcript_texts`** (1:1): clean_text, raw_text, `dt_issue`/`dt_change`/`dt_ret`.
   - **erros `transcription_problems` + dim `problem_reasons`** (absorve item 3): descrição/código, `corrected_at`, `alerted_at`, `acknowledged_at` (ignore), `deleted_at`.
   - **métricas `transcription_metrics`** (1:1): motor, processing_s, custo, duração, língua. ("língua mais usada" = query, não coluna.)
   - **dim `service_types`**: áudio-ficheiro, vídeo, ao-vivo, submódulos futuros.
   - **`*_history`/versions**: versões anteriores dos satélites mutáveis (já temos).
   - **proveniência/ator `actors`**: host, input/export path, futuro user_id, e tipo de ação (manual/auto/trigger/batch/IA).

   **3 decisões de design (input meu):**
   - (a) **Um só modelo temporal:** não ter `dt_ret` (soft-delete) E histórico a competir pela verdade. Rec.: satélites com soft-delete + histórico para versões; hub nunca DELETE; criar view `transcriptions_active` (evitar `WHERE dt_ret IS NULL` espalhado).
   - (b) **Ator unificado:** um só conceito `actors` referenciado por ciclo-de-vida E histórico (não duplicar "quem mudou").
   - (c) **YAGNI/camadas:** construir agora hub + conteúdo + erros + métricas (têm dados reais); `service_types` e `actors` como dimensões finas com FKs reservadas; NÃO criar satélites vazios para fases inexistentes — mas deixar as chaves prontas para encaixe não-quebrável.

   **Timing:** antes das fases 3-6 (tudo se pendura no id do hub; mais barato agora). Migração do core (db.py + CLI), segura (poucos dados, backups+histórico).
   **Pendente de decisão do utilizador:** validar (a)/(b)/(c) e a ordem face às fases de produto. (Discussão em curso — utilizador disse ter mais pontos.)

5. **Aparência: densidade + sistema de temas (NÃO impor um look).** **FEITO em 3 levas — v0.6.0, v0.7.0 e v0.8.0 (2026-07-15, ver os 3 Registros).** Estado final: galeria de **12 temas** (Upex Claro/Escuro, GitHub Light/Dark, One Dark, Tokyo Night, Catppuccin Mocha [acento peach], Rosé Pine, Monokai Pro, Nord, Grafite, Preto OLED — Dracula foi adicionado e REMOVIDO a pedido: cliché lilás), densidade **Compacto (default)**/Confortável, titlebar custom, ícones Lucide, restyle estrutural completo. Veredicto do utilizador: aprovado ("está bem melhor"); favoritos: Upex Escuro, Nord, Preto OLED, GitHub Dark. Em aberto (menor): podar temas não usados da galeria; "pode melhorar ainda mais" — refinamentos contínuos bem-vindos. Contexto original: preocupação do utilizador (2026-07-14): o layout atual "parece Bootstrap/CRUD", arcaico; fontes grandes sem controlo de densidade. IMPORTANTE — o utilizador tem gosto forte e específico e **rejeita o cliché "escuro + indigo/lilás"** (demasiado batido). Duas tentativas minhas de "escolher um look moderno" falharam; a resposta certa NÃO é eu escolher, é dar-lhe controlo:
   - **(a) Densidade** — modos **Compacto / Confortável** (à la VS Code/CDS), via `data-density` que remapeia espaçamentos e tamanhos de fonte. Resolve o "fontes grandes/grotescas".
   - **(b) Sistema de temas** — nas Definições, uma secção Aparência com **galeria de temas curados**, não só claro/escuro. Presets que o utilizador citou/gostou: **Monokai Pro, Dracula, GitHub (dark e light)**; +sugeridos: Nord, One Dark, Solarized. O **Indigo atual passa a ser 1 de vários**, não a identidade. Diagnóstico do arcaico mantém-se útil (raios gordos 14/9→6-8px, hairlines, hierarquia, motor como rádio-cards) mas aplicado DENTRO de cada tema.
   - **Arquitetura:** o `App.css` já usa variáveis CSS + `data-theme` (claro/escuro) — multi-tema é a extensão natural: cada tema = um conjunto de variáveis sob `data-theme="dracula"` etc.; o seletor troca o atributo. Contido e extensível (tema novo = bloco de variáveis novo). Persistir a escolha (localStorage/settings).
   - **Motivação de produto:** o utilizador vê o UpexNote a crescer muito (edições, formatação, ligação a NotebookLM/APIs de resumo, secção de notas pessoais) — a identidade visual tem de ser dele e mutável, não uma aposta minha. O sistema de temas é o backbone estético, como o hub-and-spoke é o de dados.
   - **Custo:** quase tudo `App.css` + pequeno seletor nas Definições; sem lógica de negócio. Não agendado; ordem a decidir. **Pendente:** confirmar o lote inicial de temas e se compacto é o default.

6. ~~Zoom da UI + responsividade.~~ **FEITO em v0.4.3 (2026-07-15).** `zoomHotkeysEnabled: true` na config da janela (Tauri 2.1+, WebView2) — ativa Ctrl+scroll / Ctrl +/− nativamente, zooma o layout todo. Responsividade validada até ao `minWidth: 760` declarado (sidebar/formulário/cartões reflow bem via flex/grid); encontrado e corrigido 1 risco real: a tabela de motores (`.eng-table`, 5 colunas) não tinha proteção de overflow — envolvida num `.table-scroll` (scroll horizontal local) em vez de poder espremer colunas ou empurrar a app para scroll lateral. Consolidação mantida: sem dropdown de "tamanho de fonte" (redundante com zoom + densidade do item 5).

7. **Família de fonte nas Definições (≤5).** Estética, separada da escala. Nota técnica: app é offline → fontes têm de ser **empacotadas** (não Google Fonts CDN). Escolher ~5 (ex.: Inter, humanista, mono, neutra); a definição troca `--font-sans`. Contido.

8. ~~Idioma da UI (PT/EN/ES) — só o chrome, NÃO o conteúdo.~~ **FEITO em v0.9.0 + v0.9.1, VALIDADO pelo utilizador (2026-07-16, ver Registro).** Dicionários tipados em `i18n.ts` (falta de chave = erro de compilação), seletor em Definições→Aparência, persistido; transcripts e mensagens do worker NUNCA traduzidos, como especificado. A validação apanhou 1 vazamento (label/info do motor, origem no worker) — corrigido na v0.9.1 via `ENGINE_I18N` no frontend. Contexto original: utilizador consome muito em EN, algum ES, menos PT; explícito: transcripts NÃO se traduzem (ficam na língua do áudio — são dados). Tradução profunda de conteúdo = passo futuro separado, fora deste item.

### Correção 2026-07-15 (v0.5.1) — UI congelava nas ações da Biblioteca
Os comandos Tauri `library*` eram síncronos com IO bloqueante (spawn do worker + handshake do túnel SSH + query, ~2-5s). Comandos síncronos correm na thread principal → a janela **inteira** congelava durante esse tempo a cada ação. Corrigido: passaram a `async` via `tauri::async_runtime::spawn_blocking`, a UI fica responsiva (spinner, janela mexível) enquanto o worker corre. NÃO remove a latência do túnel por chamada (item 10) — só impede que ela congele a UI.

### Backlog (continuação)

10. ~~Túnel SSH reaberto a cada chamada.~~ **FEITO em v0.11.0 (2026-07-16, ver Registro).** Processo guardião `tunnel-keep` lançado pela app no arranque mantém o túnel vivo; `db.py` deteta-o (state file + probe TCP) e liga direto; fallback automático para o túnel por chamada se o guardião não estiver vivo. Ciclo de vida pelo truque do stdin (EOF quando a app morre → sem órfãos). Handshake SSH removido do custo por comando (41.9s→7-10s em rede degradada; ≈1-2s em rede normal).

11. ~~Trocar de aba reiniciava a Biblioteca do zero.~~ **FEITO em v0.4.4 (2026-07-15).** As 3 vistas (Transcrever/Biblioteca/Definições) ficavam montadas/desmontadas condicionalmente — o React destruía o estado da Biblioteca (lista, resumo, detalhe aberto) sempre que trocavas de aba, obrigando a recarregar tudo pelo túnel SSH outra vez. Corrigido: as 3 vistas ficam sempre montadas, só escondidas via CSS (`.view-pane.hidden`).

12. ~~Regressão da v0.4.4: app congelada ~2-5s ao abrir.~~ **FEITO e VALIDADO em v0.4.5 (2026-07-15).** O efeito colateral "positivo" do item 11 (Biblioteca a carregar logo no arranque) tinha um custo: o handshake do túnel SSH competia com a inicialização da janela/WebView2 e deixava-a sem resposta por alguns segundos (nem dava para arrastar). Corrigido: a Biblioteca só carrega na **primeira vez que a aba é aberta** (prop `active` + guarda `loadedOnce`), não no arranque da app — mas continua a NÃO recarregar ao trocar de aba depois disso (mantém o fix do item 11). Lição: "manter montado" (evita reset) e "carregar no arranque" (pré-fetch) são decisões distintas — a primeira era o que o utilizador queria, a segunda foi um extra que causou a regressão. **Confirmado pelo utilizador:** arranque agora demora 4-7s (custo normal de boot Tauri/WebView2/worker, não bloqueia a janela) e fica funcional a seguir — problema de "inoperante" resolvido.

**Nota transversal (itens 5-8):** formam uma superfície coerente de **Preferências/Aparência** nas Definições (tema, densidade, zoom, fonte, idioma) — padrão de app Electron maduro. Motivação do utilizador: vê o UpexNote a crescer muito (edições, formatação, NotebookLM/APIs de resumo, secção de notas pessoais) e quer uma base bonita, moderna e configurável desde já.

13-C. **IDENTIDADE COMPLETA — Fase 1c (ESPECIFICADA pelo utilizador em 2026-07-18, prioridade nº 1 da próxima sessão; a v0.13.0 é só o esqueleto visual).** Crítica do utilizador à v0.13.0: "clube simples de login… CRUD de escola" — a identidade tem de ser nível produto maduro, não gate provisório. Especificação COMPLETA (palavras dele, estruturadas):
   - **Tabela `users` no banco do modo ativo** (SQLite local / Postgres VPS — a conta admin dele nasce no central, semente do multi-tenant da Fase 2): `id`, **`user_id`/username ÚNICO** (gerado no pré-cadastro com verificação de disponibilidade no banco + SUGESTÕES quando ocupado — ex.: "cunhaleonardo"), `email` único, `nome`, `sobrenome`, **`telefone`** (campo existe; autenticação por SMS DESCARTADA — custo de API), **`auth_provider`** (email / google / github — COMO a pessoa entrou fica registado) + `provider_id` + permissões/escopos concedidos no OAuth, `password_salt`/`password_hash` (NULL para contas OAuth; senha NUNCA visível/em claro), **`role`** (user/admin), `created_at`, `updated_at`, `last_login_at`. CRUD completo do perfil (update de nome/telefone/etc.).
   - **Login social REAL:** botões "Entrar com Google" e "Entrar com GitHub" — OAuth nativo de desktop (PKCE + loopback no browser: clica → página de autenticação do provedor → permissões → volta à app). VIÁVEL SEM SERVIDOR próprio e SEM custo; requer registo único (grátis) de OAuth apps pelo dono (Google Cloud Console + GitHub Settings) — passo guiado.
   - **Pré-cadastro pós-OAuth:** primeira entrada por Google/GitHub → tela pede nome/sobrenome (opcional, pré-preenchido do provedor) + gera/valida o user_id único com sugestões. Como toda app moderna.
   - **Admin = segundo fator, não perfil de cadastro:** o que eleva a admin é prova de posse (ex.: credenciais reais do banco/VPS) — separado do método de login. Qualquer utilizador entra por qualquer método; admin é elevação.
   - **Sessões persistidas com validação no banco:** pré-cache local do essencial, revalidação contra o banco quando precisa. Logout real.
   - **MFA (autenticador, ex.: Microsoft) nas Definições** — configurável por utilizador, independente do perfil; validação a sério (servidor/API quando a Fase 2 chegar).
   - **Regra de altitude (permanente):** em identidade/segurança, NUNCA entregar "mínimo do padrão" — entregar o padrão COMPLETO de app moderna confiável. O corpo da app está bom; a identidade tem de estar ao mesmo nível.

13. **Distribuição / arquitetura multi-instalação — DECIDIDA em 3 fases (2026-07-16). FASE 1a ENTREGUE em v0.12.0 (2026-07-18):** SQLite embutido funcional + gate de perfis + indicador/troca nas Definições. **⚠ FEEDBACK DO UTILIZADOR À TELA DO GATE (2026-07-18) — REDESENHO OBRIGATÓRIO na próxima ronda:** (1) a tela atual "dá uma aula" — cards gigantes explicando o que cada perfil acede; quem é admin JÁ SABE, quem é utilizador só quer entrar; (2) **GRAVE: revela infraestrutura** (túnel SSH, Postgres, VPS) a qualquer pessoa que abra a app — inaceitável em cenário de partilha/comercialização; NUNCA expor detalhes de infra em copy de UI; (3) fugiu do padrão de mercado: a entrada principal deve ser **login por e-mail** (como toda app hoje), com logout, reset de senha por e-mail, e depois GitHub/2FA configuráveis nas Definições (independente do perfil) — o desenho de autenticação da Fase 2 já especificado continua válido, mas a UI deve JÁ nascer com a cara padrão (login/senha/esqueci-me), mesmo que na Fase 1 o backend por trás seja local. O MECANISMO da 1a (SQLite/modo/validação VPS real) está certo e fica; a APRESENTAÇÃO é que muda. Falta também: **1b** — assistente de administrador para máquina virgem. Fases 2-3 por agendar. Contexto: a app é hoje extremamente pessoal, pode vir a ser partilhada amigavelmente; venda NÃO está nos planos (fase 3 é ideia futura, nada definido). Mas o utilizador quer levá-la "o mais profissional possível" desde já. Modelo decidido: **conteúdo local + gestão central por eventos** (o conteúdo da pessoa nunca sai da máquina dela; o admin vê métricas, não material).
   - **Fase 1 — SQLite embutido:** biblioteca dentro do executável (não é servidor); a app cria sozinha `%APPDATA%\UpexNote\upexnote.db` no 1º arranque — zero instalação/manutenção para o utilizador, aguenta anos de transcrições/edições/histórico. `db.py` ganha segundo backend + switch no config: a instalação do dono continua na VPS (power user); qualquer outra usa o embutido. Schema hub-and-spoke porta quase 1:1. (A rejeição de SQLite de 2026-07-12 era sobre o setup PESSOAL — durabilidade — e mantém-se; para outras instalações o cálculo inverte.) Sem login: a sessão do Windows é a identidade.
   - **Fase 2 — telemetria administrativa via API:** a app reporta a uma **API fina na VPS** (nunca ligação direta de terceiros ao Postgres; 1ª fase possível via n8n, item 9) eventos SISTÉMICOS: instalação (ID anónimo), versão, região, motor, duração, custo, erros. **Sem conteúdo de transcrições.** No Postgres central: tabela de utilizadores/instalações + eventos — dá consumo, falhas, nº de utilizadores, regiões, comportamento (base para produto/marketing). Encaixa nas FKs/dimensão `actors` reservadas no item 4(c). **Profissionalização incluída nesta fase:** licença/EULA no instalador + aviso de tratamento de dados RGPD/LGPD no 1º arranque (consentimento da telemetria), transporte cifrado. Assinatura digital do instalador e build sem `db_config.json` quando houver partilha real.
   - **Fase 3 — assinatura com APIs do dono (OPCIONAL, futuro indefinido):** a app pediria transcrições à API central (chaves do dono), com consumo faturado por utilizador. Mesma camada da fase 2; só muda quem paga o motor. Só se um dia o produto for vendido.
   - **Seleção de modo — bootstrap da Fase 1 (2026-07-16):** ecrã de **login com dois perfis** no arranque, em vez de deteção silenciosa por ficheiros. **Utilizador** → entra direto, SQLite, zero fricção. **Administrador** → formulário cujos campos SÃO os segredos reais (host/porta/user/password da VPS) e cuja validação é uma ligação REAL à VPS — nada de senha embutida no binário (extraível = teatro de segurança). Dentro do ambiente admin, se faltar a chave SSH, a app **gera o par e guia o único passo manual** (painel Hostinger → Chaves SSH → Testar). Indicador visível do armazenamento ativo nas Definições. NOTA: este formulário é o mecanismo ENQUANTO não existe a API da Fase 2 — com ela, é substituído pelo login abaixo.
   - **Autenticação e recuperação da Fase 2 — ESPECIFICADO E APROVADO (2026-07-16).** Princípio: o admin é **uma conta na API com vários fatores independentes** (perder 1 fator ≠ perder acesso). Escada de recuperação sem ponto único de falha: (1) dia a dia = **GitHub OAuth + TOTP** (ex.: Microsoft Authenticator); (2) máquina morta = login igual noutra máquina (nada vive na máquina); (3) senha GitHub perdida = TOTP + e-mail de recuperação; (4) telefone/TOTP perdido = **códigos de recuperação de uso único** gerados no setup e guardados offline; (5) perdeu tudo = **break-glass**: o dono entra na VPS pela conta Hostinger e faz reset no servidor — a posse da infraestrutura é a âncora final. **Credenciais do Postgres/SSH nunca saem do servidor** na Fase 2 (a app só fala com a API por token — nada nos clientes para roubar). **Multi-admin:** tabela de perfis/roles na API; um admin convida outro, que regista os SEUS fatores; revogável. **Utilizadores:** e-mail+senha com recuperação por e-mail (Google opcional); como o conteúdo é local (SQLite), perder a conta NUNCA perde as transcrições — a conta só carrega identidade/telemetria, não a obra-prima. Cada método foi avaliado pelos 3 testes do utilizador: usabilidade, segurança, e capacidade de cada um recuperar o seu acesso sem invadir o do outro.
   - **Padrões de qualidade transversais (compromisso do utilizador, 2026-07-16):** construção séria de app profissional de mercado — acessibilidade, tempo de resposta, segurança, abstração/camadas, divisão de roles e permissões, e **informação isolada por utilizador** como requisitos permanentes de tudo o que se construir daqui em diante (junta-se aos princípios do §4).

14. **Suite de documentação profissional + visão API-first (visão do utilizador, 2026-07-16 — não agendado, aguarda "vai").** Três entregáveis definidos em discussão:
   - **(A) Mapa de arquitetura C4** em Mermaid dentro de `docs/ARCHITECTURE.md` (versionado, GitHub renderiza, qualquer IA atualiza): contexto → contentores → componentes → fluxos de dados, com tecnologias, portas, onde vive cada peça e decisões-chave. Opcional: versão HTML navegável e/ou export para o draw.io da VPS.
   - **(B) Dicionário de dados bilingue (PT/EN):** cada tabela do schema v2 classificada (hub / satélite / dimensão / histórico / legada), cada coluna com nome, tipo, propósito, tradução, constraints e FKs — gerado por introspeção da base real.
   - **(C) Especificação funcional + contrato de integração:** cada funcionalidade especificada passo a passo (entradas/saídas); futuro **API-first**: todos os campos com parâmetros chave/valor definidos, endpoints e webhooks (envio E receção) documentados em **OpenAPI versionado** — importável no Postman/SoapUI para teste e consumível pelo n8n (item 9). NOTA DE ARQUITETURA: esta camada de integrações e a API da Fase 2 do item 13 (auth+telemetria) são A MESMA API — construir uma vez, servir os três propósitos.

15. **Transcript → Documento de Estudo (ideia do utilizador 2026-07-16 — ESPECIFICA as fases 3-4 do roteiro; não agendado).** Regra de ouro: **transformar sem trair** — legibilidade e estudo SEM matar o contexto real nem criar imaginação sobre o que foi dito (alinha com princípio §4.6: derivado e identificado, raw intocável). Pipeline: retirar timestamps → organizar conteúdo → identificar redundâncias → identificar conexões do assunto (início/meio/fim) → documento legível com: resumo geral, palavras/trechos-chave (temáticas), índice de tópicos, secções por tópico, glossário de termos técnicos (explicação vinda do próprio transcript primeiro; dicionário/internet só com verificação minuciosa para não trazer sujeira), fluxogramas/infográficos onde houver blocos de passos (durante e/ou no fim das secções + contexto final), e **barra de edição Markdown na app** (evoluindo depois para edições específicas). Saída futura (decidir depois): chat interativo na app OU documento + prompt portátil para estudo em qualquer IA (fluxo multi-IA do utilizador). BANDEIRA para implementação: primeira funcionalidade que exige LLM de TEXTO (além dos motores STT) — escolher motor e mostrar custo antes de processar (§4.5).
   **Extensão — documento em dupla-língua (utilizador, 2026-07-16):** tradução CONTEXTUAL (mesmo LLM do pipeline, com o contexto da reunião — explicitamente NÃO estilo Google Translate), matriz origem→alvo entre EN/PT/ES (6 pares). UI: seletor mono/dupla-língua; em dupla, frase original em cima e tradução na linha abaixo até ao fim, com hierarquia visual = padrão UNB do utilizador (original com peso principal, tradução como shadowing discreto). Objetivo: estudo e eternização de vocabulário técnico do mercado (ponte futura possível com o LMSC dele — anotado, não comprometido). Insumo de teste real disponível: reunião do utilizador 100% em inglês.

16. **Primeiras automações n8n — MOVE + ETL + webhooks (ideia do utilizador 2026-07-16 — bootstrap prático do item 14C; não agendado).** Automações escolhidas por dupla utilidade: resolver dores reais E padronizar parâmetros/webhooks de entrada/saída (testáveis em Postman/SoapUI, com documentação evolutiva — cada uma constrói o contrato do item 14):
   - **(a) Dump diário por e-mail:** pg_dump da VPS (já existe, 03:30 UTC, item resolvido em 2026-07-14) → pasta de logs → e-mail diário com ficheiro + template sucesso/erro. BANDEIRA: o dump contém TEXTO das transcrições — decidir na implementação se o e-mail leva o ficheiro ou só a notificação (privacidade).
   - **(b) Transcripts → Google Drive 2×/dia:** cópia automática da pasta local para o Drive — se a máquina morrer, os transcripts sobrevivem (fecha a última ponta de durabilidade de dados; §7 já previa Drive opcional por escolha do utilizador).
   - **(c) Backup de desenvolvimento: DECIDIDO NÃO fazer além do GitHub** — código já está seguro; o que precisa de cópia extra são dados (cobertos por (a) e (b)).
   - Capacidades a validar no n8n: transporte de documentos (MOVE), compactação e descompactação (ETL).

9. **Opção estratégica: n8n como camada de orquestração de funcionalidades futuras (na manga).** Ideia do utilizador (2026-07-15): funcionalidades futuras — **interação de chat, formatação de documentos, envio/exportação, e outras automações** — poderiam ser feitas via **n8n** em vez de tudo nativo na app. Racional de custo: o n8n **já corre self-hosted na VPS do próprio utilizador** (projeto `upexflow`, agora na v2.31.1) → **custo incremental zero pelo n8n** em si; o único custo é o das **IAs** que se ligam (chaves/créditos dos providers). Ponto de ligação possível: a app UpexNote chamar workflows n8n (webhooks) ou vice-versa. NÃO é um compromisso — é uma opção a pesar (n8n vs implementação nativa) quando cada funcionalidade surgir. Vale a pena manter presente porque baixa muito o custo de acrescentar automações.

---

## 11. Protocolo de atualização para qualquer IA

Ao trabalhar neste projeto, uma IA deve:

1. Ler este arquivo, `docs/ARCHITECTURE.md`, `docs/PRODUCT.md` e o `README.md` antes de propor mudanças significativas.
2. Não mover/copiar vídeos brutos nem enviar mídia a serviços externos sem autorização explícita.
3. Nunca pedir, registrar, expor ou inserir chaves em arquivos, logs, terminal compartilhado ou chat.
4. Registrar decisões, resultados de testes, mudanças de arquitetura e pendências neste documento.
5. Manter a seção **Estado atual** correta após cada marco.
6. Tratar `raw transcript` como referência imutável; qualquer versão limpa/formatada deve ser derivada e identificada.
7. Atualizar o Git apenas com código e documentação sem dados privados.
8. Antes de alterar configuração de VPS, banco, permissões de Drive ou integrações cloud, explicar impacto de privacidade, custo e reversibilidade.

### Modelo de entrada para atualizações futuras

```md
## Registro — AAAA-MM-DD

### O que mudou
- ...

### Evidência / teste
- ...

### Decisão
- ...

### Impacto em dados, custo ou privacidade
- ...

### Próximo passo
- ...
```

---

## 12. Registro de atualizações

### Registro — 2026-07-18: identidade completa — tabela users + login social (item 13-C) — v0.14.0

### O que mudou
- **Tabela `users`** no banco do modo ativo (SQLite local / Postgres VPS, mesmo DDL via adaptador de dialeto): `user_id` ÚNICO (username), `email` único, nome/apelido/**telefone** (campo; SMS descartado), **`auth_provider` + `provider_id` + `provider_scopes`** (regista COMO a pessoa entrou e as permissões concedidas), `password_salt`/`password_hash` (**PBKDF2-HMAC-SHA256 120k iterações no worker** — NULL para contas OAuth), `role`, `created_at`/`updated_at`/`last_login_at`. Novo módulo `accounts.py`: register / login / oauth_login / suggest_user_id (disponibilidade + sugestões) / update_profile / reset_password.
- **Login social REAL** (`oauth.py`, SÓ stdlib — zero dependências novas): **Google** = Authorization Code + PKCE com loopback local (padrão para apps instaladas); **GitHub** = Device Flow (só client_id; a app mostra o código de confirmação em tempo real via eventos `oauth://event`). Config em `oauth_config.json` (ao lado do db_config; example commitado) — **passo único do dono pendente:** criar as OAuth apps (grátis: Google Cloud Console tipo Desktop; GitHub OAuth App com Device Flow ativo). Sem config → erro limpo e genérico na UI.
- **Fluxo completo na UI:** botões "Continuar com Google/GitHub" + divisor "ou" + formulário e-mail/senha; **pré-cadastro pós-OAuth** (e-mail bloqueado, nomes pré-preenchidos do provedor, user_id com verificação de disponibilidade em tempo real e sugestões clicáveis — também no Criar conta normal); OAuth de conta já existente entra direto e atualiza `last_login_at`+escopos. Sessão guarda user_id; e-mail lembrado para o próximo login.
- **CLI:** `account-register/-login/-oauth-login/-update/-reset` (payload JSON por STDIN, nunca argv), `account-suggest`, `oauth --provider`. **Rust:** `account(op, payload)` com whitelist, `account_suggest`, `oauth_start` (streaming como o transcribe).
- Incidente sem consequência: 1 byte nulo apareceu no App.tsx (dentro de função removida nesta versão) — detetado e limpo.
- Worker re-empacotado. Versão: **0.14.0**.

### Evidência / teste
- Ciclo completo de contas no SQLite (módulo + CLI por stdin): register→login certo/errado→sugestões de user_id ocupado→OAuth novo→pré-cadastro→register OAuth→retorno OAuth entra direto→reset→login com senha nova→update de perfil (telefone). `oauth` sem config → erro genérico correto. Settings do dono restaurados (default vps intacto). `tsc`/`vite` limpos.
- **Pendente:** validação visual do utilizador; registo das OAuth apps pelo dono (Google/GitHub) para os botões sociais funcionarem de ponta a ponta; conta admin dele na tabela `users` da VPS (hoje o link de administrador entra por validação de ligação, sem linha em users — juntar na Fase 1b/2).

### Impacto em dados, custo ou privacidade
- Senhas nunca em claro nem em argv; tabela users no mesmo perfil de privacidade do banco de cada modo. OAuth: só e-mail/nome/escopos do provedor. Sem custo (OAuth apps grátis).

### Próximo passo
- Utilizador: valida a UI + regista as 2 OAuth apps (guio quando quiseres). Depois: Fase 1b, MFA (Fase 2) e item 15.

### Registro — 2026-07-18: login padrão de mercado (redesenho pós-feedback) — v0.13.0

### O que mudou
- **A tela de perfis da v0.12.0 foi substituída** conforme o feedback do utilizador (registado no item 13): sem aula, sem cards gigantes, **zero menção a infraestrutura** no ecrã de entrada.
- **Cartão de login normal** (~380px, centrado): e-mail + senha + Entrar; primeira execução = "Criar conta" (e-mail, senha ≥6, confirmação); "Esqueci-me da senha" → repor senha local (copy honesto e genérico); "Criar conta"/"Já tenho conta" alternam. Conta **local desta máquina** nesta fase: e-mail + hash SHA-256 com salt (Web Crypto) em localStorage — é um portão de identidade, não cifra de dados; a identidade migra para a API na Fase 2 (GitHub/2FA entram aí, validados no servidor — sem teatro local).
- **"Entrar como administrador"** = link discreto sob o cartão: valida a ligação real por trás (`db_check --mode vps`); falha → mensagem genérica "Esta máquina não tem perfil de administrador configurado." Nada de túnel/Postgres/VPS no copy.
- **Logout**: "Terminar sessão" nas Definições (substitui "Trocar de perfil") — limpa a sessão (conta fica; e-mail lembrado no login) + cache da Biblioteca. Sessão em `upexnote-session`; chave `upexnote-profile` da v0.12.0 é limpa (obsoleta).
- Badges de armazenamento suavizados: "Local nesta máquina" / "Base central 🔒".
- Gotcha WebView2 respeitado: campos de senha são `type="text"` com máscara CSS (`-webkit-text-security: disc`) + interceção de paste — `type="password"` crasha nesta máquina.
- Só frontend (sem repack do worker). Versão: **0.13.0**.

### Evidência / teste
- `tsc`/`vite` limpos; instalador no Desktop. Pendente: validação do utilizador (criar conta → logout → login; link de administrador na máquina dele).

### Impacto em dados, custo ou privacidade
- Zero: mecanismo de armazenamento intacto; conta local sem dados sensíveis além do e-mail (senha só como hash+salt).

### Próximo passo
- Validação do utilizador. Fase 1b (assistente admin máquina virgem) e depois item 15.

### Registro — 2026-07-18: SQLite embutido + ecrã de perfis (item 13, Fase 1a) — v0.12.0

### O que mudou
- **Banco embutido (modo "local"):** o `db.py` ganhou um segundo backend — SQLite (stdlib, zero dependências novas) em `%APPDATA%\UpexNote\upexnote.db` (dev: junto ao código), criado sozinho no 1º uso. **Mesmo schema hub-and-spoke v2** (DDL traduzido por regras: serial→AUTOINCREMENT, timestamptz→TEXT ISO-8601 UTC, jsonb→TEXT, etc.), mesmas funções, mesmo contrato JSON — a UI não distingue. Adaptador mínimo dá ao sqlite3 a cara do psycopg2 (context manager de cursor + tradução %s→?, ILIKE→LIKE, now()→strftime, jsonb_agg→json_group_array). Requer SQLite ≥3.35 (RETURNING) — o Python empacotado traz muito mais.
- **Seleção de modo:** `storage_mode` em settings.json ("local"/"vps"). **Default sem chave preserva o comportamento antigo:** vps se houver config+password (instalação do dono intacta), local caso contrário (instalação virgem → SQLite automático).
- **Ecrã de perfis no 1º arranque** (decisão do item 13 — explícito, não deteção silenciosa): **Utilizador** → modo local, entra direto; **Administrador** → `db-check --mode vps` valida uma ligação REAL à VPS antes de trocar (falha → mensagem + orientação para entrar como Utilizador; o assistente de máquina virgem é a Fase 1b). Perfil guardado em localStorage; a cache da Biblioteca é limpa ao trocar (nunca misturar bases).
- **Definições → Onde guardar:** indicador do armazenamento ativo ("🔒 VPS (Postgres)" vs "Local nesta máquina (SQLite)") + botão "Trocar de perfil…" (limpa perfil+cache e reabre o gate).
- **Infra:** CLI `db-check --mode` (testa sem gravar), `set-settings --storage-mode`, get-settings devolve `storage_mode`+`vps_configured`; Rust `db_check(mode)` async; guardião do túnel sai imediatamente em modo local. `migrate_v1_to_v2` guardado (local nasce em v2). `insert_transcription` continua best-effort nos dois modos.
- Worker re-empacotado. Versão: **0.12.0**.

### Evidência / teste
- **Ciclo de vida completo no SQLite (dev):** check→insert→summary/list(pesquisa)/item(problemas classificados)→update(+snapshot histórico)→ack→soft-delete(+snapshot)→migrate guard — tudo verde, acentos intactos, datas ISO UTC.
- **Regressão VPS:** `db-check` sem argumentos → vps, 10 linhas (dados reais do utilizador intactos, incluindo as transcrições novas de 2026-07-17); `get-settings` devolve vps como default na máquina do dono sem mexer em nada.
- Pendente: validação do utilizador na app instalada (gate → Administrador na máquina dele; simular Utilizador via "Trocar de perfil").

### Impacto em dados, custo ou privacidade
- Nenhum dado movido; modos são bases SEPARADAS (sem sync — futuro, se fizer sentido). Sem custo. SQLite local = mesmo perfil de privacidade dos transcripts locais.

### Próximo passo
- Validação do utilizador. **Fase 1b:** assistente de administrador para máquina virgem (formulário VPS + geração de chave SSH guiada + Hostinger). Depois: item 15 (produto) já nasce multi-modo.

### Registro — 2026-07-16: túnel SSH persistente (item 10 do backlog) — v0.11.0

### O que mudou
- **Causa raiz atacada:** cada invoke que tocava no Postgres abria um `SSHTunnelForwarder` novo (handshake completo por comando — a razão de a Biblioteca custar 2-5s por clique).
- **Processo guardião:** novo comando interno do worker `tunnel-keep` — abre o túnel UMA vez (porta local efémera), publica `{port, pid}` em `tunnel_state.json` (dev: junto ao código; congelado: `%APPDATA%\UpexNote`) e bloqueia a ler stdin até EOF.
- **Ciclo de vida sem órfãos (truque do stdin):** o Rust lança o guardião no arranque (`.setup()`, em thread própria — lição da v0.4.5: nada compete com a inicialização da janela) e guarda o `Child` num static para o stdin ficar preso ao processo da app. App fecha (até em CRASH) → pipe fecha → EOF → guardião termina e limpa o state file. Zero gestão manual de processos.
- **Caminho rápido no `db.py`:** `connect()` deteta o guardião (state file + probe TCP 0.4s) e liga direto a `127.0.0.1:<porta>`; qualquer falha cai no túnel próprio por chamada (comportamento antigo intacto — NUNCA fica pior que antes). Guardião falhou ao arrancar? Cada chamada usa o fallback.
- Worker re-empacotado (PyInstaller). Versão: **0.11.0**.

### Evidência / teste
- Medições em rede DEGRADADA (pior caso real): baseline sem guardião 41.9s (db-check); com guardião: dev 10.0s / library 15.2s; **worker congelado 7.3s / 10.8s** — o handshake SSH desapareceu do custo por chamada; o que resta é latência de rede das queries + arranque do Python (em rede normal ≈1-2s). `library` devolve JSON correto (7 transcrições, agregados certos) pelo caminho rápido, dev e congelado.
- Pendente: validação do utilizador na app instalada (sentir a Biblioteca fluida a partir do 2º acesso).

### Impacto em dados, custo ou privacidade
- Nenhum dado novo; o túnel continua com bind só em 127.0.0.1 e a mesma chave SSH. Sem custo.

### Próximo passo
- Validação do utilizador. Item 10 fecha o grupo de performance da Biblioteca (com a cache v0.8.1).

### Registro — 2026-07-16: identidade profissional no front — versão visível + direitos — v0.10.1

### O que mudou
- **Pedido do utilizador:** app sem versão visível "é um perigo" (suporte vira adivinhação) e faltavam os direitos/atribuição a ele/ao domínio.
- **Versão na titlebar** (à direita, antes dos botões de janela, discreta): lida em runtime via `getVersion()` do Tauri — vem do binário/tauri.conf.json, **nunca dessincroniza** com hardcode.
- **© {ano} UpexFlow · upexflow.com** no rodapé da sidebar (ano calculado; oculto quando a sidebar está recolhida). Sem chaves i18n — nomes próprios, universal.
- Versão: **0.10.1**.

### Impacto
- Zero em dados/custo. Frontend + config. Pendente: validação visual do utilizador.

### Registro — 2026-07-16: tipografia — 15 fontes curadas + controlos (item 7, âmbito ampliado pelo utilizador) — v0.10.0

### O que mudou
- **Âmbito ampliado pelo utilizador:** em vez de ≤5 fontes, pediu ~15 das mais usadas em apps estilo Electron, escolhidas com PESQUISA REAL (modernidade, impacto visual, acessibilidade/fadiga ocular), registo em **JSON pré-carregado**, absorção de **fontes já instaladas na máquina**, e controlos de **negrito, sombra e tamanho** além da escolha de fonte.
- **Pesquisa feita (2026-07-16):** Inter é o padrão das UIs modernas (Notion/Linear/Figma); Geist (Vercel) é o outro neo-grotesco de referência; Lato é a do Slack; a gg sans do Discord é proprietária (não empacotável). Fontes variáveis = standard. Acessibilidade com investigação real: **Lexend** (fluência de leitura) e **Atkinson Hyperlegible** (Braille Institute).
- **Lote (15):** Segoe UI Variable (sistema/default) + 14 empacotadas: Inter, Geist, Roboto Flex, Open Sans, Lato, Source Sans 3, IBM Plex Sans, Manrope, DM Sans, Figtree, Nunito Sans, Public Sans, Lexend, Atkinson Hyperlegible. Todas OFL/livres, via pacotes npm `@fontsource-variable/*` (woff2 variáveis, offline, ~1.5 MB em subsets — só o latino carrega). Registo de metadados em `src/fonts.json` (fonte nova = 1 pacote npm + 1 import no main.tsx + 1 linha no JSON); imports estáticos no `main.tsx` = pré-carregamento.
- **Fontes do sistema:** novo comando Rust `list_system_fonts` (crate `winreg`; lê HKLM+HKCU `...\CurrentVersion\Fonts`, limpa sufixos de formato e estilos, devolve famílias únicas) → segundo grupo no seletor.
- **Cartão "Tipografia" nas Definições** (entre Aparência e Credenciais): seletor com os 2 grupos + **preview ao vivo** (pangram na fonte/peso escolhidos), slider **Tamanho** (90–115%, multiplica os tamanhos da densidade via `--font-scale`), slider **Peso do texto** (300–600, passo 25 — as variáveis rendem qualquer valor; nas estáticas o browser sintetiza), toggle **Sombra no texto**, botão Repor. Persistência: `upexnote-font` (localStorage). CSS: `--font-sans`/`--fw-base`/`--text-shadow` no `:root`; `font-synthesis: none` removido (bloqueava pesos sintetizados de Lato/Atkinson).
- Versão: **0.10.0**.

### Evidência / teste
- `tsc`/`vite` limpos; fontes visíveis no bundle do Vite (subsets woff2). Instalador no Desktop.
- **VALIDADO pelo utilizador (2026-07-16):** capturas com Rosé Pine + Inter em uso; veredicto: "avançamos muito, saímos de uma coisa grosseira de bootstrap e agora sim está ganhando design e vida". **Grupo Preferências (itens 5, 6, 7, 8) COMPLETO e validado** — tema, densidade, zoom, tipografia (fonte/tamanho/peso/sombra) e idioma.

### Impacto em dados, custo ou privacidade
- Sem custo/rede em runtime (fontes empacotadas; licenças OFL incluídas nos pacotes). O comando Rust só lê nomes de fontes do registry local.

### Próximo passo
- Validação do utilizador. Grupo Preferências (itens 5-8) fica então COMPLETO. Estrutural: item 10 (túnel persistente); produto: fases 3-6.

### Registro — 2026-07-16: idioma da UI PT/EN/ES (item 8 do backlog) — v0.9.0

### O que mudou
- **i18n leve, sem biblioteca** (`apps/desktop/src/i18n.ts`): ~110 chaves tipadas × 3 idiomas (PT-PT tu-forma, EN, ES tú-forma). `type Key = keyof typeof pt` + `Record<Key, string>` nos outros idiomas → **uma tradução em falta é erro de compilação**. `t(key, {vars})` com interpolação `{var}`. Contexto React (`LangProvider`/`useLang`) no `App.tsx`; o export raiz passou a ser um wrapper `Root` com o provider.
- **Só o CHROME é traduzido** (regra do item 8): labels, botões, placeholders, tooltips, mensagens de estado, diálogos nativos. Transcripts e mensagens de progresso vindas do worker ficam na língua original (são conteúdo/dados). Nomes de temas são nomes próprios, exceto "Upex Claro/Escuro" (traduzidos).
- **Seletor nas Definições → Aparência:** segmentado Português / English / Español; persiste em `localStorage` (`upexnote-lang`, default pt); o `lang` do `<html>` acompanha; datas formatam no locale (pt-PT/en-US/es-ES via `fmtDate(iso, locale)`).
- Detalhe técnico: o listener de eventos do worker re-subscreve quando o idioma muda (dep `[t]`) para as mensagens de fim ("Concluído.") não saírem no idioma antigo.
- Versão: **0.9.0**.

### Evidência / teste
- `tsc`/`vite` limpos (a tipagem valida a completude dos 3 dicionários); instalador no Desktop. **Validação do utilizador (2026-07-16):** EN e ES percorridos; encontrado 1 vazamento em cada — a descrição/label do MOTOR continuava em PT (vem do worker: `registry.py` devolve `label`/`info` em PT sem acentos).
- **Corrigido em v0.9.1:** mapa `ENGINE_I18N` no frontend sobrepõe label+info por id de motor nos 3 idiomas (com fallback para o texto do worker se surgir motor novo). Bónus: o PT ganhou acentos ("diarização", "rápido") que as strings do worker não têm. Sem re-empacotar o worker.

### Impacto em dados, custo ou privacidade
- Zero: só frontend; preferência de idioma em localStorage local.

### Próximo passo
- Validação do utilizador. Do grupo de Preferências resta o item 7 (família de fonte, ≤5, empacotadas). Estrutural: item 10 (túnel persistente).

### Registro — 2026-07-15: Biblioteca deixa de "resetar" a cada arranque — v0.8.1

### O que mudou
- **Feedback do utilizador (v0.8.0):** fechar e reabrir a app "resetava" a Biblioteca — cada arranque voltava ao ecrã de carga do túnel SSH. Sugestão do próprio: guardar a última sessão localmente (JSON no AppData) e mostrá-la ao abrir, atualizando depois. É exatamente o padrão **stale-while-revalidate**.
- **Implementado (frontend only):** a cada carga completa da lista (sem filtro de pesquisa), `summary`+`items` (metadados, SEM textos de transcrições) são guardados em `localStorage` (`upexnote-lib-cache`, com timestamp). Ao abrir a aba pela primeira vez numa sessão nova: se há cache, aparece INSTANTANEAMENTE com um badge "dados de \<data\> · a atualizar…" e o `load()` corre como refresh em fundo; quando chega, o badge desaparece. Se o refresh falhar (VPS offline), os dados em cache FICAM no ecrã com o erro por cima. O overlay de carga da v0.8.0 só aparece quando não há cache nenhuma (primeira execução de sempre).
- Nota de privacidade: a cache guarda metadados (nomes de ficheiro, custos, datas) no `localStorage` do WebView2 da própria máquina — mesmo perfil de privacidade dos transcripts locais.
- Versão: **0.8.1**.

### Evidência / teste
- `tsc`/`vite` limpos; instalador no Desktop. Pendente: validação do utilizador (fechar/reabrir a app → Biblioteca aparece de imediato com selo de data + refresh em fundo).

### Impacto em dados, custo ou privacidade
- Sem custo; metadados em cache local apenas. O item 10 do backlog (túnel persistente) continua a ser o fix estrutural da latência por chamada.

### Próximo passo
- Validação do utilizador. Possível extensão futura: cache também dos textos de detalhe já abertos.

### Registro — 2026-07-15: reação à v0.7.0 (positiva) + 3ª leva — v0.8.0

### Feedback do utilizador à v0.7.0
- **Aprovação geral:** "agora sim… está mais clean, está mais moderno, está bem melhor" — a direção (titlebar custom, Lucide, hairlines) está certa; continuar a refinar.
- **Temas:** gostou de Upex Escuro (favorito), Nord, Preto OLED, GitHub Dark. **Rejeitou o Dracula** ("lilás índigo… padrão de tudo quanto é sistema, bem copia e cola") → REMOVIDO. Pediu pesquisa REAL no GitHub por temas dark modernos em vez de eu ir de memória.
- **Densidade:** Confortável deve existir, mas **Compacto passa a default**.
- **UX crítica (nova):** a primeira carga da Biblioteca (túnel SSH) deixa o ecrã vazio e mudo — parece travado. "A aplicação tem que conduzir a pessoa" → precisa de indicação visível de carregamento.

### O que mudou (v0.8.0)
- **Pesquisa feita** (web, 2026-07): Catppuccin e Tokyo Night são os temas em maior crescimento na comunidade; One Dark Pro/GitHub/Dracula lideram por instalações acumuladas. Adicionados com paletas OFICIAIS (hexes confirmados nos repos): **Tokyo Night** (tokyo-night-vscode-theme), **Catppuccin Mocha** (catppuccin.com — acento *peach*, deliberadamente NÃO o lavender lilás), **Rosé Pine** (rose-pine/palette, variante main). Dracula removido. Galeria: 12 temas.
- **Compacto é o default** de densidade (quem já escolheu Confortável mantém).
- **Overlay de carga na Biblioteca:** na primeira carga (loading sem dados), overlay semi-transparente com blur + spinner + "A carregar a Biblioteca… A primeira ligação abre um túnel seguro — pode demorar alguns segundos." Só na primeira; refresh posterior continua no botão.
- Versão: **0.8.0**.

### Evidência / teste
- `tsc`/`vite` limpos; instalador no Desktop. Pendente: reação do utilizador (temas novos + overlay).

### Impacto em dados, custo ou privacidade
- Zero: só frontend. A pesquisa web não expôs nada do projeto.

### Próximo passo
- Reação do utilizador; possível poda da galeria (12 temas é muito se metade não for usada). Item 10 do backlog (túnel persistente) é o fix REAL da lentidão que o overlay só amortece. Depois: itens 7 (fonte) e 8 (idioma).

### Registro — 2026-07-15: reação do utilizador à v0.6.0 + 2ª leva do item 5 — v0.7.0

### O que mudou (feedback do utilizador à v0.6.0 — IMPORTANTE para futuras IAs)
O utilizador viu a v0.6.0 e continuou insatisfeito: "continua com cara de Bootstrap". Gostou dos TEMAS (pediu mais variações de preto/escuro), mas rejeitou os detalhes estruturais que denunciam "página web" em vez de app moderna:
- **Emojis como ícones = "grosseiro", "ícone de ChatGPT"** — nunca usar emoji como ícone de UI neste projeto; usar ícones de linha (Lucide/codicon-style).
- **Barra de título nativa azul do Windows = "ridículo de feio"** — tinha de ser da cor do tema.
- **Setinhas «/» para recolher o menu = "bem antigo"** — usar o ícone de painel com recorte lateral (estilo VS Code).
- Pediu: **lupa** no campo de pesquisa, **setas voltar/avançar** de navegação, borda lateral da sidebar na **cor forte do tema**, métricas da Biblioteca sem "duas tabelinhas" (não parecer Bootstrap), mais vida na logo, e referência explícita: VS Code, Claude desktop, "pacote Microsoft new" (Fluent).

### Resposta (v0.7.0)
- **Barra de título custom:** `decorations: false` no tauri.conf.json + componente `Titlebar` (React) com `data-tauri-drag-region`, botões min/max/fechar próprios (hover vermelho no fechar, padrão Windows) e **setas voltar/avançar** (histórico de vistas em memória). Permissões novas em `capabilities/default.json`: `core:window:allow-minimize/-toggle-maximize/-close/-is-maximized`. A tarja azul desapareceu; a barra é pintada pelo tema.
- **Ícones Lucide** (`lucide-react`, empacotado — app continua offline): Mic/LibraryBig/Settings/Palette na nav, PanelLeftClose/Open no recolher, Search embutida no campo de pesquisa (`.input-icon`), ArrowLeft/Right e Minus/Square/X na titlebar.
- **+5 temas escuros:** GitHub Dark, One Dark, Monokai Pro, **Grafite** (escuro neutro sem tinte azul, acento terracota) e **Preto OLED** (preto puro, acento branco, estilo Vercel). Total: 10 temas.
- **Métricas sem caixas:** os 4 cartões da Biblioteca viraram números grandes com labels uppercase pequenos, separados por hairlines verticais (padrão Linear) — zero caixinhas.
- **Sidebar:** borda direita na cor de acento do tema (pedido explícito); marca SVG (balão+onda, eco do ícone da app) na cor de acento ao lado do wordmark; quando recolhida mostra só a marca.
- **Tipografia Fluent:** stack passa a "Segoe UI Variable Text" → "Segoe UI" → Inter (a fonte variável do Windows 11).
- Versão: **0.7.0**.

### Evidência / teste
- `tsc`/`vite` limpos; instalador NSIS gerado e no Desktop. **Pendente: reação do utilizador** (2ª ronda do ciclo iterativo).
- Risco a validar na máquina real: janela sem decoração nativa (WebView2 desta máquina tem historial de quirks) — arrastar, redimensionar, maximizar/restaurar, duplo-clique na titlebar.

### Impacto em dados, custo ou privacidade
- Zero: frontend + config da janela. `lucide-react` é dependência de build (SVGs inline), sem rede em runtime.

### Próximo passo
- Utilizador reage à v0.7.0. Ainda em aberto do item 5: quais temas ficam, default de densidade; depois itens 7 (fonte) e 8 (idioma).

### Registro — 2026-07-15: sistema de temas + densidade + restyle moderno (item 5 do backlog, 1ª leva) — v0.6.0

### O que mudou
- **Sistema de temas (galeria, não imposição):** o `App.css` foi reescrito como sistema de tokens — cada tema é um bloco de variáveis CSS sob `[data-theme="…"]`; tema novo = 1 bloco novo + 1 entrada no registo `THEMES` do `App.tsx`. Lote inicial: **Upex Claro, Upex Escuro** (os atuais, refinados), **GitHub Light, Dracula, Nord**. O indigo/azul atual passou a ser "1 de vários", como pedido. Novas variáveis por tema: `--accent-soft` (tints de hover/seleção) e `--on-accent` (texto sobre o acento — Dracula e Nord têm acentos claros que pedem texto escuro).
- **Galeria nas Definições (secção Aparência, primeiro cartão):** cartões de preview clicáveis. Truque de implementação: cada cartão leva o `data-theme` do respetivo tema no próprio elemento, e os blocos CSS cobrem `[data-theme]` em qualquer elemento (não só `:root`) — o preview pinta-se com as cores REAIS do tema, sem duplicar hexes no TSX.
- **Densidade Compacto/Confortável:** `data-density` no `<html>` remapeia ~15 variáveis (fontes, paddings, gaps, alturas de linha). Confortável é o default e já baixou a base de 15px→14px; Compacto vai a 13px com espaçamentos apertados (resolve o "fontes grandes/grotescas"). Persistência de tema e densidade em `localStorage` (`upexnote-theme`/`upexnote-density`); o valor antigo de `upexnote-theme` ("light"/"dark") continua válido — sem migração.
- **Restyle estrutural anti-"Bootstrap antigo"** (aplicado DENTRO do sistema, vale para todos os temas): raios 14/9px→10/7px; sombras quase-hairline; títulos de secção pequenos/uppercase/dim (padrão Linear/VS Code settings); nav ativa com tint de acento (`--accent-soft`) em vez de caixa com borda; botões secundários fantasma (transparentes com borda); focus ring visível (`:focus-visible` + box-shadow nos inputs — acessibilidade §9); cabeçalhos de tabela uppercase pequenos; badges mais discretos.
- **Sidebar:** o botão "Tema claro/escuro" do rodapé (obsoleto com a galeria) deu lugar a "🎨 Aparência", que abre as Definições.
- Versão da app: **0.6.0**.

### Evidência / teste
- `tsc`/`vite` limpos; instalador NSIS gerado e copiado para o Desktop.
- **Pendente: reação/validação do utilizador** — este item é explicitamente iterativo ("2-3 temas primeiro, para eu reagir a algo concreto").

### Impacto em dados, custo ou privacidade
- Zero: só frontend (`App.css`/`App.tsx`); worker Python, Rust e schema intocados. Preferências ficam em `localStorage` local.

### Próximo passo
- Utilizador reage: temas que ficam/saem, restantes presets (Monokai Pro, GitHub Dark, One Dark, Solarized), default de densidade, ajustes ao restyle. Depois: itens 7 (fonte) e 8 (idioma) da mesma superfície de Preferências.

### Registro — 2026-07-15: schema hub-and-spoke (item 4 do backlog) — v0.5.0

### O que mudou
- A tabela plana `transcriptions` foi partida no modelo **hub-and-spoke**: hub magro (`transcriptions`: identidade+FKs+metadados, **soft-delete via `deleted_at`** — o id nunca desaparece) + satélites `transcript_texts` (1:1, clean/raw/clean_path), `transcription_metrics` (1:1), `transcription_problems` (N:1) + dimensões `engines`, `service_types`, `problem_reasons`. Os `problems` em texto livre passaram a linhas com `reason_code` (classificador heurístico leve: COVERAGE_GAP, HALLUCINATION_LOOP, UNCLASSIFIED) — **absorve os itens 1 e 3 do backlog**.
- `transcriptions_history` mantida intacta (auditoria flat); o snapshot passou a juntar hub+texts+metrics.
- **Contrato JSON dos comandos inalterado** (library/library-item/etc.) → Rust e UI não mudaram neste passo (menos risco).
- Nova função `migrate_v1_to_v2` (CLI `db-migrate`): transacional, renomeia a tabela antiga para `transcriptions_legacy_v1` (BACKUP, não apagada), preserva os ids, verifica contagens ANTES do commit.

### Evidência / teste
- Dump de segurança antes de tocar. Migração na produção: **8 transcrições / 8 textos / 8 métricas / 1 problema**, agregados idênticos ($0.8852, motores certos), backup `transcriptions_legacy_v1` com as 8 linhas.
- Ciclo de vida completo testado num registo descartável (dev + worker congelado): insert→update→ack→soft-delete→limpeza. Raw sempre intacto; problemas classificados (COVERAGE_GAP + HALLUCINATION_LOOP); soft-delete esconde da lista mas mantém a linha + histórico ('update','delete'). Worker congelado fala com o v2 (db-check/library/library-item OK).
- **Nota:** a VPS já está em v2; o app instalado <0.5.0 tem worker antigo (schema flat) e a Biblioteca dá erro até reinstalar — sem risco de dados (best-effort; ficheiro local primeiro).

### Impacto em dados, custo ou privacidade
- Nenhuma transcrição perdida (contagens verificadas + tabela antiga guardada + dump). Sem custo; nenhuma API paga chamada.

### Próximo passo
- Reinstalar (0.5.0). Depois: limpar `transcriptions_legacy_v1` quando houver confiança; possível surface do reason_code na UI; itens 5/7/8 (aparência).

### Registro — 2026-07-15: updates de segurança do Ubuntu + reboot da VPS

### O que mudou
- Aplicados 66 pacotes de atualização na VPS (incluindo segurança), mantendo as configs existentes (`--force-confold`; SSH/firewall não tocados). Dump fresco do Postgres antes de mexer. Reboot feito (autorizado pelo utilizador — VPS pessoal, não comercial, nada em uso).
- Kernel novo ativo: **6.8.0-134-generic**; `reboot-required` limpo.

### Evidência / teste
- **Firewall sobrevive ao reboot:** o serviço systemd `upexnote-firewall.service` reaplicou as regras no arranque (DROP v4+v6 confirmados). Postgres OK pelo túnel (8 linhas). Backup cron presente.
- **Efeito colateral (resolvido):** o serviço `upexflow_n8n` (outro projeto, lmsc/upexflow — NÃO UpexNote) ficou 0/1 após o reboot (arrancou e recebeu SIGTERM na reconciliação do boot; Swarm não reinicia com política on-failure + exit 0). Reposto com `docker service update --force upexflow_n8n` → 1/1 estável, v2.12.3. Imagem FIXADA em `n8nio/n8n:2.12.3` (não latest); a atualização de VERSÃO pendente deve ser feita pelo EasyPanel (gere o serviço; comando cru dessincronizaria + n8n corre migrações no arranque). Todos os serviços do UpexNote (upexnote-db, drawio) voltaram 1/1.
- **Aprendizagem:** durante o upgrade o docker-ce foi atualizado (reinicia o Docker) e as regras DOCKER-USER sobreviveram, mas por sorte — reforço futuro: reaplicar o firewall a cada restart do Docker, não só no boot (ver §10 item 2).

### Registro — 2026-07-14 (e): Biblioteca — editar e apagar com histórico/auditoria (v0.4.0)

### O que mudou
- **Editar** (na vista de detalhe): corrige o texto **clean** onde ficou mal, direto na app. A **raw NUNCA é tocada** (princípio #1). Ao guardar, reescreve também o ficheiro clean no disco (best-effort; raw fica intacto).
- **Apagar**: remove da lista ativa, com confirmação **inline** (evita o diálogo nativo que crasha a WebView2 desta máquina).
- **Tabela de histórico `transcriptions_history`** (decisão do utilizador, opção "histórico completo"): antes de cada edição E de cada delete, a linha atual é copiada para lá com `change_type` ('update'/'delete') e `archived_at`. Resultado: edições reversíveis, deletes recuperáveis, auditoria. Nova coluna `edited_at` em `transcriptions`. Migração idempotente no `ensure_table` (ADD COLUMN IF NOT EXISTS + CREATE TABLE IF NOT EXISTS).
- **Correção do cursor**: as linhas da lista já não ficavam desativadas ao abrir (cursor "proibido" que o utilizador achou ofensivo) — agora mostram um spinner na própria linha.
- CLI: `library-update` (novo texto por stdin) e `library-delete`. Rust: `library_update` (texto por stdin) e `library_delete`. Versão **0.4.0**.

### Evidência / teste
- Update e delete testados a fundo pelo túnel em dev E no worker **congelado** (registo descartável): update por stdin com acentos (çãõ) intactos, `edited_at` marcado, delete arquiva-e-remove. Um teste chegou a editar o id 8 real — restaurado a partir do próprio histórico (a rede funcionou) e histórico de teste purgado; dados reais intactos (8 ativos, 0 no histórico). `tsc`/`vite` e `cargo check` limpos.
- **Pendente:** validação visual do utilizador (editar uma palavra e guardar; apagar um registo de teste).

### Impacto em dados, custo ou privacidade
- Edições/deletes só na base + ficheiro clean local; a raw (texto e ficheiro) é imutável. Sem custo; nenhuma API paga. O histórico guarda cópias na mesma VPS (mesmo modelo de privacidade do resto).

### Próximo passo
- Validação do utilizador. Depois: fases 3-6 do roteiro (contexto, estudo, chat). Possível: UI para ver/restaurar o histórico (hoje só via SQL).

### Registro — 2026-07-14 (d): aba Biblioteca — histórico e dashboards (v0.3.0)

### O que mudou
- **Nova aba Biblioteca** (menu lateral) que lê a tabela `transcriptions` do Postgres (pelo túnel SSH): cartões de topo (total de transcrições, custo total, áudio processado, tempo médio), tabela de repartição **por motor** (contagem, custo, áudio, tempo médio), e lista pesquisável (por nome de ficheiro) com estado de validação, motor, data, duração e custo. Clicar numa linha abre a **vista de detalhe** com o texto completo (clean) + copiar.
- **Worker (`db.py`):** `library_summary()` (agregados SQL), `library_list(limit, search)` (metadados, sem texto — payload leve), `library_item(id)` (registo completo com texto). CLI: comandos `library` e `library-item`. Rust: comandos `library`/`library_item`.
- Versão da app: **0.3.0**.

### Evidência / teste
- Comandos testados pelo túnel em dev e no **worker congelado**: `library` devolve total=8, custo≈$0.885, 3 motores; `library-item --id 10` traz o texto (~19,7 mil chars). `tsc`/`vite` e `cargo check` limpos.
- **Pendente:** validação visual do utilizador na app instalada (abrir a aba, confirmar cartões/lista/detalhe).

### Impacto em dados, custo ou privacidade
- Só leitura da base (nenhuma escrita nova). Sem custo; nenhuma API paga chamada. O texto só sai da base quando o utilizador abre uma transcrição específica.

### Próximo passo
- Validação do utilizador. Depois: fases 3-6 do roteiro (contexto, estudo, chat).

### Registro — 2026-07-14 (c): acesso ao Postgres migrado para túnel SSH; porta fechada a 100% da internet

### O que mudou
- **A allowlist de IP do Registro (b) durou horas e foi substituída de propósito:** o utilizador viaja constantemente, usa VPN e vai mudar-se para Portugal — amarrar o acesso a um IP era o modelo errado ("segurança e liberdade de acesso aonde eu for"). O modelo certo: **túnel SSH com chave**, que funciona de qualquer rede/IP/VPN.
- **Worker:** `db.py` abre túnel SSH (lib `sshtunnel`; `paramiko` fixado em `>=3,<4` — o 5.x removeu `DSSKey` e quebra o sshtunnel 0.4) quando o `db_config.json` tem a secção `"ssh"` (host/port/user/key — a chave é o caminho para `~/.ssh/upexnote_vps`, NÃO um segredo no ficheiro). Fecho da ligação via `close_connection()` (fecha ligação E túnel). Sem secção `ssh`, liga direto como antes.
- **Firewall da VPS:** o script `/usr/local/sbin/upexnote-firewall.sh` agora faz DROP total na 55433 (IPv4+IPv6) — **sem exceções, sem allowlist para gerir**. A secção "Como mudar o IP autorizado" do Registro (b) está OBSOLETA.
- **DBeaver:** passa a usar o túnel embutido (aba SSH: `root@vps.upexflow.com:22`, chave `upexnote_vps`; aba Main: host `127.0.0.1:55433`).

### Evidência / teste
- Dev e worker congelado: `db-check` OK pelo túnel (8 linhas). Ligação direta à porta: `TcpTestSucceeded: False` até do IP do utilizador. A porta está fechada para o planeta; o único caminho é ter a chave SSH.
- **DBeaver validado pelo utilizador (2026-07-14):** ligação `upexnote` reconfigurada com túnel SSH embutido (aba SSH: `vps.upexflow.com:22`, user `root`, chave `C:\Users\cunha\.ssh\upexnote_vps`; aba Principal: host `localhost:55433`, user `postgres`). "Testar conexão" → Conectado (PostgreSQL 17.10). Cadeado SSH visível no painel.
- Nota de dev descoberta no processo: o Python da MS Store **virtualiza** `%APPDATA%` (lê/escreve em `...\PythonSoftwareFoundation...\LocalCache\Roaming` em vez da pasta real) — em modo dev, o settings/config do worker pode divergir do que o worker congelado vê. Em produção (exe congelado) está tudo na pasta real.

### Impacto em dados, custo ou privacidade
- Exposição da base: 0 portas públicas (antes: 1 porta com allowlist). Credencial = chave SSH por máquina (runbook §8). Máquinas novas precisam da própria chave registada na Hostinger.
- Sem custo. Reversível: repor secção allowlist no script de firewall + remover `"ssh"` do config.

### Próximo passo
- Aba Biblioteca. Menor: reboot pendente da VPS; cópia off-VPS dos dumps.

### Registro — 2026-07-14 (b): VPS endurecida — firewall na porta do Postgres + backup diário

### O que mudou
- **Firewall:** a porta pública `55433` (Postgres `upexnote-db`) está agora restrita ao IP do utilizador. Regras na cadeia `DOCKER-USER` (a única que o Docker respeita — o UFW é ignorado pelo Docker, razão pela qual tentativas anteriores falharam), aplicadas por `/usr/local/sbin/upexnote-firewall.sh` e reaplicadas a cada arranque pelo serviço systemd `upexnote-firewall.service`. IPv4 e IPv6 cobertos (a porta estava publicada nos dois).
- **Backup:** dump diário às 03:30 UTC (`/etc/cron.d/upexnote-backup` → `/usr/local/sbin/upexnote-backup.sh`): `pg_dump` da base `upexnote` para `/root/backups/upexnote/upexnote-<data>.sql.gz`, rotação de 14 dias, log em `/var/log/upexnote-backup.log`.
- **Acesso SSH por chave** estabelecido para a máquina de desenvolvimento (ver runbook na secção 8): chave adicionada pelo utilizador via painel Hostinger (Chaves SSH), sem password a circular.

### Evidência / teste
- **Bug encontrado e corrigido durante o teste:** a 1ª versão da regra allow filtrava por `-s <IP>`, o que bloqueava as RESPOSTAS do Postgres (origem = IP do container) — o pedido entrava, a resposta morria, timeout. Corrigido com `--ctorigsrc` (permite ambos os sentidos de ligações INICIADAS pelo IP autorizado). Lição para o futuro: testar sempre o caminho completo, não só a regra.
- Verificação dupla: `db-check` do IP autorizado → OK (8 linhas); teste externo de 56 localizações (check-host.net) → timeout em todas (o único "Connected" de 3ms era falso positivo de proxy no nó, confirmado por 0 ligações estabelecidas no conntrack do servidor e 158 pacotes no contador DROP).
- Primeiro dump feito e íntegro (`gunzip -t` OK, ~54 KB). Serviço `enabled`, cron instalado.

### Como mudar o IP autorizado — OBSOLETO (ver Registro (c))
No mesmo dia, a allowlist de IP foi substituída por túnel SSH e a porta fechada por completo — deixou de existir IP autorizado para gerir. Mantido só como histórico.

### Restaurar um backup (se alguma vez for preciso)
`gunzip -c /root/backups/upexnote/upexnote-<data>.sql.gz | docker exec -i <container upexnote-db> psql -U postgres upexnote`

### Impacto em dados, custo ou privacidade
- Superfície de exposição da base caiu de "internet inteira" para 1 IP. Sem custo. Reversível: `systemctl disable upexnote-firewall` + remover as 3 regras (ou correr o script com outro IP).
- Nota vista no servidor: o Ubuntu tem updates de segurança pendentes e pede restart — decisão do utilizador para altura conveniente (reinicia todos os serviços do EasyPanel por ~1-2 min).

### Registro — 2026-07-14: v0.2.0 — pasta dos transcripts à escolha do utilizador

### O que mudou
- **Fim da estrutura imposta:** `Documentos\UpexNote` é agora só o padrão de fábrica. Nas **Definições** há "Pasta padrão" (seletor nativo + "Repor padrão") e o interruptor **"organizar por dia/motor"** (desligado = ficheiros diretos na pasta escolhida; o nome já carrega origem+data+motor+tipo). No ecrã **Transcrever** há "Guardar em (opcional — só desta vez)": os ficheiros dessa transcrição vão DIRETOS para a pasta indicada, ignorando padrão e organização.
- Implementação: `%APPDATA%\UpexNote\settings.json` (`storage_dir`, `organize_by_day_engine`); `paths.py` resolve override → settings → fábrica; CLI ganhou `get-settings`/`set-settings` e `transcribe --dest`; Rust ganhou `get_settings`/`set_settings` e `dest` opcional. O par raw/clean continua sempre a ser gravado (princípio intocável).
- Versão da app: **0.2.0** (`UpexNote_0.2.0_x64-setup.exe`).

### Evidência / teste
- Lógica de caminhos testada em dev (5 cenários: fábrica, custom+organize off, override pontual, repor, organize on) e no worker congelado (get/set-settings roundtrip OK, padrão congelado = Documentos). `tsc`/`vite` e `cargo check` limpos. Instalador 0.2.0 gerado e no Desktop do utilizador.
- **VALIDADO pelo utilizador (2026-07-14):** instalou a 0.2.0, desligou a organização por dia/motor, escolheu o Desktop como pasta e fez uma transcrição real (AssemblyAI, ~$0.0713, 20 min, validação OK, linha #10 no Postgres). Ficheiros gravados diretamente na pasta escolhida, como desenhado.

### Impacto em dados, custo ou privacidade
- Nenhum dado movido; transcripts existentes ficam onde estão. `settings.json` não contém segredos (só caminhos/booleano). Sem custo.

### Próximo passo
- Utilizador valida a 0.2.0. Depois: endurecimento da VPS e aba Biblioteca.

### Registro — 2026-07-13 (e): logo/ícone da marca

### O que mudou
- Ícone próprio escolhido pelo utilizador entre 9 propostas: **balão de conversa em contorno com barras de onda sonora** (índigo `#818CF8` + acento verde `#34D399` sobre fundo `#1E1B4B`). Comunica "conversa → transcript".
- Fonte vetorial em `apps/desktop/src-tauri/icons/icon-source.svg`; raster 1024px e todos os tamanhos gerados com `tauri icon` (janela, barra de tarefas, Menu Iniciar, `icon.ico`). Instalador recompilado com a marca.

### Evidência / teste
- PNG 1024 verificado visualmente; instalador novo gerado e copiado para o Desktop (substituição por cima da instalação atualiza o ícone). Validado pelo utilizador: ícone correto no Menu Iniciar, barra de tarefas e Desktop.

### Armadilhas encontradas (para builds futuros de ícone)
- **O cargo não re-embute o ícone sozinho:** trocar os ficheiros em `icons/` não faz o build script correr de novo — o exe sai com o ícone ANTIGO embutido. Forçar com `touch tauri.conf.json build.rs` antes do `tauri build`. Verificar extraindo o ícone do exe (`[System.Drawing.Icon]::ExtractAssociatedIcon`), não confiando no build.
- **Caches de ícone do Windows:** mesmo com o exe certo, o Desktop (OneDrive-sincronizado) mostra o ícone velho. Foi preciso limpar `iconcache_*.db` E `thumbcache_*.db` (este último é o do Desktop OneDrive) + reiniciar o Explorer, e recriar o atalho com `IconLocation` explícito.

### Impacto em dados, custo ou privacidade
- Nenhum. Só assets de imagem no repositório.

### Registro — 2026-07-13 (d): instalador NSIS — "app de verdade"

### O que mudou
- **Instalador de um único ficheiro:** `UpexNote_0.1.0_x64-setup.exe` (~49 MB), gerado pelo bundler do Tauri (`npm run tauri build`, alvo `nsis`). Instala por utilizador (sem admin) em `AppData\Local\Programs`, cria entrada no Menu Iniciar e desinstalador nas Definições do Windows. Instalador em PT/EN.
- **Worker vai dentro do instalador:** `tauri.conf.json` inclui a pasta `worker` como *resource* — no PC de destino fica ao lado do exe instalado, exatamente onde o `worker_command()` do Rust já procura. Nenhuma alteração de código foi precisa.
- `build_worker.ps1` passa a copiar o worker também para `apps/desktop/src-tauri/worker/` (fonte do bundler; gitignorado).

### Evidência / teste
- Build do instalador terminou sem erros; ficheiro em `target/release/bundle/nsis/` e copiado para o Desktop do utilizador.
- **VALIDADO pelo utilizador (2026-07-13):** instalou pelo setup, renomeou a pasta do projeto para `..._OFF` e fez uma **transcrição real de ponta a ponta pela app instalada** (AssemblyAI). Transcript gravado em `Documentos\UpexNote\storage\transcripts\2026-07-13\assemblyai\` (clean+raw). Prova de independência total da pasta do projeto — o teste que faltava ao sidecar. Pasta renomeada de volta em seguida.
- Pendência cosmética: o ícone da app é o default do Tauri — logo própria em curso.

### Decisão
- NSIS `currentUser` (sem admin) e não MSI: experiência tipo Chrome/Spotify, adequada a uso pessoal.
- Instalador **não assinado**: SmartScreen avisa na primeira execução noutras máquinas ("Mais informações → Executar mesmo assim"). Assinatura digital (certificado pago) só se justifica com distribuição pública — fica para depois.

### Impacto em dados, custo ou privacidade
- O instalador leva o `db_config.json` (endereço da VPS, sem password) — mesmo racional do zip portátil: para máquinas do próprio. Sem custo; nenhuma API chamada.
- Instalar não toca nos dados: transcripts continuam em `Documentos\UpexNote`, chaves no Credential Manager.

### Próximo passo
- Utilizador corre o setup e valida (incluindo uma transcrição real pelo sidecar). Depois: endurecimento da VPS e aba Biblioteca.

### Registro — 2026-07-13 (c): pacote portátil (zip) — app corre em qualquer PC ao descompactar

### O que mudou
- **`make_portable.ps1`** (raiz do repo): constrói worker + app e gera `dist\UpexNote-portable.zip` (~67 MB) com `UpexNote\upexnote.exe` + `worker\`. Descompactar em qualquer Windows 10/11 → abrir o exe → colar as chaves em Definições (uma vez) → app normal. Zero cópias manuais de ficheiros.
- **`db_config.json` viaja no pacote:** o `db.py` congelado procura primeiro em `%APPDATA%\UpexNote` (override do utilizador) e depois **ao lado do worker** (versão incluída no zip). O passo manual "copiar config para o AppData" deixou de existir.
- `build_worker.ps1` inclui o config no pacote se existir; se for removido antes do build (distribuição a terceiros), a app funciona na mesma — só não grava histórico na VPS.

### Evidência / teste
- Cenário "PC novo" simulado: com o config do `%APPDATA%` escondido, o worker empacotado usou o config de dentro do pacote e ligou à VPS (`db-check` OK). Restaurado no fim.
- Zip verificado: `UpexNote\upexnote.exe`, `worker\upexnote-worker.exe`, `worker\db_config.json`, `worker\_internal\...` (201 entradas).

### Decisão
- Sem "ecrã de login": a app não tem contas; o ecrã de Definições já cumpre o papel de configuração única por máquina (chaves ficam no Credential Manager local).

### Impacto em dados, custo ou privacidade
- O zip leva o endereço da VPS (host/porta/base/user — **sem password**). É para máquinas do próprio; para terceiros, apagar `transcription\db_config.json` antes de correr o `make_portable.ps1`.
- Sem custo; nenhuma API paga chamada. O zip fica em `dist/` (fora do Git).

### Próximo passo
- Testar o zip numa segunda máquina real. Depois: endurecimento da VPS e aba Biblioteca.

### Registro — 2026-07-13 (b): worker Python empacotado como sidecar (PyInstaller onedir)

### O que mudou
- **Worker empacotado:** `services/worker/build_worker.ps1` gera, com PyInstaller (**onedir**), a pasta `upexnote-worker.exe` + `_internal/` (~146 MB, PyAV traz o ffmpeg) e copia-a para `apps/desktop/src-tauri/target/release/worker/`. Novo ponto de entrada `worker_entry.py` (o PyInstaller precisa de um script, não de `-m`).
- **Resolução no Rust (`lib.rs`):** novo `worker_command()` usado pelos 3 pontos de spawn — prefere `worker\upexnote-worker.exe` ao lado do exe da app; se não existir, fallback de desenvolvimento (`python -m transcription.cli` no layout do repo). O comentário "caminho fixo desta máquina" deixou de ser verdade.
- **Caminhos em modo congelado:** transcripts → `Documentos\UpexNote\storage\...` (pasta estável e visível; sobrevive a atualizações); `db_config.json` → `%APPDATA%\UpexNote\` (antes ficaria enterrado no `_internal/`). Em dev nada muda.
- `-u` substituído por `PYTHONUNBUFFERED=1` (o exe congelado não aceita flags do interpretador; o efeito é o mesmo — NDJSON linha a linha).
- **Onedir e não onefile (decisão):** a app lança o worker em muitas chamadas curtas; o onefile descomprime para o temp a cada chamada (lento + falsos positivos de antivírus).

### Evidência / teste
- Worker congelado testado diretamente: `engines` (4 motores, chaves detetadas — keyring funciona congelado com `--hidden-import keyring.backends.Windows`), `list-keys` (4 credenciais OK) e `db-check` (leu config do `%APPDATA%\UpexNote`, ligou à VPS, tabela OK, 5 linhas). Sem chamadas a APIs pagas.
- `cargo check` limpo; app de produção recompilada com sucesso.
- **Pendente de validação:** uma transcrição real de ponta a ponta pela app usando o sidecar (custa ~$0.07; fazer no próximo uso normal).

### Decisão
- Sidecar por deteção em runtime (exe ao lado) em vez de configuração de bundle do Tauri: funciona já com o fluxo atual (`build --no-bundle` + atalho); o bundle formal fica para a fase do instalador.

### Impacto em dados, custo ou privacidade
- **Os transcripts vivem agora em `Documentos\UpexNote\storage\`** — os novos (via app de produção) são gravados lá, e os 12 ficheiros antigos foram migrados do `storage/` do repo (cópia verificada com `diff -r` antes de apagar a origem). Nota: em modo de desenvolvimento (fallback sem sidecar) o worker ainda escreve no `storage/` do repo.
- `db_config.json` copiado (não movido) para `%APPDATA%\UpexNote\`. Sem custo; nenhuma API paga chamada.

### Próximo passo
- Validar uma transcrição real pela app (sidecar). Depois: endurecimento da VPS (firewall + backup do Postgres) e aba Biblioteca.

### Registro — 2026-07-13 (a): remoção do `devtools` + build de produção limpo

### O que mudou
- Removida a feature `devtools` do `tauri` em `apps/desktop/src-tauri/Cargo.toml` (`features = ["devtools"]` → `features = []`). Estava ligada apenas para diagnosticar os crashes da WebView2 desta máquina (Lunar Lake / Arc), já resolvidos (ver Registro (i)).
- Recompilada a app de produção (`npm run tauri build -- --no-bundle`); `upexnote.exe` regerado (~9,5 MB) sem `devtools`.

### Evidência / teste
- Build terminou com exit 0. Único aviso: mensagem benigna do linker (criação da `.dll.lib`), sem relação com a alteração. `tsc && vite build` OK; compilação Rust `Finished release` em ~3m31s.
- `Cargo.lock` inalterado (o `devtools` era feature do crate `tauri` já presente; não mexeu na árvore de dependências).

### Decisão
- Distribuir sem `devtools` — a app deixa de expor as ferramentas de desenvolvimento da WebView2 na versão de produção.

### Impacto em dados, custo ou privacidade
- Nenhum. Só alteração de código; sem chamadas a APIs nem custo. Commit `307c763` publicado no `main`.

### Próximo passo
- Empacotar o worker Python como sidecar (portabilidade/instalador); endurecimento da VPS; aba Biblioteca.

### Registro — 2026-07-12 (i): Definições na app, navegação lateral, app de produção (.exe)

### O que mudou
- **Ecrã de Definições:** gerir as 4 credenciais (AssemblyAI, OpenAI, Deepgram, password do Postgres) pela própria app — Guardar e Remover, sem terminal. O valor é enviado ao worker por **stdin** (nunca em argumentos/linha de comando). Novos comandos CLI `set-key --stdin`, `clear-key`, `list-keys` (estado de todas as chaves numa só chamada) e comandos Rust `save_credential`/`clear_credential`/`list_credentials`.
- **Navegação:** menu lateral recolhível (Transcrever / Definições + tema + recolher). O estado da transcrição mantém-se ao trocar de vista. Botão "Novo" para limpar a sessão.
- **Passámos de modo-dev para app de PRODUÇÃO (`.exe`):** o `npm run tauri dev` era instável (o servidor caía → janela preta; exigia um terminal aberto). Agora há um `.exe` real (`tauri build --no-bundle`) com atalho **"UpexNote"** no ambiente de trabalho — abre como app normal, sem terminal nem servidor. Para veres alterações de código é preciso recompilar (~1–1.5 min) e reabrir.

### Bugs corrigidos (WebView2 nesta máquina — Lunar Lake / Arc)
- **Terminais a piscar:** cada chamada ao Python abria uma consola. Corrigido com `CREATE_NO_WINDOW` em todos os spawns (Rust `with_no_window`).
- **Ecrã branco/preto ao clicar/colar nos campos das chaves:** (1) eram `type="password"` → a WebView2 abria a UI de guardar-password e crashava ao focar → mudados para texto normal; (2) o "colar nativo" da WebView2 crashava → intercetado no `onPaste` (a app insere o texto ela própria). Confirmado a funcionar **sem** devtools. **NÃO era GPU** (testámos desligar, não resolveu, revertido).
- Nota: `devtools` ligado no Cargo.toml (feature) — foi para diagnóstico; remover antes de distribuir.

### Evidência / teste
- As 4 chaves configuradas pela UI (clicar/colar/guardar/remover a funcionar). Transcrição continua a gravar em ficheiro local + Postgres.

### Decisão
- Chaves geridas na app (fim da dependência do terminal para credenciais).
- App usada como `.exe` de produção; o worker Python é encontrado pelo caminho fixo desta máquina (baked `CARGO_MANIFEST_DIR`) — funciona aqui, mas para outras máquinas falta empacotar o worker como sidecar.

### Próximo passo
- Remover devtools; empacotar o worker como sidecar (portabilidade/instalador); endurecimento VPS (firewall + backup do Postgres); aba Biblioteca.

### Registro — 2026-07-12 (h): Postgres ligado e verificado (serviço dedicado)

### O que mudou
- Criado um **serviço Postgres dedicado** no EasyPanel (projeto `upexnote`, serviço `upexnote-db`) — isolado do `lmsc`, visível e gerível pelo utilizador (a abordagem de "base dentro do container existente" foi abandonada). Porta pública `55433` em `vps.upexflow.com`, base `upexnote`, user `postgres` (superuser só deste container isolado).
- App liga-se por TCP direto: `db.py` lê `db_config.json` (gitignored) e a password do Windows Credential Manager (`UPEXNOTE_PG_PASSWORD`). Novo comando `db-check`. Escrita best-effort no `transcribe` após o ficheiro local.

### Evidência / teste
- `db-check`: "Ligação OK. Tabela 'transcriptions' pronta." A tabela foi criada automaticamente.
- Escrita verificada: inserção de uma linha de teste (id #1) + apagada; tabela limpa (0 linhas).
- Utilizador vê a base `upexnote` e a tabela `transcriptions` no DBeaver (ligação `vps.upexflow.com:55433`).

### Decisão
- Serviço dedicado (container próprio) em vez de partilhar o Postgres do `lmsc`: isolamento real, backups próprios, visível. Como é isolado, a app usa o `postgres` desse container sem risco de tocar noutras apps — sem necessidade de role/schema extra.

### Impacto em dados, custo ou privacidade
- Metadados + texto (clean/raw) vão para a VPS em claro (opção 1). Transito: `sslmode=prefer` (usa TLS se o servidor tiver; senão, texto simples — endurecer depois).
- Porta pública: endurecer com firewall/allowlist de IP. Falta configurar dump/backup do Postgres.

### Próximo passo
- Endurecimento (firewall no IP, backup do Postgres). Produto: ecrã de Definições (gerir chaves/DB pela UI), empacotamento (worker como sidecar), aba Biblioteca (consultar histórico a partir da tabela).

### Registro — 2026-07-12 (g): privacidade resolvida (opção 1) + plano de ligação ao Postgres

### O que mudou
- Resolvida a questão pendente do Registro (f): **opção 1** — metadados **e texto** do transcript vão para o Postgres na VPS, **em claro** (sem encriptação).
- Raciocínio: a ameaça que o utilizador quer cobrir é "a máquina morre" (durabilidade), e para essa o texto em claro na própria VPS já resolve. Encriptar só protegeria de invasão da VPS (ameaça baixa, ambiente fechado e menos exposto do que as APIs que já recebem o áudio) e introduziria risco de perder tudo por perder a chave — o que jogaria contra a própria durabilidade. Texto em claro é também totalmente consultável no DBeaver para os dashboards.

### Estado da infraestrutura (confirmado pelo utilizador)
- Postgres a correr no EasyPanel (serviço `lmsc-db`), superuser `postgres`, base existente `lmsc` (outra app, Prisma — não mexer).
- Porta **exposta publicamente** (host externo do tipo `vps.upexflow.com`, porta alta). A app liga direto por TCP — sem túnel SSH.
- Detalhes de ligação (host/porta/base/user) ficam num **config local ignorado pelo Git** (não no repositório). Password no Windows Credential Manager (o utilizador introduz; a IA nunca lhe toca).

### Decisão de setup
- Nova base `upexnote` + utilizador dedicado `upexnote_app` (dono da base) — NÃO usar o superuser `postgres` na app.
- Segurança a endurecer depois: restringir a porta pública por firewall ao IP do utilizador, ou fechar e usar túnel SSH.
- Escrita best-effort a partir do worker: ficheiro local primeiro (nunca se perde), depois linha no Postgres; tolera VPS offline.

### Próximo passo
- Utilizador cria a base + role no DBeaver. Depois: schema `transcriptions` (metadados + texto clean/raw), config local + password no Credential Manager, e escrita best-effort no worker. Backup/dump do Postgres a planear (a VPS também é ponto único de falha).

### Registro — 2026-07-12 (f): decisão de armazenamento revista — Postgres na VPS (não SQLite)

### O que mudou
- Revista a decisão do Registro (e). Em vez de um índice SQLite local, o histórico/metadados de transcrições vai para o **Postgres já existente na VPS** (Docker), reutilizando o ambiente.

### Evidência / raciocínio (feedback do utilizador)
- Criar SQLite seria uma segunda tecnologia + nova instância, quando já há Postgres a correr na VPS (acedido por DBeaver via SSH).
- Durabilidade: dados só locais morrem com a máquina. (Nota: os *scripts* já estão seguros no GitHub; o que falta proteger fora da máquina são os *dados*.)
- Um banco serve para histórico, dashboards e cruzar consumo: custo por motor, motor mais usado, tempo de processamento, tipo de atividade mais frequente.

### Decisão
- Base de metadados/histórico = Postgres na VPS.
- Guardrails de falha: (1) ficheiro local é o artefacto primário, gravado primeiro; escrita no Postgres é best-effort e reconcilia se a VPS estiver offline (nunca se perde uma transcrição já paga); (2) o Postgres precisa de dump/backup próprio (a VPS é ponto único de falha); (3) o fluxo de transcrever tem de funcionar mesmo com a VPS em baixo.

### Pendente (decisão do utilizador)
- Texto do transcript vai para a VPS ou só metadados? (privacidade de conteúdo sensível — litígio/confidencial). Hipótese: guardar texto por defeito com marcação "privado/local-only" para os sensíveis.
- Caminho de rede: túnel SSH a partir da app vs porta Postgres exposta com firewall/TLS.
- Password do Postgres no Windows Credential Manager (o utilizador introduz; a IA nunca lhe toca).

### Próximo passo
- Definir os dois pontos pendentes; depois desenhar o schema (tabela de transcrições + eventos) e a escrita best-effort a partir do worker.

### Registro — 2026-07-12 (e): seletor de ficheiro + organização do storage

### O que mudou
- Seletor de ficheiro nativo (plugin dialog do Tauri): botão "Escolher…" abre o explorador do Windows; o campo de texto continua a aceitar um caminho colado.
- Organização do storage por dia/motor: `storage/transcripts/<AAAA-MM-DD>/<motor>/<origem>__<data>__<motor>__<kind>.txt` (nova função `transcript_path` em `paths.py`; removida a antiga `output_path`). Os 4 motores foram atualizados. Ficheiros existentes reorganizados para a nova estrutura.

### Evidência / teste
- Seletor validado a funcionar (escolha de `processos jira.mp4`, transcrição OK).
- `transcript_path` testada para os 4 motores (caminhos e nomes corretos). Registo importa os 4 motores sem erro.

### Decisão
- **Não zipar** e **não usar banco por espaço**: transcripts são texto (~20 KB), o espaço nunca é o gargalo. A preocupação real é organização, resolvida por pastas por dia/motor + nome auto-descritivo.
- Banco de dados fica para a Biblioteca (índice local SQLite para pesquisa) e, mais tarde, Postgres/VPS para sincronização — não para espaço.

### Impacto em dados, custo ou privacidade
- Nenhum custo. Só reorganização de ficheiros de texto locais (fora do Git).

### Próximo passo
- Ecrã de Definições (gerir chaves pela UI). Depois: empacotamento (worker como sidecar) e a Biblioteca com índice.

### Registro — 2026-07-12 (d): primeira interface funcional (transcrição ponta a ponta)

### O que mudou
- Ponte interface↔worker implementada em Rust (`apps/desktop/src-tauri/src/lib.rs`): comandos `list_engines`, `check_key` e `transcribe`. O `transcribe` corre a CLI Python numa thread e transmite cada linha NDJSON como evento Tauri (`worker://event` / `worker://done`).
- Primeiro ecrã real do UpexNote (`apps/desktop/src/App.tsx` + `App.css`): wordmark + tagline, tema claro/escuro (persistente), seletor de motor preenchido a partir do worker, campo de caminho do ficheiro, progresso em etapas (Enviar→Submeter→Transcrever→Finalizar) com cronómetro, e vista de resultado com validação/custo/duração/idioma + copiar.
- Título e dimensões da janela ajustados (`tauri.conf.json`).

### Evidência / teste
- **Transcrição de ponta a ponta feita inteiramente dentro da app** (não pela CLI): gravação real ~20 min, motor AssemblyAI. Resultado na janela: Validação OK, idioma pt, ~$0.0713, diarização (Speakers A–D), code-switching PT/EN preservado. Guardado em `storage/transcripts/assemblyai/...__clean.txt`.
- Confirma a cadeia React → comando Rust → worker Python → eventos de volta à UI, com progresso ao vivo.

### Decisão
- Integração via comandos Rust + eventos (não via shell plugin): mantém o modelo de permissões simples e o streaming NDJSON limpo.
- Em desenvolvimento, o Rust localiza `services/worker` a partir de `CARGO_MANIFEST_DIR`. Para a app empacotada isto terá de mudar (worker como sidecar) — pendente.

### Impacto em dados, custo ou privacidade
- Uma chamada real à AssemblyAI (~$0.07). Chave lida do Windows Credential Manager pelo worker; nunca passou pela UI nem por argumentos.
- Vídeo lido do caminho original; só o transcript foi escrito, em `storage/` (fora do Git).

### Próximo passo
- Seletor de ficheiro nativo (plugin dialog) em vez de colar o caminho; ecrã de Definições para gravar chaves pela UI; depois empacotamento (worker como sidecar) e as abas de contexto/estudo.

### Registro — 2026-07-12 (c): saída do Google Drive + scaffold da interface

### O que mudou
- Criado o scaffold da interface em `apps/desktop`: Tauri 2 + React + TypeScript + Vite (nome do pacote/crate `upexnote`, produto `UpexNote`, identificador `com.upexflow.upexnote`).
- **Desenvolvimento saiu do Google Drive.** A raiz mudou de `G:\My Drive\Projects\upexflow\upexnote` para `C:\Users\cunha\Projects\upexflow\upexnote` (disco local). Motivo: `npm install` falha no Google Drive File Stream com `EBADF`/`TAR_ENTRY_ERROR` — o sistema de ficheiros virtual não aguenta as milhares de escritas do `node_modules`. Isto bloqueia qualquer build de JS no Drive, não só o Tauri.
- Método da mudança (sem perda): commit + push de tudo para o GitHub, depois `git clone` fresco para o disco local. O GitHub é agora, explicitamente, a fonte de verdade e a sincronização — não o Drive.

### Evidência / teste
- Pré-requisitos do Tauri confirmados no Windows: Rust 1.97.0 (toolchain msvc), Cargo, compilador C++ (`cl.exe`, VS 2022 Build Tools), WebView2. Um mini-programa Rust compilou+linkou+correu (linker OK).
- `npm install` no disco local: OK (73 pacotes). `npm run build` (Vite): OK.
- Aviso pendente: Node instalado é v18.16.1, mas o Vite 7 pede Node 20+/22+ (Node 18 está em fim de vida). Recomendada atualização do Node para 22 LTS antes do primeiro `tauri dev`.
- Primeiro `tauri dev` (compilação Rust nativa + janela) ainda não foi corrido.

### Decisão
- Interface confirmada em Tauri 2 + React/TS (segue o plano da arquitetura).
- Código de projeto vive em disco local; Drive deixa de ser destino de desenvolvimento. A cópia antiga em `G:` fica órfã (a confirmar com o utilizador antes de apagar dados do Drive dele).

### Impacto em dados, custo ou privacidade
- Nenhum dado sensível movido; só código, via GitHub. Sem custo.
- Passa a haver menos exposição em nuvem: o código de trabalho já não é sincronizado pelo Drive.

### Próximo passo
- Atualizar Node para 22 LTS; correr o primeiro `tauri dev` (validar janela nativa); depois ligar a UI à CLI do worker.

### Registro — 2026-07-12 (b): CLI NDJSON do worker

### O que mudou
- Criado o ponto de entrada `services/worker/transcription/cli.py` (+ `__main__.py`): CLI que comunica por NDJSON (um objeto JSON por linha no stdout), pensada para o shell Tauri a lançar como sidecar e ler o progresso em tempo real.
- Comandos: `engines` (lista motores + se a chave está configurada), `transcribe --engine <id> --file <caminho>` (eventos `start`/`progress`/`result`|`error`), `set-key --name <NOME>` (lê por stdin sem eco, guarda no Credential Manager), `check-key --name <NOME>` (diz se está configurada, sem revelar valor).
- Protocolo de eventos documentado em `services/worker/README.md`.

### Evidência / teste
- Testados sem chamar APIs: `engines`, `check-key`, e os caminhos de erro do `transcribe` (motor desconhecido, ficheiro inexistente, chave em falta) — todos emitem NDJSON válido e códigos de saída corretos. `python -m transcription` e `python -m transcription.cli` funcionam.
- **Teste real de ponta a ponta (2026-07-12):** `transcribe --engine assemblyai` sobre uma gravação real de ~20,4 min (942 MB, reunião PT com code-switching EN). Resultado: validação OK, zero alucinações, 4 interlocutores diarizados, ~$0,071, 111 s de processamento; code-switching preservado corretamente (frase em inglês manteve-se em inglês). Confirma que a migração não introduziu regressão face ao protótipo. Os transcripts `__raw`/`__clean` foram gravados em `storage/transcripts/assemblyai/` e ficaram fora do Git (gitignored), como esperado. As três chaves (AssemblyAI, OpenAI, Deepgram) foram (re)gravadas pelo utilizador via `set-key` no novo `SERVICE_NAME` "UpexNote".

### Decisão
- CLI + NDJSON escolhida em vez de servidor HTTP local para o primeiro entrypoint: sem gestão de portas/servidor/CORS, e encaixa diretamente no callback `log=` que os motores já têm.
- Chaves nunca passam por argv (visível na lista de processos); `set-key` lê por stdin sem eco e é corrido pelo próprio utilizador.

### Impacto em dados, custo ou privacidade
- Nenhum dado movido; sem custo (nenhuma API chamada).
- Reforça a política de chaves: a chave nunca aparece no comando nem no histórico do terminal.

### Próximo passo
- Ligar o `apps/desktop` (Tauri) a esta CLI.

### Registro — 2026-07-12 (a): migração dos pipelines

### O que mudou
- Pipelines de transcrição migrados de `C:\Users\cunha\Project\scripts\` (protótipo Tkinter) para `services/worker/transcription/` neste repositório, como pacote Python (`assemblyai.py`, `whisper_openai.py`, `deepgram.py`, `gpt4o_openai.py`, `audio_chunks.py`, `transcript_utils.py`, `paths.py`, `credentials.py`, `registry.py`).
- Destino dos transcripts gerados mudou de `resultados\<motor>\` (protótipo) para `storage/transcripts/<motor>/` (gitignorado), alinhado com a tabela de dados do `ARCHITECTURE.md`.
- `credentials.py` passou a usar `SERVICE_NAME = "UpexNote"` no Windows Credential Manager (antes era `"TranscricaoReunioes"`) — chaves guardadas pelo protótipo antigo não são vistas automaticamente pelo novo worker; terão de ser reintroduzidas quando existir UI/CLI para tal.
- Acoplamento ao Tkinter removido; `registry.py` expõe um `ENGINES` dict framework-agnostic para uma futura CLI/IPC usar.

### Evidência / teste
- `python -c "from transcription import registry; ..."` a partir de `services/worker/` confirmou os 4 motores registados e `paths.output_path()` a resolver corretamente para `G:\My Drive\Projects\upexflow\upexnote\storage\transcripts\<motor>\`.
- Não foi feito um teste de transcrição real (ponta-a-ponta com chamada às APIs) nesta migração — só verificação de imports e resolução de caminhos.

### Decisão
- Nenhuma lógica de motor foi alterada (parâmetros, chunking, deteção de alucinações, validação permanecem exatamente como validados no protótipo).
- gpt-4o-transcribe foi mantido no código (não descartado do repositório) por já estar documentado como referência, mas continua marcado como não recomendado.

### Impacto em dados, custo ou privacidade
- Nenhum. Nenhum vídeo, áudio, transcript ou chave foi movido/copiado — só código.
- Sem custo (nenhuma API foi chamada).

### Próximo passo
- Construir o ponto de entrada (CLI/IPC) que liga `apps/desktop` a `services/worker`.

