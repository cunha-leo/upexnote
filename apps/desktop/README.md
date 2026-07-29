# UpexNote Desktop

Aplicação Windows local-first do UpexNote. A versão atual é **0.28.0**.

## Stack

- Tauri 2 como shell desktop;
- React 19 + TypeScript + Vite na interface;
- comandos Rust assíncronos como corredor entre a UI e o worker;
- worker Python empacotado como sidecar;
- comunicação por JSON/NDJSON e eventos, sem servidor HTTP local.

## Superfícies entregues

- Transcrever;
- Biblioteca;
- Suporte;
- Definições e Segurança;
- perfil e sessão;
- Administração hierárquica: Users, Activity, Audit, Telemetry, Support e Data Studio;
- Data Studio: Visual Builder, SQL Editor, Saved Queries e ER Diagram.

A aplicação inclui temas, densidade, tipografia, zoom, titlebar própria, navegação por teclado e interface em PT/EN/ES. As preferências ficam locais.

## Limites de segurança

O frontend não processa mídia nem acessa credenciais diretamente. Ele envia operações permitidas aos comandos Tauri; o worker lê as credenciais no Windows Credential Manager e só envia áudio a um fornecedor quando o utilizador escolhe explicitamente um motor cloud.

O transcript `raw` não é editado. A edição da Biblioteca atua somente sobre o conteúdo `clean` e mantém histórico.

Operações administrativas e Data Studio exigem sessão MFA válida, revalidação do papel administrativo e whitelists no corredor Tauri/worker.

## Desenvolvimento

```powershell
npm install
npm run build
npm run tauri build
```

O bundle final depende do worker previamente empacotado por `services/worker/build_worker.ps1`. Versões de produção não incluem devtools.

Antes de alterações visuais, seguir [`docs/UX_PRODUCT_STANDARD.md`](../../docs/UX_PRODUCT_STANDARD.md) e validar janela real, menu aberto/recolhido, overflow, foco, hover, estados vazios, textos longos e todos os temas relevantes.
