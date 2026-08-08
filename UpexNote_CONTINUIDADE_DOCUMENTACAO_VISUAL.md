# UpexNote — Continuidade da Documentação Funcional e Visual

## 1. Objetivo deste arquivo

Este arquivo é o ponto de continuidade para uma nova sessão de IA. Ele deve ser lido junto com:

1. `UpexNote_Documentacao_Funcional_Visual_v1.0_FINAL` (DOCX, sem extensão no nome do arquivo, na pasta `Product Strategy & Validation` do Drive) — confirmar sempre se existe versão superior na mesma pasta antes de ler;
2. `docs/CONTEXT_ORCHESTRATION.md`, como porta de entrada e coordenador da ordem de leitura;
3. `docs/PROJECT_CONTEXT.md`, como matriz consolidada do estado real do produto;
4. `docs/FEATURE_VALIDATION_AND_ROADMAP.md`, como submatriz operacional que distribui a leitura para os documentos especializados e separa validação, execução, backlog e ideias futuras;
5. os documentos especializados indicados pela submatriz conforme a tarefa, especialmente `UX_PRODUCT_STANDARD.md`, `PRODUCT.md`, `ARCHITECTURE.md`, `AI_MEDIA_EVOLUTION.md`, `SUPPORT_ARCHITECTURE.md` e `DATA_STUDIO_ARCHITECTURE.md`.

A versão DOCX é uma consolidação parcial. Não recomece a documentação do zero.

> **Divergência conhecida (registrada em 08/08/2026):** o arquivo chama-se `v1.0_FINAL`, mas a capa e o rodapé internos declaram `Versão de trabalho v0.1 — captura parcial da aplicação v0.28.0`. O conteúdo é o que vale: é uma consolidação parcial, com lacunas de captura explicitamente listadas na própria seção 17 do DOCX. Não tratar `FINAL` no nome como aceite fechado de cobertura. A próxima revisão do DOCX deve reconciliar nome e versão interna.

## 2. Instrução mínima para a nova sessão

> Leia integralmente este MD e o DOCX anexado. Para contexto técnico adicional, siga a hierarquia `CONTEXT_ORCHESTRATION.md` → `PROJECT_CONTEXT.md` → `FEATURE_VALIDATION_AND_ROADMAP.md` → documentos especializados aplicáveis. Considere o DOCX como o estado visual consolidado até agora. Continue a coleta e catalogação a partir das lacunas registradas, sem reconstruir telas já documentadas. Para cada nova captura, identifique fluxo, tela, perfil, objetivo, ações, dados, estados, regra de privacidade/segurança e evidência. Não invente funcionalidades. Preserve a separação entre implementado, backlog e ideia futura.

## 3. Estado consolidado

A versão atual do DOCX (arquivo `v1.0_FINAL`, versão interna `v0.1`) já documenta, com capturas:

- abertura e login administrativo;
- senha administrativa, Google OAuth e MFA;
- tela inicial do administrador;
- Transcribe: estado inicial, seleção de motor, arquivo/destino, progresso e conclusão;
- Library: carregamento, resumo, lista e menu recolhido;
- Settings: temas, densidade, idioma, tipografia, MFA, credenciais, armazenamento e telemetria;
- Administration > Users: lista, edição, papéis, exclusão lógica e permanente;
- Administration > Activity: histórico e filtros;
- Administration > Audit: registros e snapshots;
- Administration > Telemetry;
- Administration > Support: fila, detalhe e status;
- Administration > Data Studio: catálogo, Visual Builder, Data, Indexes, SQL Editor, ER Diagram e Saved Queries.

## 4. Convenção de IDs

Use os prefixos existentes:

- `ADM-AUTH-*` — autenticação administrativa;
- `TR-*` — transcrição;
- `LIB-*` — biblioteca;
- `SET-*` — configurações;
- `USR-*` — utilizadores administrativos;
- `ACT-*` — atividade;
- `AUD-*` — auditoria;
- `TEL-*` — telemetria;
- `SUP-*` — suporte;
- `DS-*` — Data Studio.

Para novos fluxos:

- `ONB-*` — onboarding e cadastro;
- `USER-AUTH-*` — login do utilizador;
- `PROFILE-*` — perfil;
- `USER-SUP-*` — suporte do lado do utilizador;
- `PRIV-*` — consentimento e privacidade;
- `RESP-*` — responsividade, textos longos, scroll e acessibilidade.

Não renumere os IDs já consolidados sem motivo forte.

## 5. Lacunas prioritárias de captura

### Novo utilizador

- criar conta por e-mail;
- cadastro/login com Google;
- consentimento Google;
- perfil pré-preenchido e editável;
- boas-vindas local-first;
- modal de telemetria;
- primeira transcrição;
- biblioteca vazia;
- pasta de armazenamento e backup sincronizado.

### Utilizador existente

- login sem papel administrativo;
- Transcribe, Library, Settings, Support e Profile;
- detalhe de uma transcrição;
- raw e clean;
- estados de copiar, salvar, excluir, erro e confirmação;
- tema claro e escuro;
- menu aberto e recolhido.

### Data Studio

- Structure;
- Relations;
- execução SQL com resultado;
- erro SQL;
- confirmação/revisão de operação mutável;
- Saved Query já salva e reaberta;
- parâmetros e histórico de execução;
- estados vazios.

### Fluxos transversais

- Profile e logout;
- textos longos e scroll;
- diferentes densidades;
- responsividade em janela estreita/ampla;
- loading, empty, success, error, blocked e destructive confirmation;
- telemetria recusada e revogada;
- segunda conta na mesma instalação herdando a escolha local de telemetria.

## 6. Ficha obrigatória para cada nova captura

Registrar:

- ID provisório;
- nome da tela;
- perfil aplicável;
- passo anterior e ponto de entrada;
- objetivo;
- ações disponíveis;
- dados apresentados;
- saída do fluxo;
- estados vazios, carregamento, sucesso, erro, confirmação ou bloqueio;
- regra de produto, privacidade ou segurança;
- evidência: captura, código ou documento;
- dados que precisam de anonimização;
- lacuna associada, se houver.

## 7. Regras de privacidade para as imagens

Antes de inserir em documento compartilhável ou Git, anonimizar:

- e-mails;
- nomes e usernames;
- fotos e avatares;
- caminhos locais;
- códigos, IDs e tokens de sessão;
- QR code/segredo MFA e códigos de recuperação;
- conteúdo real de tickets, transcrições e queries que contenham dados privados;
- qualquer dado pessoal ou corporativo.

Um código TOTP isolado e expirado pode ser evidência visual, mas deve ser removido quando não agregar valor funcional.

## 8. Regras de interpretação

- Não inventar telas, ações ou promessas.
- Não tratar documentos futuros como estado entregue.
- Código e estado real do repositório têm prioridade sobre conversa antiga.
- `PROJECT_CONTEXT.md` é a matriz consolidada.
- `FEATURE_VALIDATION_AND_ROADMAP.md` é a submatriz de validação e execução.
- `UX_PRODUCT_STANDARD.md` é obrigatório para qualquer avaliação de layout, frontend, acessibilidade ou experiência.
- O transcript raw é imutável; clean e conteúdos estruturados são derivados.
- UpexNote é local-first.
- Credenciais aparecem apenas como estado funcional, nunca como valor.

## 9. Processo de atualização do DOCX

1. Receber e catalogar novas capturas.
2. Anonimizar cópias locais.
3. Cruzar com código e MDs do domínio.
4. Atualizar o índice de figuras e a matriz de funcionalidades.
5. Remover da lista de lacunas somente o que foi efetivamente evidenciado.
6. Incrementar a versão do documento, por exemplo `v0.2`.
7. Preservar o histórico e evitar reescrever o estado já validado sem evidência nova.
8. Renderizar o DOCX e revisar visualmente todas as páginas antes de entregar.

### 9.1. Pipeline obrigatório de renderização e validação

A leitura do XML, a extração de texto ou a abertura parcial do arquivo não substituem a revisão visual. O DOCX atualizado só pode ser considerado validado depois deste fluxo completo:

1. converter o DOCX para PDF com LibreOffice em modo headless;
2. renderizar o PDF em uma imagem por página com Poppler ou ferramenta equivalente;
3. confirmar que todas as páginas esperadas foram geradas;
4. revisar visualmente todas as páginas, inclusive capturas, tabelas, diagramas, cabeçalhos, rodapés, quebras, cortes, sobreposições e páginas vazias inesperadas;
5. corrigir o documento e repetir todo o ciclo quando houver qualquer divergência.

Na máquina Windows de Leonardo, verificar primeiro estes caminhos já preparados:

```text
LibreOffice/soffice:
C:\Users\cunha\AppData\Local\Programs\LibreOfficeCodex\program\soffice.exe

Poppler (pdfinfo/pdftoppm):
C:\Users\cunha\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin
```

Se os comandos não forem encontrados, adicionar esses diretórios ao `PATH` do processo atual. Para o perfil temporário do LibreOffice no Windows, usar URI válida no formato `file:///C:/...`, preferencialmente gerada por `Path(...).resolve().as_uri()`, e não `file://C:\...`.

Em cloud ou em outra máquina, localizar as ferramentas equivalentes disponíveis. Se não houver um pipeline capaz de preservar e rasterizar páginas e imagens, declarar a limitação e não afirmar revisão visual completa nem leitura integral do documento.

## 10. Resultado esperado ao final da coleta

O documento final deve permitir que:

- uma pessoa entenda o UpexNote sem abrir o código;
- outra IA debata produto com contexto técnico e visual suficiente;
- estado entregue, backlog e possibilidade futura não sejam confundidos;
- a documentação possa ser versionada no GitHub privado sem exposição de dados pessoais ou corporativos.
