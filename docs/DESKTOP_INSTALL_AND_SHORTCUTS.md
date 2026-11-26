# UpexNote - instalacao e atalhos estaveis (26/11/2026)

## Regra de distribuicao

Na instalacao normal do Windows, o instalador Tauri/NSIS ja apresenta a escolha do diretorio de instalacao e, na tela final, a opcao de criar atalho na Area de Trabalho. O utilizador escolhe. O script de build nunca altera o atalho controlado pelo NSIS.

Apos o build de desenvolvimento, executar: powershell -NoProfile -ExecutionPolicy Bypass -File C:\Dev\upexnote\scripts\build_and_publish.ps1 -Edition both. Aceita tambem personal ou internal. O script historico build_and_publish_r031.ps1 permanece como wrapper compativel.

A sequencia e build -> validacao -> atualizacao de atalho. Se uma validacao falhar, o atalho nao deve ser publicado.

Atalhos de release portatil fixos:
- UpexNote Personal - Abrir.lnk
- UpexNote Internal - Abrir.lnk

O script utiliza a pasta Desktop efetiva, inclusive OneDrive, identifica versao e productName pelas configuracoes Tauri, verifica instalador, app e worker adjacente, e cria ou atualiza o MESMO atalho, sem duplicacoes por versao.

A primeira execucao limpa apenas atalhos gerados por scripts antigos (Teste, Multimodel e Instalar R03.1) quando os destinos conferem com a pasta do respectivo release. Os atalhos nativos do instalador NSIS (UpexNote e UpexNote Internal) nao sao modificados.

## Evidencias

1. Dois atalhos criados e destinos validados no Desktop real do Windows.
2. Quatro atalhos geridos anteriormente removidos com verificacao previa.
3. Segunda execucao do script retornou UPDATED para ambos, sem novos atalhos.
4. Simulacao em pasta temporaria com versoes 0.99.0 personal e internal identificou os instaladores corretos; executaveis reais nao foram modificados.
5. O installer.nsi gerado contem MUI_PAGE_DIRECTORY e MUI_FINISHPAGE_SHOWREADME_TEXT apontando para CreateOrUpdateDesktopShortcut.

Este hotfix nao exigiu recompilar o Tauri nem alterar databases. O ZIP R03.1 FULL anterior continua intacto, com snapshot anterior; consultar a main atual e o sidecar privado para as versoes mais recentes dos scripts.
