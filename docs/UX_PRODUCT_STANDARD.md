# UpexNote - Padrao de Experiencia do Produto

## Objetivo

Transformar a arquitetura tecnica madura do UpexNote em uma experiencia desktop que uma pessoa consiga usar diariamente sem treinamento: clara, rapida, coerente e visualmente segura.

## Regra de aceite

Uma tela so e considerada pronta quando responde, em poucos segundos, a quatro perguntas:

1. Onde estou?
2. O que preciso fazer agora?
3. O que aconteceu com minha acao?
4. Como volto ou aprofundo o contexto sem me perder?

## Hierarquia de navegacao

- O menu lateral e a arquitetura de navegacao do aplicativo.
- Um modulo pode expandir submodulos no proprio menu; nao usar fileiras de abas horizontais como navegacao principal.
- O conteudo central exibe uma unica tarefa operacional por vez: visao geral, fila/lista ou detalhe.
- O detalhe sempre oferece retorno claro para a lista de origem.

## Prateleiras e ecossistemas

- A navegacao principal organiza prateleiras de produto, nao uma lista plana de telas.
- `Transcriptions` agrupa nova transcricao e Library; futuras funcoes pontuais de transcricao entram nesse ecossistema sem crescer o menu raiz indiscriminadamente.
- `Notebooks` e uma prateleira principal separada. A arvore de projetos, pastas, cadernos, secoes e notas vive dentro do workspace, nao no menu global.
- `Settings` pode expandir destinos para Appearance, Typography, Layout, Storage, Engines, Privacy, Account e Security. Enquanto partilharem a tela atual, cada destino usa ancora estavel e posiciona o utilizador exatamente na secao pedida.
- `Administration` continua como prateleira de governanca e pode agregar dominios separados, como Support e Data Studio, sem misturar seus schemas.
- Menu organiza experiencia; schema delimita responsabilidade e ciclo de vida. Nao criar correspondencia artificial de um para um.
- Em menu recolhido, icones, tooltips e estado ativo preservam a orientacao. Em menu expandido, pais e filhos deixam clara a hierarquia.

## Padrao operacional

Todo modulo com dados operacionais segue, quando aplicavel:

`visao geral -> filtros -> lista/fila -> detalhe -> acao/contexto`

- Visao geral: indicadores acionaveis, nao enfeites.
- Filtros: controles explicitos com periodo, estado e busca; nao colecoes de badges sem acao.
- Lista: colunas essenciais, densidade legivel e nenhuma barra horizontal visivel no desktop normal.
- Detalhe: conteudo principal primeiro; metadados e acoes secundarias em contexto lateral ou bloco proprio.

## Componentes e estados

- Acoes frequentes recebem botao nomeado; acoes secundarias de tabela usam icones com `title` e `aria-label`.
- Campos de texto e resposta usam fundo do tema, contraste correto e tamanho proporcional ao conteudo esperado.
- Estados de hover, foco, selecao, vazio, carregamento, erro e sucesso precisam ser visiveis e coerentes em todos os temas.
- Scroll e parte do aplicativo: discreto, com a cor do tema, e nunca usado para compensar uma tabela ou layout mal dimensionado.

## Artefactos derivados do transcript

- O detalhe do transcript pode aprofundar a jornada em `detalhe -> artefacto derivado`, sem perder a origem. O artefacto sempre oferece uma acao clara para voltar ao transcript que o gerou.
- O leitor estruturado da v0.29.1 e uma **previa estruturada**: ajuda a compreender objetivo, assuntos, decisoes e conceitos antes de criar material editavel. Nao e o Caderno nem o documento pessoal final.
- A implementacao atual usa a faixa `Documentos gerados`; a direcao aprovada e evoluir a linguagem para `Previa estruturada`, imediatamente depois dos badges e antes do conteudo principal.
- Cada documento e representado por um chip acionavel. O titulo completo deve permanecer legivel: em espaco reduzido, quebra em mais de uma linha em vez de usar reticencias ou cortar informacao. `title` pode complementar, mas nao substituir o texto visivel.
- Um transcript pode ter varios documentos derivados; a faixa precisa acomodar essa relacao sem transformar os chips em navegacao principal do aplicativo.
- O leitor estruturado abre com retorno para a origem, titulo completo, metadados relevantes e a acao secundaria `Copiar`. Enquanto o ADF-01 permanecer em leitura, nao exibe campos editaveis nem affordances de edicao.
- A ordem do documento e: cabecalho e metadados, objetivo, blocos estruturados na sequencia persistida, glossario e identificacao final de que o material e derivado.
- Blocos mantem rotulo semantico e conteudo legivel. Risco, decisao e acao recebem diferenciacao visual; trechos preservam falante e timestamp quando disponiveis; listas e pares campo/valor sao renderizados como estrutura, nunca como JSON cru.
- Em janela estreita, menu lateral pode compactar para icones; titulos, badges, chips e cartoes quebram linha; pares campo/valor e glossario empilham. Nao pode haver sobreposicao, truncamento de rotulos ou overflow horizontal da pagina.
- Falha ao carregar um documento precisa permanecer visivel no contexto do transcript, com estado de erro explicito; nunca retornar silenciosamente como se o clique nao tivesse funcionado.

## Previa, Caderno e painel pos-transcricao

- O fluxo mental e `transcript -> previa estruturada -> Caderno`; cada camada permanece identificavel.
- Sem previa: oferecer `Criar previa`, com fornecedor e custo visiveis antes de qualquer chamada paga.
- Com previa: oferecer `Ver previa` e `Salvar no Caderno`.
- Com nota ja criada: oferecer `Abrir no Caderno` e indicar o destino.
- Depois de uma transcricao concluida, as acoes aparecem no mesmo workspace sem reload. Na primeira utilizacao, uma mensagem explica as camadas e informa que a pessoa pode adiar e continuar depois pela Library; nas seguintes, o painel fica compacto.
- `Salvar no Caderno` pede ou confirma o destino hierarquico e cria uma copia editavel com linhagem. Nunca torna a previa editavel nem altera o transcript.
- O Caderno permite documento visualmente continuo, sem bordas obrigatorias em cada bloco. Estrutura interna e IDs estaveis permanecem invisiveis para sustentar historico, baloes e referencias.
- Barra superior concentra formatacao; corpo central concentra escrita; painel lateral concentra comentarios, referencias, dicionario, glossario e palavras-chave.
- Selecao de palavra, trecho ou secao pode abrir menu contextual para comentar, destacar, referenciar, consultar definicao e adicionar ao glossario.
- A arvore interna precisa deixar claro projeto/pasta, caderno, secao e nota, com criacao, movimento, vazio e retorno previsiveis.
- O contrato detalhado e os limites de dados vivem em `NOTEBOOK_ARCHITECTURE.md`.

### Validacao de referencia — ADF-01

- Validado na v0.29.1 em 08/08/2026 com o transcript #23 e o documento #9, em janela normal e estreita.
- Evidencia cobriu faixa e chip de documentos, cabecalho, objetivo, inicio/meio/fim dos 30 blocos, 34 entradas de glossario e retorno ao transcript de origem.
- O leitor permaneceu em so leitura, sem cortes, sobreposicoes, truncamentos ou estados vazios incorretos.

## Privacidade e administracao

- Audit apresenta eventos semanticamente e filtra segredos, tokens, hashes, provider scopes e identificadores tecnicos desnecessarios.
- Telemetria consentida e agregada/anonima; nao deve ser reinterpretada como rastreamento pessoal.
- Diagnostico individual futuro exige consentimento proprio, identificador pseudonimo e trilha clara para um chamado de suporte.
- Webhooks e integracoes pertencem a um modulo dedicado, com chaves protegidas e logs de entrega; nunca ao Audit.

## Processo antes de publicar um modulo

1. Confirmar fluxo e estados com o dominio de negocio.
2. Desenhar a hierarquia de navegacao e a tela vazia antes dos dados reais.
3. Implementar com componentes e tokens existentes.
4. Testar no tamanho real da janela desktop, inclusive texto longo, dados vazios e estados de erro.
5. Validar visualmente antes de declarar o modulo concluido.
