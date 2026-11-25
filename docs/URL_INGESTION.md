# UpexNote — Importação por URL do YouTube (implementação local em validação)

**Estado em 24/11/2026:** implementação candidata à **v0.45.0**. A promoção para produção exige validação do worker empacotado, instalador e publicação. O aplicativo anterior é v0.44.0.

## Experiência
- A tela **Transcrever** permanece com sua identidade, densidade, tipografia e campos existentes.
- Um bloco aditivo **Importar por URL** aceita vídeo, live e Shorts públicos ou não listados que estejam acessíveis.
- O usuário cola o endereço e seleciona **Analisar link**. A análise identifica título, duração, canal e trilhas de legenda, sem descarregar o áudio.
- **Com legendas:** duas alternativas explícitas: **Usar transcrição existente** (legenda do criador ou automática do YouTube, sem custo do motor de transcrição) ou **Gerar nova transcrição com UpexNote** (motor selecionado, potencialmente maior fidelidade e recursos disponíveis como diarização).
- **Sem legendas:** só é oferecida a opção de gerar nova transcrição.
- **Vídeo inacessível:** comunicar problema sem efetuar transcrição e oferecer nova URL.

## Contratos técnicos
- Worker `transcription/url_ingest.py`: normaliza e restringe URLs ao YouTube, usa `yt-dlp` em subprocesso sem shell e sem cookies/autenticação, extrai apenas áudio temporário ou legendas VTT.
- Comandos: `url-analyze`, `url-captions`, `url-transcribe`.
- Tauri: `url_analyze`, `url_captions`, `url_transcribe`; o último par emite os mesmos eventos `worker://event` e `worker://done` do pipeline existente.
- Legenda importada: VTT original e seus timestamps preservados intactos como RAW; CLEAN é apenas extração de texto visível, sem IA, deduplicação de fala, interpretação nem timestamps fabricados. Registro na Biblioteca SQLite do mesmo utilizador com `engine=youtube_captions`, URL de origem e custo de motor zero. A prévia estruturada/IA só acontece posteriormente mediante solicitação na Biblioteca.
- Novo áudio: descarregado no computador do usuário em diretório temporário, fornecido ao comando de transcrição existente; metadados da Biblioteca usam URL/título originais e o áudio temporário é excluído ao final.
- Transcrição por motor cloud só começa após ação explícita. A consulta inicial ao YouTube não envia arquivos para o servidor UpexFlow.
- Na v0.45.0, `yt-dlp.exe` é incluído no pacote do worker. A importação direta de legendas não depende de FFmpeg; a opção de extrair áudio para transcrever exige FFmpeg disponível no PATH do computador (instalação externa por enquanto). Validar em máquina limpa antes de anunciar distribuição autossuficiente.
- Não usar cookies, credenciais da sessão do browser, conversores externos, subprocesso com `shell=True`, nem efetuar bypass de vídeos privados/restritos.

## Validação e liberação
- Verificar as 3 localidades de interface PT/EN/ES, estados com/sem legenda, erros e telas responsivas.
- Testar URL pública/não listada autorizada, importação efetiva VTT, fluxo cloud com consentimento, RAW/CLEAN, Biblioteca/Caderno e limpeza de temporários.
- Executar testes Python, `npm run build`, `cargo check` e rebuild de sidecar **antes** de qualquer build Tauri definitivo. Confirmar que o worker empacotado aceita `url-analyze` e que `yt-dlp.exe` foi copiado e reconhecido.
- Proteger mudanças preexistentes em `Cargo.lock`.
- Só publicar e atualizar `docs.upexflow.com` quando a integração for aceita e houver autorização de deploy.
