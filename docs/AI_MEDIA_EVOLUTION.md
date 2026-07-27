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
  → conteúdo formatado derivado
  → leitura e edição
  → reprodução do áudio original ou síntese de voz
  → estudo, ações, quiz e chat ancorado
```

Cada camada permanece identificável. Uma formatação, resumo ou correção nunca substitui silenciosamente o material de origem.

## 3. Formatação e Estudo

A futura superfície deve funcionar como editor e leitor do mesmo material.

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
