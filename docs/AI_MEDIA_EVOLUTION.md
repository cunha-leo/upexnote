# UpexNote — evolução de IA, leitura e mídia

> **Natureza:** especificação futura e memória de produto para Formatação, Estudo, Leitura, Reprodução e modo ao vivo.
>
> **Não representa:** autorização imediata de implementação, escolha definitiva de fornecedor ou permissão para enviar conteúdo privado a serviços externos.
>
> **Origem:** comunicados da AssemblyAI e Deepgram de julho de 2026, cruzados com a implementação atual do UpexNote.

## 1. Objetivo

Preservar as capacidades que deverão ser consideradas quando o UpexNote evoluir do transcript para conteúdo formatado, estudo, revisão e consumo multimídia.

O utilizador deverá poder:

- transformar o transcript em formatos de reunião, aula, resumo ou estudo;
- editar o conteúdo derivado sem alterar o transcript bruto;
- ler o conteúdo visualmente;
- ouvir o conteúdo do início ao fim ou a partir de um ponto escolhido;
- controlar velocidade, voz e idioma;
- acompanhar no texto a palavra ou o trecho reproduzido;
- navegar entre texto, áudio original e voz sintetizada;
- gerar ações, tópicos, decisões, riscos e materiais de estudo.

## 2. Jornada futura

```text
áudio ou vídeo
  → transcript bruto imutável
  → transcript limpo validado
  → prévia estruturada derivada em documents
  → nota editável e hierárquica em notebooks
  → leitura, edição e estudo
  → reprodução do áudio original ou síntese de voz
  → estudo, ações, quiz e chat ancorado
```

Cada camada permanece identificável. Uma formatação, resumo ou correção nunca substitui silenciosamente o material de origem.

## 3. Prévia, Caderno, Formatação e Estudo

A prévia e o Caderno são superfícies relacionadas, mas não idênticas. A prévia estruturada em `documents` serve à compreensão rápida e permanece em só leitura; `Salvar no Caderno` cria material editável no domínio `notebooks`, preservando a linhagem sem alterar a origem. O editor e leitor do Caderno trabalham sobre a nota pessoal.

O contrato arquitetural, a hierarquia e a separação de responsabilidades estão em `NOTEBOOK_ARCHITECTURE.md`, cuja leitura é obrigatória para qualquer implementação deste fluxo.

### Capacidades mínimas

- formatos predefinidos: reunião, ata, aula, resumo executivo, guia de estudo, tópicos e perguntas e respostas;
- títulos, seções, listas, decisões, ações, responsáveis, datas, riscos e dúvidas;
- edição manual do conteúdo derivado;
- comparação ou retorno ao transcript de origem;
- histórico de versões;
- indicação do motor e processamento utilizados;
- exportação sem perder a estrutura;
- geração de Action Items quando solicitada;
- suporte a PT-PT, PT-BR, inglês e futuros idiomas validados;
- preservação explícita de code-switching.

### Inteligência de conteúdo a avaliar

- AssemblyAI LLM Gateway para Action Items;
- Deepgram Audio Intelligence para sumarização, tópicos, sentimento e insights;
- outros modelos ou processamento local, comparados em qualidade, custo e privacidade;
- extração própria e independente de fornecedor quando isso reduzir acoplamento.

Promessas de fornecedor não substituem testes com reuniões, aulas e vídeos representativos do uso real.

## 4. Modo Leitura

O quadro que apresenta o conteúdo formatado também deve oferecer leitura confortável.

### Controles previstos

- reproduzir, pausar, reiniciar e continuar de onde parou;
- clicar em parágrafo, frase ou palavra para começar naquele ponto;
- voltar ou avançar por frase, parágrafo ou intervalo;
- velocidades `0,5×`, `0,75×`, `1×`, `1,25×`, `1,5×`, `1,75×` e `2×`;
- seleção de voz e idioma;
- volume e dispositivo de saída quando disponível;
- destaque sincronizado do trecho e, quando houver timestamps, da palavra atual;
- atalhos de teclado e controles acessíveis;
- persistência opcional da posição de leitura por documento.

O modo de leitura terá duas fontes claramente separadas:

1. **Áudio original:** reprodução sincronizada com o transcript.
2. **Síntese de voz:** leitura do transcript, formatação, resumo ou material de estudo.

## 5. Sincronização por palavra

Timestamps por palavra permitem:

- clicar no texto e saltar ao instante correspondente;
- destacar palavras durante a reprodução;
- gerar legendas;
- revisar erros no contexto exato;
- selecionar e repetir trechos;
- criar clipes ou citações com referência temporal;
- navegar em reuniões e aulas longas.

O Deepgram Flux com `start` e `end` por palavra deve ser avaliado no futuro modo ao vivo. Para arquivos, devem ser comparadas as informações já devolvidas pelos motores existentes.

O modelo interno deverá aceitar timestamps opcionais por palavra sem obrigar todos os motores a fornecê-los.

## 6. Vozes e síntese de fala

As vozes Pocket da AssemblyAI e as vozes da Deepgram TTS são candidatas, não decisões definitivas.

Antes de escolher um fornecedor, avaliar:

- naturalidade em PT-PT, PT-BR e inglês;
- troca de idioma dentro do conteúdo;
- pronúncia de nomes e termos técnicos;
- velocidade, estabilidade e tempo até o primeiro áudio;
- streaming e alinhamento com texto;
- custo, licenciamento e uso comercial;
- privacidade e retenção;
- alternativa local/offline.

Preferências de voz, velocidade e idioma pertencem ao utilizador e devem ser persistidas localmente.

## 7. Transcrição e idiomas

### Estado atual

- AssemblyAI Universal-3.5 Pro permanece o motor principal para arquivos.
- O UpexNote já usa explicitamente `universal-3-5-pro`, detecção de idioma, diarização, contexto e termos importantes.
- Deepgram Nova-3 permanece alternativa e candidato para baixa latência/modo ao vivo.
- O UpexNote já usa Nova-3 multilíngue, numerais, timestamps, utterances, parágrafos e diarização.

### Melhorias a acompanhar

- Universal-3.5 Pro em Async, Sync e Realtime;
- contexto entre turnos para captura ou agentes ao vivo;
- code-switching e diarização conjunta;
- melhorias automáticas do Nova-3 por idioma;
- Flux multilíngue, timestamps por palavra e numerais;
- expansão de idiomas somente depois de validação real;
- comparação contínua de qualidade, custo, latência e diarização.

O motor principal não será trocado por causa de divulgação comercial. A mudança exige benchmark próprio e reversível.

## 8. Modo ao vivo e agentes

Recursos de contexto, interrupção e relatório de latência interessam ao futuro modo ao vivo:

- captura local de microfone e loopback;
- transcrição incremental;
- contexto da conversa anterior;
- interrupção controlada de um agente;
- latência de STT, LLM, TTS e ponta a ponta;
- continuidade entre turnos;
- sincronização da fala com o texto;
- ações geradas ao final ou durante a sessão.

`LatencyReport` da Deepgram pode alimentar telemetria técnica agregada, mas nunca deve transportar áudio, texto privado ou identidade sem consentimento específico.

## 9. Privacidade e consentimento

- áudio, vídeo, transcript e conteúdo derivado são privados por padrão;
- reprodução local não exige envio externo;
- síntese ou análise cloud exige ação e consentimento explícitos;
- antes de processar, informar fornecedor, conteúdo enviado, finalidade e possível custo;
- credenciais permanecem no Windows Credential Manager;
- respostas de IA são artefatos derivados e identificam sua origem;
- telemetria nunca inclui áudio, transcript, resumo, sentimento ou Action Items;
- quando possível, oferecer alternativa local/offline.

## 10. Arquitetura a preservar

- abstrair STT, TTS e inteligência de conteúdo por capacidades, sem acoplar a interface a fornecedor;
- manter formatos portáveis para palavras, timestamps, falantes, idiomas e segmentos;
- guardar preferências e posição de leitura localmente;
- separar áudio original de áudio sintetizado;
- suportar cancelamento, progresso, erro e retomada;
- não persistir respostas completas de fornecedores sem necessidade;
- novos domínios de banco usam schema PostgreSQL separado e em inglês;
- conteúdos privados permanecem locais, salvo escolha explícita do utilizador.

## 11. Quando consultar este documento

Antes de implementar:

- Formatação;
- contexto estruturado;
- estudo e quiz;
- leitura e edição;
- player de áudio;
- text-to-speech;
- destaque sincronizado;
- timestamps por palavra;
- novos idiomas;
- captura ao vivo;
- agente de voz;
- Action Items, tópicos, sentimento ou insights.

## 12. Ordem sugerida

1. Leitor/editor de transcript e conteúdo derivado.
2. Formatações predefinidas com histórico e origem.
3. Player do áudio original com navegação por segmento.
4. Timestamps e navegação por palavra quando disponíveis.
5. Síntese de voz, velocidades e escolha de voz/idioma.
6. Action Items, tópicos e materiais de estudo sob solicitação.
7. Captura e transcrição ao vivo.
8. Agentes de voz, interrupções e contexto entre turnos.

Esta ordem registra dependências; não é um backlog aprovado.

## Atualização operacional — 26/11/2026 — expansão multimodelos em homologação

Na branch `feat/desktop-editions`, foram adicionados ao registro de transcrição os candidatos AssemblyAI-STT-3.7 (ID de API `assemblyai-stt-3-7`) e OpenAI `gpt-4o-mini-transcribe`, com IDs internos independentes, sem substituir os quatro motores anteriores. Ambos passaram em smoke real de áudio curto (~23s); falta benchmark longo, multilíngue, taxa de alucinação e validação funcional do aplicativo instalado. O motor principal aprovado permanece Universal-3.5 Pro até nova decisão baseada em evidência.

Os registros de transcrição e formatação expõem metadados de provedor/modelo, para seletor dependente dentro dos controles existentes; a aparência geral aprovada deve permanecer intacta. Definições passou a oferecer entrada protegida de chaves também para DeepSeek, xAI/Grok, Anthropic/Claude, Gemini, ElevenLabs e OrcaRouter. Estes dois últimos são apenas suporte a cadastro de credencial nesta fase, não adaptadores operacionais.

O catálogo deve continuar extensível por capacidades (STT, formatação, tradução, TTS, interação com caderno e descoberta via OrcaRouter), preservando as APIs diretas BYOK, preços históricos e documentação visual como referências, sem tratar todos os modelos exibidos em dashboards de provedores como automaticamente suportados pelo backend. Credencial cadastrada não significa endpoint homologado. Consulte `releases/R03.1/MULTIMODEL-STATUS-2026-11-26.md` (local) para evidências e bloqueios de fechamento.


## Decisão de produto confirmada — 26/11/2026 às 14h03
O UpexNote não deve limitar artificialmente escolha a modelos vendidos como STT. Critério: compatibilidade técnica por tarefa, comprovada por execução, com pipeline explícito quando multi-etapa. Preservar UX aprovada: em Transcrever, Provedor -> Modelo, recomendados acima dos outros compatíveis, e descrição dinâmica abaixo (fidelidade, custo, idioma, velocidade, restrições e grau de validação). BYOK: usuário pode experimentar alternativas e assume custos; nunca oferecer modelo tecnicamente incompatível como funcional. LLM texto não transcreve áudio diretamente; pode refinar resultado após STT. Biblioteca terá seu próprio catálogo para formatação/resumo, Caderno outro para interação com IA, voz/VSL outra família incluindo ElevenLabs. OrcaRouter removido da interface; Groq (STT) é distinto de Grok/xAI (LLM). Não redesenhar nem acrescentar cartões/painéis. Diferenciar chave armazenada de API validada.
Evidências 26/11: DeepSeek deepseek-flash HTTP 200 e adaptador formatting OK; xAI grok-4.20-0309-non-reasoning HTTP 200 e adaptador OK; Gemini gemini-3-flash-preview HTTP 200 e adaptador OK; Anthropic HTTP 401 — credencial nova necessária. Catálogo STT fonte: 10 modelos, AssemblyAI 3/OpenAI 3/Deepgram 2/Groq 2; Universal-2, Nova-2 e Groq V3/Turbo ainda carecem de smoke e revisão de parâmetros e custos, não homologados. 37 unittest aprovados e frontend compilado; o binário anterior instalado não reflete novas alterações até rebuild. Não declarar checkpoint FULL.


## 26/11/2026 — checkpoint incremental multimodelos (branch feat/desktop-editions)

Contrato aprovado pelo proprietário: **Provedor → Modelo**, dentro da interface existente, modelos recomendados primeiro por provedor, alternativas funcionais depois, texto explicativo dinâmico e BYOK. Não restringir por marketing de modelo; incluir LLM multimodal que receba áudio diretamente, mas nunca usar modelo somente texto como transcritor direto sem pipeline explícito. Bibliotecas, Caderno e futuras funções TTS/VSL têm catálogos por capacidade, não obrigatoriamente idênticos. Sem novos painéis ou redesign.

Catálogo de transcrição no worker: **13 modelos e seis provedores** (AssemblyAI 3, OpenAI 4, Deepgram 2, Groq 2, Gemini 1, xAI/Grok 1). Os novos GPT-Transcribe, Gemini Flash multimodal com áudio e Grok Voice STT 2.0 passaram em chamadas reais de ~23 s (HTTP 200, saída 0, validação ok), mas com nível de precisão de timestamps diferente; custos monetários ainda não mensurados são `null`, não zero. AssemblyAI STT-3.7 e GPT4o Mini antigos passaram smokes; Universal-2 e Deepgram Nova-2 passaram após correção do idioma: Nova-2 `language=multi` cobre só inglês+espanhol, usar `detect_language=true` para PT e outros idiomas; não substitui o Nova-3 no code-switching. Groq V3/Turbo têm adaptadores mas `GROQ_API_KEY` não está configurada; falta smoke com chave própria.

Catálogo de formatação da Biblioteca: **13 modelos e cinco provedores** (DeepSeek 2, xAI/Grok 2, OpenAI 3, Anthropic 4, Gemini 2). DeepSeek Flash, Grok4.20, Gemini3 Flash e Claude Haiku4.5 funcionaram em teste curto anterior; os novos GPT5.4 Nano, Grok4.3, Claude Haiku5.5, Gemini3.1 Flash Lite produziram documento estruturado válido no worker. DeepSeek V4 Pro, GPT5.4 Mini, Claude Sonnet5.5 passaram apenas JSON curto; o ensaio de documento longo do DeepSeek Pro foi interrompido por latência/cautela de custos. Gemini 3.1 Pro Preview retornou 429 quota, não publicado. Novos modelos são experimentais até benchmarks longos.

Todas as sete credenciais históricas de provedores foram testadas com APIs reais nesta missão/turnos anteriores; Anthropic e Gemini foram substituídas pelo proprietário e reconfirmadas HTTP 200. Campo `Guardada` da interface indica chave armazenada, **não** saúde da API. Gemini usa `x-goog-api-key` no cabeçalho para não incluir segredo na URL. Google Pro não equivale a cotas pagas da Gemini API. OrcaRouter saiu da UI; ElevenLabs reservado para futuro TTS/VSL, sem adaptador ainda. OpenAI Whisper/gpt-4o legados encerram em 26/02/2027 segundo documentação oficial, sem remover IDs históricos. Sem alteração da main, bancos ou experiência visual; builds e aceitação visual posteriores precisam ser verificados; Recovery R03.1 DOCUMENTAL preservado.


## 26/11/2026 — fechamento da distribuição R03.1 FULL

O seletor BYOK `Provedor → Modelo` com metadados dinâmicos está nas duas edições desktop aprovadas; Biblioteca/Prévia estruturada teve alinhamento Perfil corrigido, com aceite visual do proprietário em Personal e Internal. O catálogo atual tem 13 STT em seis provedores e 13 motores de formatação em cinco provedores. Tauri/NSIS e regressões executados. Opções marcadas em teste não têm benchmark longo garantido; Google Pro não implica quotas específicas da API; modelos Groq aguardam chave própria. Caderno com IA, tradução e voz/VSL são evoluções futuras. Referência: `docs/RELEASE_R03_1_FULL_2026-11-26.md`.
