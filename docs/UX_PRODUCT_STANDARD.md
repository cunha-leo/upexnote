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
