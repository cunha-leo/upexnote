# UpexNote — dossiê de continuidade entre contas e agentes

> **Finalidade:** permitir que uma nova conta do ChatGPT/Codex continue o UpexNote com o máximo possível de contexto, método e sensibilidade de produto.
>
> **Segurança:** este documento não contém senhas, tokens, chaves, OAuth, conteúdo corporativo, áudio, vídeo ou transcrições privadas.
>
> **Estado do dossiê:** 4 de agosto de 2026.
>
> **Entrada obrigatória atual:** antes de usar este arquivo isoladamente, ler `docs/CONTEXT_ORCHESTRATION.md`. Ele coordena a camada pessoal e decisória no Google Drive, a matriz principal, a submatriz operacional e os documentos especializados.

## 1. Por que este documento existe

O trabalho começou numa conta pessoal que deixará de ser a conta principal. A continuidade será feita em outra conta pessoal dedicada a tecnologia e idiomas.

Não basta entregar o código. A nova conta precisa compreender:

- o que o UpexNote se tornou;
- quais decisões já foram tomadas;
- como o utilizador trabalha e valida;
- quais limites são absolutos;
- onde está a fonte de verdade;
- como evitar repetir funcionalidades existentes;
- como continuar sem perder a cadência e a qualidade construídas.

Este arquivo permanece como dossiê de handoff entre contas e agentes. A ordem completa de reconstrução do contexto passou a ser governada por `docs/CONTEXT_ORCHESTRATION.md`.

## 2. O criador e a intenção do produto

Leonardo é um profissional experiente de tecnologia, com vivência em grandes ambientes corporativos, integração, dados, sistemas e operação. O UpexNote nasceu de uma necessidade real: compreender e reutilizar melhor reuniões, aulas, vídeos e áudios, especialmente quando misturam PT-PT, PT-BR e inglês técnico.

O objetivo não é criar funcionalidades por moda. O produto resolve dores concretas:

- transcrever com qualidade;
- preservar a matéria-prima;
- organizar uma biblioteca permanente;
- transformar conteúdo em contexto, estudo e ações;
- permitir leitura, edição, pesquisa, reprodução e exportação;
- manter controle local e transparência sobre APIs, privacidade e custo.

O UpexNote pode continuar como ferramenta pessoal excelente e preservar a possibilidade de produto comercial. Possibilidades comerciais são hipóteses, não obrigação.

Para reconstruir com fidelidade como Leonardo pensa, trabalha e decide, consultar primeiro os documentos pessoais coordenados por `CONTEXT_ORCHESTRATION.md`, na ordem Dossiê e depois Contexto Vivo. Este resumo não substitui esses arquivos vivos. Em 08/08/2026, a versão canônica mais recente do Dossiê passou a ser a v1.3, cuja Adenda H registra capacidade, identidade profissional, direção, modelo de construção com IA, autoria e a arquitetura de prateleiras/Notebooks; a descoberta de versão do protocolo LIFE continua obrigatória.

## 3. Estado consolidado no momento da transição

- Repositório privado: `cunha-leo/upexnote`.
- Branch principal: `main`.
- Raiz local: `C:\Users\cunha\Projects\upexflow\upexnote`.
- Versão instalada/desenvolvida documentada: `v0.28.0`.
- Total observado em 28 de julho de 2026: 156 commits.
- Último commit anterior à primeira versão deste dossiê: `22165e2`.

### Capacidades entregues

- aplicativo desktop local-first com Tauri, React e TypeScript;
- worker local Python para mídia e transcrição;
- API central fina;
- login, Google OAuth, sessão, administração e MFA;
- transcrição por múltiplos motores;
- AssemblyAI Universal-3.5 Pro como motor principal para arquivos;
- Deepgram Nova-3 como alternativa e candidato a modo ao vivo;
- biblioteca, armazenamento e metadados;
- perfis, usuários, atividade, auditoria e telemetria consentida;
- suporte estruturado;
- Data Studio com:
  - exploração de schemas, tabelas, colunas e metadados;
  - Visual Builder;
  - SELECT e joins cruzados;
  - INSERT, UPDATE, DELETE, CREATE TABLE e ALTER TABLE protegidos;
  - SQL Editor PostgreSQL;
  - autocomplete de catálogo;
  - temas e formatação;
  - execução e resultado na mesma jornada;
  - Saved Queries;
  - parâmetros seguros e histórico;
  - diagramas ER por schema, tabela e SQL atual ou salvo.

O estado exato e os testes validados estão em `docs/PROJECT_CONTEXT.md`. Não confiar apenas neste resumo para editar.

As frentes ainda não entregues, seu estado, prioridade, critérios e fluxo de promoção estão em `docs/FEATURE_VALIDATION_AND_ROADMAP.md`.

## 4. Arquitetura principal

```text
apps/desktop
  Tauri + React + TypeScript
        │
        ├── worker local Python
        │     mídia, transcrição, credenciais e operações locais
        │
        └── API central fina
              autenticação, administração, telemetria consentida,
              suporte e operações controladas

PostgreSQL central
  schemas separados por domínio e em inglês

VPS / EasyPanel
  serviços centrais e infraestrutura
```

Princípio arquitetural: a interface pode ser moderna e conectada, mas o material bruto permanece sob controle local. Integrações externas são explícitas e delimitadas.

Desde 08/08/2026, a direção arquitetural organiza o produto como monólito modular por prateleiras/bounded contexts. `documents` possui transformação e prévia estruturada; o futuro `notebooks` possuirá hierarquia e conhecimento pessoal editável. A autoridade é `docs/NOTEBOOK_ARCHITECTURE.md`. Leonardo Cunha é o arquiteto principal, construtor sistêmico e responsável intelectual pelo produto. Ele possui capacidade demonstrada para conceber e construir software de ponta a ponta; não escolher `Developer` como rótulo profissional principal é posicionamento, não incapacidade. IAs ampliam pesquisa, produção, formalização, implementação e validação sob sua governança e não devem atribuir a si a autoria da arquitetura nem reduzi-lo a solicitante ou fonte de feedback.

## 5. Fonte de verdade e sequência de retomada

A porta de entrada é `docs/CONTEXT_ORCHESTRATION.md`.

A sequência mínima coordenada por ele é:

1. Dossiê pessoal no Google Drive;
2. Contexto Vivo no Google Drive;
3. `AGENTS.md` aplicável;
4. `docs/PROJECT_CONTEXT.md`;
5. `docs/FEATURE_VALIDATION_AND_ROADMAP.md`;
6. documentos especializados exigidos pela tarefa — `docs/NOTEBOOK_ARCHITECTURE.md` é obrigatório para Prévia/Caderno;
7. código, Git e comportamento executável;
8. este dossiê quando houver troca de conta, agente ou ambiente;
9. chats exportados apenas como material histórico complementar.

Para determinar o que realmente existe, prevalecem comportamento validado, código e Git. Para estado consolidado e decisões vigentes, prevalece `PROJECT_CONTEXT.md`. Para prioridade e trabalho ainda não consolidado, prevalece `FEATURE_VALIDATION_AND_ROADMAP.md`. Uma conversa antiga pode estar desatualizada.

## 6. Regras permanentes

### Privacidade e segurança

- nunca revelar ou registrar credenciais;
- nunca copiar áudio, vídeo ou transcrição privada para Git, logs ou chats;
- não copiar os documentos pessoais integrais do Drive para o repositório;
- credenciais ficam no Windows Credential Manager;
- nenhum material bruto sai da máquina sem ação e consentimento explícitos;
- telemetria não contém conteúdo;
- auditoria não revela secrets, tokens, hashes ou payloads privados;
- mudanças destrutivas exigem alvo preciso, preview e confirmação;
- novos domínios usam schema PostgreSQL separado e em inglês.

### Dados e conteúdo

- o transcript bruto é imutável;
- `raw`, `clean`, formatação, resumo e estudo são camadas distintas;
- arquivos locais continuam sendo artefatos primários;
- respostas de IA são derivadas e identificadas;
- fornecedores de IA precisam ser abstraídos, testados e reversíveis.

### UX

- UI/UX é requisito de arquitetura;
- `docs/UX_PRODUCT_STANDARD.md` é consulta obrigatória para qualquer impacto de layout, front-end, fluxo, interação, acessibilidade ou estado visual;
- administração usa menu lateral hierárquico;
- uma tela deve deixar claro onde o utilizador está, o que deve fazer, o resultado da ação e como voltar;
- layout precisa ser fluido e proporcional;
- testar menu aberto e recolhido;
- evitar overflow, sobreposição, margens quebradas e scroll usado para esconder layout mal dimensionado;
- hover, foco, seleção, vazio, loading, erro e sucesso precisam ser coerentes;
- o produto deve ser intuitivo sem esconder poder avançado.

## 7. Como Leonardo trabalha

### Estilo de colaboração

- fala de forma natural, exploratória e direta;
- ideias podem surgir durante a validação e ganhar forma por conversa;
- essa forma conversacional não torna a concepção casual: Leonardo está arquitetando, separando responsabilidades, testando coerência e refinando o sistema enquanto fala;
- não interpretar uso extensivo de IA nem rejeição do rótulo profissional `Developer` como ausência de entendimento técnico ou incapacidade de construir aplicações;
- espera que o agente investigue o repositório antes de responder;
- não gosta de receber propostas de coisas que já existem;
- prefere autonomia e continuidade a interrupções constantes;
- quando autoriza uma tarefa, espera execução até o final, com build/deploy quando isso fizer parte do pedido;
- feedback visual é concreto e deve ser levado literalmente;
- se disser que algo está confuso, carregado, pequeno, estourando ou sobreposto, inspecionar no tamanho real e corrigir a causa;
- não confundir concordância com evidência: verificar código, estado e comportamento.

O Dossiê pessoal no Drive é a fonte mais completa para o método de colaboração e deve ser relido quando houver nova sessão, ferramenta, conta ou possível atualização.

### Cadência de desenvolvimento

```text
necessidade real
  → orquestração de contexto
  → inspeção do que já existe
  → definição da jornada
  → implementação pequena e completa
  → validação técnica
  → build/instalação quando aplicável
  → validação visual e funcional real
  → correções
  → atualização do documento especializado
  → retroalimentação do roadmap
  → promoção ao contexto consolidado
  → commit e push
```

Versão visual sem funcionalidade real não é considerada conclusão.

### Comunicação desejada

- liderar pelo resultado;
- linguagem clara, humana e objetiva;
- explicar trade-offs sem jargão desnecessário;
- atualizações curtas durante trabalho longo;
- não esconder limitações;
- não prometer capacidades inexistentes;
- quando houver erro do agente, reconhecer e voltar ao pedido concreto.

## 8. Decisões de produto que não devem ser esquecidas

- local-first é diferenciação central, não detalhe;
- privacidade e controle pertencem ao utilizador;
- o produto precisa servir trabalho, reuniões, ensino e estudo;
- biblioteca permanente importa mais que respostas descartáveis;
- a frente aprovada atual transforma transcript clean em documento estruturado e workspace rico de estudo;
- comentários ancorados, referências de estudo, dicionário/glossário, persistência e exportação fazem parte dessa frente para refinamento;
- haverá reprodução do áudio original e leitura sintetizada em fases posteriores;
- leitura deverá ter velocidades até `2×`, escolha de voz/idioma e navegação pelo texto;
- timestamps por palavra permitirão sincronização, destaque e salto no áudio;
- Action Items, tópicos e inteligência de conteúdo serão avaliados sob solicitação;
- captura ao vivo e agentes são fases futuras;
- Data Studio nasceu no UpexNote como laboratório, mas pode tornar-se produto UpexFlow separado;
- webhooks, scheduler, jobs, eventos e integrações vêm depois de contratos claros;
- não criar várias frentes simultâneas sem necessidade real.

O estado preciso dessas frentes está em `FEATURE_VALIDATION_AND_ROADMAP.md`; este dossiê não deve duplicar o roadmap operacional.

## 9. “Abrir o ambiente”

Quando Leonardo pedir “abra o ambiente”, ele está falando do navegador do Codex.

Abrir ou reutilizar uma aba no navegador interno do Codex para cada destino habitual:

- Google Cloud/API do projeto UpexNote: `https://console.cloud.google.com/apis/credentials?project=upexnote&pli=1`;
- GitHub: `https://github.com/cunha-leo`;
- EasyPanel/VPS: `https://vps.upexflow.com/`;
- Hostinger hPanel: `https://hpanel.hostinger.com/`;
- webmail da conta `contact@upexflow.com`, usando a sessão autenticada disponível.

Reutilizar abas e sessões existentes quando possível, evitar duplicatas e deixar os destinos abertos para Leonardo acompanhar. Se algum serviço pedir autenticação, deixar a página visível para ele concluir o acesso e continuar abrindo os outros destinos.

Não criar documento separado de “sites do projeto” para isso e não confundir navegador com ambiente de código. Sessões, cookies, credenciais, senhas e tokens não devem ser copiados, expostos nem registrados.

## 10. Migração oficial entre contas ChatGPT

O ChatGPT não oferece fusão completa de contas nem restaura automaticamente os chats antigos como conversas separadas na nova barra lateral.

O procedimento oficial é:

1. na conta antiga, abrir perfil → **Settings** → **Data controls**;
2. em **Export data**, escolher **Export** e confirmar;
3. baixar o ZIP quando o e-mail chegar; o link expira;
4. extrair o ZIP;
5. localizar `conversations.json` ou arquivos numerados;
6. na conta nova, criar uma conversa de referência;
7. enviar o JSON ou partes menores;
8. usar o arquivo como histórico consultável, não como substituto do contexto durável do repositório.

A exportação pode levar até sete dias para chegar. O link de download expira 24 horas depois do recebimento.

Limitações importantes:

- a barra lateral antiga não será reconstruída;
- chats não reaparecem como conversas separadas;
- assinatura, configurações, memórias, GPTs e arquivos não são transferidos automaticamente;
- instruções personalizadas precisam ser recriadas;
- projetos e conexões devem ser conferidos na nova conta;
- não cancelar a conta antiga antes de baixar e validar a exportação.

## 11. Estratégia recomendada para UpexNote

### Camada 1 — orquestração de contexto

- `CONTEXT_ORCHESTRATION.md` é a porta única;
- ele coordena Dossiê, Contexto Vivo, matriz, submatriz, documentos de domínio e retorno documental;
- `NEW_ACCOUNT_BOOTSTRAP_PROMPT.md` fornece o prompt mínimo para iniciar a leitura.

### Camada 2 — repositório

O GitHub é a continuidade operacional. A nova conta deve:

- conectar o GitHub correto;
- clonar ou abrir o mesmo repositório;
- trabalhar na mesma raiz local quando apropriado;
- ler `AGENTS.md` e a documentação obrigatória;
- conferir `git status` e histórico antes de agir.

### Camada 3 — histórico exportado

Enviar o export oficial apenas como arquivo de referência. Para reduzir ruído e exposição, priorizar as conversas `UpexNoteV1` e `UpexNoteV2`, ou recortes delas, em vez de misturar projetos profissionais e pessoais não relacionados.

## 12. Checklist antes de abandonar a conta antiga

- [ ] Solicitar e baixar a exportação oficial.
- [ ] Confirmar que `conversations.json` contém UpexNoteV1 e UpexNoteV2.
- [ ] Guardar o ZIP em local pessoal seguro, fora do Git.
- [ ] Não colocar a exportação completa no repositório UpexNote.
- [ ] Conectar GitHub, Gmail/Drive e demais integrações necessárias na conta nova.
- [ ] Recriar instruções personalizadas e preferências relevantes.
- [ ] Abrir o repositório na nova conta.
- [ ] Colar o prompt de bootstrap.
- [ ] Pedir ao novo Codex que leia `CONTEXT_ORCHESTRATION.md` e siga suas coordenadas antes de alterar.
- [ ] Fazer uma tarefa pequena de verificação.
- [ ] Manter a conta antiga acessível até confirmar a continuidade.
- [ ] Revisar assinaturas para evitar cobrança duplicada.

## 13. Critério de sucesso da transição

A nova conta está pronta quando o novo Codex consegue, sem inventar:

- declarar se conseguiu acessar e atualizar-se pelo Dossiê e Contexto Vivo;
- explicar como Leonardo trabalha e valida;
- identificar a versão e o último commit;
- explicar a arquitetura local-first;
- listar as regras de privacidade, banco e UX;
- distinguir entregue, frente aprovada, backlog e visão futura;
- localizar os documentos corretos;
- executar uma pequena tarefa preservando o worktree;
- atualizar documento especializado, roadmap e contexto consolidado na ordem correta.

## 14. Referências oficiais da migração

- OpenAI Help Center — [Transferir conversas exportadas entre contas do ChatGPT](https://help.openai.com/pt-br/articles/9106926-transferindo-conversas-de-1-conta-do-chatgpt-para-outra-conta-do-chatgpt)
- OpenAI Help Center — [Exporting your ChatGPT history and data](https://help.openai.com/en/articles/7260999-how-do-i-export-my-chatgpt-history-and-data)
