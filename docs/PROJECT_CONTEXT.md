# UpexNote — Contexto Vivo do Projeto

> **Objetivo deste documento:** manter uma fonte de verdade legível por pessoas e IAs. Deve ser atualizado a cada decisão, teste relevante, alteração estrutural ou mudança de estado. Não contém chaves, vídeos, áudios privados nem transcrições sensíveis.

**Última atualização:** 12 de julho de 2026 (migração dos pipelines para `services/worker`)  
**Produto:** UpexNote  
**Ecossistema:** UpexFlow  
**Repositório:** `https://github.com/cunha-leo/upexnote` (privado)  
**Raiz local de desenvolvimento:** `G:\My Drive\Projects\upexflow\upexnote`

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
G:\My Drive\Projects\upexflow\upexnote
├─ apps/desktop/        interface do UpexNote
├─ services/worker/     pipelines locais e integração de mídia
├─ docs/                documentação de produto e engenharia
├─ storage/             conteúdo gerado pelo utilizador (ignorado pelo Git)
├─ README.md
└─ .gitignore
```

O seletor de arquivos deverá aceitar qualquer caminho do Windows. Selecionar um vídeo de um Drive corporativo/pessoal não significa copiá-lo para a pasta do projeto.

---

## 8. Infraestrutura existente

### Google Drive

- Pasta remota principal criada para o produto: `My Drive/Projects/upexflow/upexnote`.
- Raiz local sincronizada: `G:\My Drive\Projects\upexflow\upexnote`.
- O Drive é a pasta de desenvolvimento e, opcionalmente, arquivo de derivados (TXT, Markdown, JSON, documentos e exportações).
- O Drive não é substituto de Git nem destino automático de mídia bruta.

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

### Próximo trabalho

1. Ligar o `apps/desktop` (Tauri + React) à CLI do worker: lançar o sidecar, mapear `engines`/`check-key` para o ecrã de definições e `transcribe` (eventos NDJSON) para a barra de progresso + vista de transcript.
3. Construir o primeiro fluxo: escolher arquivo → selecionar motor → acompanhar progresso → abrir transcript → guardar derivado.
4. Só depois adicionar contexto estruturado, estudo, chat, síntese de voz e sincronização com Postgres.

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

### Registro — 2026-07-12 (b): CLI NDJSON do worker

### O que mudou
- Criado o ponto de entrada `services/worker/transcription/cli.py` (+ `__main__.py`): CLI que comunica por NDJSON (um objeto JSON por linha no stdout), pensada para o shell Tauri a lançar como sidecar e ler o progresso em tempo real.
- Comandos: `engines` (lista motores + se a chave está configurada), `transcribe --engine <id> --file <caminho>` (eventos `start`/`progress`/`result`|`error`), `set-key --name <NOME>` (lê por stdin sem eco, guarda no Credential Manager), `check-key --name <NOME>` (diz se está configurada, sem revelar valor).
- Protocolo de eventos documentado em `services/worker/README.md`.

### Evidência / teste
- Testados sem chamar APIs: `engines`, `check-key`, e os caminhos de erro do `transcribe` (motor desconhecido, ficheiro inexistente, chave em falta) — todos emitem NDJSON válido e códigos de saída corretos. `python -m transcription` e `python -m transcription.cli` funcionam.
- Um `transcribe` real (com API) ainda não foi corrido através da CLI.

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

