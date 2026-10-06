# Prompt de retomada: publicação LinkedIn "UpexNote Parte 1", vídeos e anonimização (05/10/2026)

> Este documento atualiza qualquer IA que assumir o trabalho depois da sessão de 05/10/2026. Ele explica o que foi feito, por que foi feito, onde estão os arquivos e o que ler antes de agir. Não contém valores reais de infraestrutura: use sempre os marcadores e a tabela local descrita na seção 3.
>
> Regra de estilo que vale para tudo que for escrito para Leonardo ou em nome dele: **não usar travessão (o traço longo ou o médio) em textos de publicação, comentários, README ou mensagens**. Ele considera o travessão um sinal de texto de IA. Prefira dois pontos, vírgula, ponto ou parênteses.

---

## 1. Resumo em 30 segundos

- Em 05/10/2026 Leonardo publicou no LinkedIn o post **"UpexNote | Parte 1: Da minha dor à construção de uma solução"**, com o vídeo do módulo do usuário (v4) e, no primeiro comentário, o link do repositório e o infográfico.
- O repositório público `cunha-leo/upexnote` ganhou dois vídeos de demonstração no README (usuário e administrador, este de acesso restrito), hospedados no próprio GitHub.
- Todos os identificadores reais de infraestrutura e pessoais foram trocados por marcadores no repositório. A tabela de equivalência real ficou **só no computador dele**, em arquivo ignorado pelo Git.
- Existe uma série planejada: a Parte 1 está publicada; as próximas partes aprofundam cada camada.

## 2. Por que isso existe (objetivo)

O post e os vídeos são **evidência pública** do posicionamento profissional de Leonardo: Business Analyst / Analista Funcional-Técnico / Analista de Sistemas que concebe, estrutura e governa soluções de ponta a ponta orquestrando IAs, com UX/UI, dados, segurança e operação. Não adotar "desenvolvedor" como identidade principal é uma decisão de carreira, não uma limitação técnica (ver Dossiê LIFE, Adenda H, citada no `AGENTS.md`).

O uso prático é currículo e LinkedIn voltados ao mercado brasileiro. Por isso o texto do post fala em "analista de negócio e sistemas, conduzi a concepção e a arquitetura, orquestrando a construção com IAs".

## 3. Documento de infraestrutura local (o que é, por quê, como usar)

**O quê.** O repositório é público. Para isso, todos os valores reais foram substituídos por marcadores:

`<VPS_HOST>`, `<DB_PORT>`, `<SSH_USER>`, `<CHAVE_SSH_VPS>`, `<USER>`, `<LINK_DRIVE_PRIVADO>`, `<ID_DRIVE_PRIVADO>`, `<URL_PAINEL_EASYPANEL>`, `<usuario_admin_1>`, `<usuario_admin_2>`.

**Onde estão os valores reais.** No arquivo `docs/private/INFRA_LOCAL.md` do clone local de Leonardo (`C:\Users\<USER>\Projects\upexflow\upexnote\docs\private\INFRA_LOCAL.md`). Ele está no `.gitignore` (`docs/private/`) e **nunca deve ser commitado, copiado para chat, README, issue ou comentário**.

**Por quê.** Evitar expor servidor, portas, usuário SSH, nome de chave, caminhos locais e links privados do Drive em um repositório público, sem fazer a IA perder o caminho: quando uma IA trabalha no projeto, ela lê o marcador e consulta a tabela local para saber o valor.

**Como usar (obrigatório).**
1. Antes de operar SSH, banco, caminhos locais ou links do Drive, leia `docs/private/INFRA_LOCAL.md`.
2. Se o arquivo não existir (por exemplo, ambiente em nuvem), **pare e peça a Leonardo**. Não invente valores e não tente deduzi-los de commits antigos.
3. Nunca escreva o valor real em arquivo versionado. Use sempre o marcador.

**Limite conhecido.** O histórico do Git ainda contém os valores antigos, de antes da anonimização. Leonardo decidiu **não reescrever o histórico**. Portanto: não reabra o assunto sem pedido explícito, e trate o histórico como potencialmente sensível (não cite valores antigos em lugar nenhum).

Arquivos anonimizados no commit `c2ad255` e seguintes: `AGENTS.md`, `UpexNote_CONTINUIDADE_DOCUMENTACAO_VISUAL.md`, `docs/ACCOUNT_CONTINUITY_HANDOFF.md`, `docs/CONTEXT_ORCHESTRATION.md`, `docs/HANDOFF_CLAUDE_2026-08-09_UPEXNOTE_V030.md`, `docs/PROJECT_CONTEXT.md` (com nota de anonimização no topo) e `docs/handoff/PROMPT_RETOMADA_*.md`.

## 4. Vídeos: o que existe, onde está e qual é o oficial

| Item | Situação | Onde |
|---|---|---|
| Vídeo do usuário **v4** (1 min 36 s) | **Oficial.** É o que está no LinkedIn e no README | GitHub (README, seção "Demonstração do usuário") e pasta local de mídia |
| Vídeo do administrador v3 (1 min 32 s) | **Oficial.** README, seção "Demonstração administrativa · acesso restrito" | GitHub (README) e pasta local de mídia |
| Infográfico `UpexNote_Premium_v5.png` | **Oficial.** Anexo do primeiro comentário e encerramento do vídeo | Pasta local de mídia |
| Vídeo do usuário v3 | **Superado.** Mostrava, por alguns segundos, o item de nuvem corporativa na janela de abrir arquivo | Não usar |

**Pasta local de mídia (computador de Leonardo):** `C:\Users\<USER>\OneDrive\Desktop\upexnote Midia`. Contém `upexnote-parte1-v4-User.mp4`, `upexnote-parte1-admin-v3-rascunho.mp4` e `UpexNote_Premium_v5.png`.

**Como o README exibe os vídeos.** Só links do tipo `https://github.com/user-attachments/assets/<id>` colados sozinhos em uma linha renderizam o player. A tag `<video>` com link `raw` não funcionou. Para trocar um vídeo: editar o `README.md` pelo editor web do GitHub, arrastar o `.mp4` para dentro do texto (o GitHub gera o link novo), apagar a linha do link antigo e commitar. A IA não consegue fazer esse upload; é um passo manual de Leonardo. Os arquivos `.mp4` **não ficam no repositório** (commit `bf957ce`); `docs/media/` guarda só as duas imagens de exemplo de transcrição.

**Como foram produzidos.** Gravações brutas feitas por Leonardo, editadas com `ffmpeg` (H.264, 1920x1080, 30 fps, crf 18): cartões de abertura e pausa, legendas pontuais renderizadas como imagem, trechos de espera acelerados com selo "3x" ou "1,5x", trilha contínua com fade, borrões com `boxblur` onde havia dado pessoal, e infográfico no encerramento. Os scripts de montagem ficaram na sessão em nuvem (diretório temporário) e **podem não existir mais**. Se for preciso refazer, peça a Leonardo as gravações originais e reconstrua o processo acima.

**Regra de privacidade das gravações.** Antes de qualquer nova versão, revisar quadro a quadro as janelas de abrir e salvar arquivo (o painel lateral do Windows mostra contas de nuvem) e telas com e-mail ou código MFA. Código MFA é aleatório e pode aparecer. O e-mail pessoal de contato dele é público (currículo e repositório), pode aparecer. O que deve ser borrado: contas de nuvem corporativas e qualquer arquivo ou pasta de empresa. Um primeiro nome de professor numa transcrição de aula foi avaliado e **deixado como está**, por não identificar ninguém nem expor conteúdo sensível.

## 5. A publicação no LinkedIn

**Estado.** Publicada em 05/10/2026, uma única vez (a primeira versão foi apagada por Leonardo para trocar o vídeo pela v4 borrada). Não há duplicata nem rascunho pendente. O título do post foi aprovado e fica como está: `UpexNote | Parte 1: Da minha dor à construção de uma solução`.

**Estrutura do texto (já aprovado, não reescrever sem pedido).**
1. Título.
2. A origem: necessidade em reuniões, calls, aulas e estudos, especialmente em mais de um idioma.
3. A rotina e a pergunta (recapitular, anotar, resumir, fluxograma).
4. O nascimento do UpexNote (preservar o original e gerar material organizado, editável e reutilizável).
5. Frase de posicionamento: "Como analista de negócio e sistemas, conduzi a concepção e a arquitetura da solução, orquestrando sua construção com IAs e integrando UX/UI e governança."
6. Sete decisões em lista com "•": Negócio e requisitos; Arquitetura e dados; UX/UI; Integração de IAs; Privacidade; Segurança; Operação.
7. Condução das IAs (engenharia de prompts e contexto, memória documental).
8. Evolução por entregas incrementais.
9. Estado atual e como o projeto reflete a forma de trabalhar dele.
10. Sobre o vídeo, o infográfico e a demo administrativa no GitHub.
11. Aviso de que o link e o infográfico estão no primeiro comentário.
12. Fechamento da série (as próximas partes aprofundam cada camada).
13. Hashtags: `#BusinessAnalysis #InteligenciaArtificial #UXDesign #UpexNote`.

**Por que o link fica no primeiro comentário.** Link no corpo do post reduz o alcance no LinkedIn. O comentário leva o repositório e o infográfico.

**Primeiro comentário (publicado).** "Repositório com código, documentação e demonstrações (usuário e administrador):" + `https://github.com/cunha-leo/upexnote` + "O infográfico resume a jornada e as decisões de construção. Nas próximas partes, aprofundo cada camada." + imagem `UpexNote_Premium_v5.png` anexada.

**Limites do LinkedIn a respeitar.** 3.000 caracteres por post (o texto atual tem cerca de 2.950). O vídeo é reproduzido sem som por padrão; por isso o conteúdo depende de legendas visuais, não de narração. Sem legenda automática (não há fala). Miniatura automática (primeiro quadro, que já é o cartão de título).

## 6. Como operar o LinkedIn pelo navegador do app (lições aprendidas)

- O navegador embutido do app funciona com o LinkedIn já autenticado; o acesso foi liberado por site.
- **Não digite textos longos com a ação de digitar:** o editor atrasa e embaralha caracteres (apareceram letras trocadas e sobras). O que funcionou: inserir o texto por script no campo do editor (`ProseMirror`), parágrafo a parágrafo, com `insertText` e `insertParagraph`, e depois **ler de volta o conteúdo do campo** para conferir contagem de caracteres, travessões e parágrafos.
- Em caixas de comentário curtas, digitar em blocos pequenos com espera entre eles e quebras de linha com Shift+Enter funciona, conferindo sempre depois.
- **O seletor de arquivos do Windows não é controlável pela IA.** Anexar vídeo e imagem é sempre um passo de Leonardo: ele clica em Mídia ou no ícone de imagem do comentário e escolhe o arquivo.
- Cliques por coordenada falham quando a janela é redimensionada; prefira referências de elemento.
- Verificação de vídeo dentro do post: dá para ler o quadro direto do elemento de vídeo (desenhar em canvas) e medir se a região esperada está borrada.

## 7. Regras de segurança desta frente (valem sempre)

1. **Nada é publicado, enviado ou apagado sem o "sim" explícito de Leonardo naquele momento.** Aprovação de texto não é aprovação de publicar. Mostrar o editor preenchido, conferir e perguntar antes de clicar em Publicar ou Comentar.
2. Não expor segredos, tokens, senhas, chaves, cookies, valores reais de infraestrutura, e-mails que não sejam os já públicos, nem conteúdo privado de gravações.
3. Não executar deploy, push ou operação destrutiva sem autorização específica. Nunca usar `git add -A`; listar arquivos.
4. Não reabrir decisões já tomadas sem fato novo: sem thumbnail personalizada, sem reescrita do histórico do Git, sem trocar o título aprovado, sem legendas automáticas.
5. Atribuição em commits feitos por IA segue a instrução do ambiente (linha `Co-Authored-By` e link da sessão).

## 8. O que ler antes de agir (ordem)

1. `AGENTS.md` da raiz do repositório (Parte 1: protocolo LIFE com Dossiê, Contexto Vivo e Fio Condutor na pasta canônica do Drive; Parte 2: regras do repositório).
2. `docs/CONTEXT_ORCHESTRATION.md`, `docs/PROJECT_CONTEXT.md`, `docs/FEATURE_VALIDATION_AND_ROADMAP.md`, `docs/UX_PRODUCT_STANDARD.md` e `README.md`.
3. `docs/private/INFRA_LOCAL.md` (apenas se a tarefa tocar em infraestrutura; só existe no computador de Leonardo).
4. Este documento.
5. Para a Parte 2 da série: `docs/NOTEBOOK_ARCHITECTURE.md`, `docs/ARCHITECTURE.md`, `docs/AI_MEDIA_EVOLUTION.md` conforme a camada escolhida.

Se a tarefa for só ajustar texto de publicação, os itens 1 e 2 bastam em modo de leitura focada; se for tocar em código, em vídeo com dado pessoal ou em infraestrutura, leia tudo.

## 9. Pendências e próximos passos

- **Destaques do LinkedIn.** Ideia aprovada para depois: destacar o post da Parte 1 (primeiro item) e, opcionalmente, o link do repositório como segundo. Esperar cerca de 2 a 3 dias para o post acumular reações. Em post, não há título separado a editar (o título é a primeira linha); em link, conferir o título que o LinkedIn sugerir.
- **Parte 2 da série.** Ainda não escrita. Mesmo roteiro: rascunho do texto com a IA, aprovação de Leonardo, conferência no editor, publicação só com o "sim" dele, comentário com link.
- **Documentação.** Se a próxima etapa tocar em algo do produto, atualizar `docs/PROJECT_CONTEXT.md` (Registro e Estado atual) e `docs/FEATURE_VALIDATION_AND_ROADMAP.md`. Documentação desatualizada é entrega incompleta.
- **Ajustes menores já sinalizados e não resolvidos:** conferir no currículo se o nome do arquivo e o cabeçalho têm a mesma versão, e se o e-mail do currículo é o mesmo usado no repositório.

## 10. Prompt para colar na abertura do novo chat

```text
Você está continuando um trabalho anterior com Leonardo Cunha sobre a publicação "UpexNote | Parte 1" no LinkedIn, os vídeos de demonstração no GitHub e a anonimização do repositório público cunha-leo/upexnote.

Antes de agir:
1. Leia INTEIRO, do início ao fim, o arquivo docs/handoff/PROMPT_RETOMADA_LINKEDIN_PARTE1_2026-10-05.md do repositório. Ele diz o que já foi feito, o que é oficial e o que está superado.
2. Leia o AGENTS.md da raiz e execute o protocolo LIFE nele descrito (Dossiê, Contexto Vivo e Fio Condutor, na pasta canônica do Drive), sem pular nenhuma parte.
3. Se a tarefa tocar em SSH, banco, caminhos locais ou links do Drive, leia docs/private/INFRA_LOCAL.md no computador de Leonardo. Se o arquivo não existir, peça a ele. Nunca invente valores e nunca escreva valores reais em arquivo versionado.

Regras fixas: não publicar, enviar, apagar, fazer push ou deploy sem o "sim" explícito dele no momento; não usar travessão (traço longo ou médio) em nenhum texto; manter o título e o texto já aprovados do post; vídeo oficial do usuário é a v4; o v3 está superado; revisar qualquer vídeo novo quadro a quadro em busca de dado pessoal antes de sugerir publicação.

Tarefa de hoje: <descrever aqui>
```
