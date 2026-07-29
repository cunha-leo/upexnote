# Arquitetura do UpexNote

> Estado alinhado à versão desktop `0.28.0`. O histórico detalhado, decisões e validações vivem em `PROJECT_CONTEXT.md`.

## Visão geral

O UpexNote é uma aplicação **local-first**: a experiência principal vive no desktop do utilizador, enquanto serviços centrais suportam identidade, administração, telemetria consentida e atendimento. O material bruto continua sob controlo da máquina do utilizador.

```text
Desktop UpexNote (Tauri + React + TypeScript)
        |
        | comandos Rust + eventos NDJSON
        v
Worker local Python (sidecar)
  ├─ seleção e leitura de ficheiros locais
  ├─ extração temporária de áudio e transcrição
  ├─ Windows Credential Manager
  ├─ SQLite local ou PostgreSQL por túnel SSH
  └─ futuros: captura WASAPI e fluxos de contexto/estudo

API central FastAPI (/v1, HTTPS)
  ├─ recuperação de senha e MFA administrativo
  ├─ telemetria anónima com opt-in
  ├─ tokens de instalação
  └─ suporte
        |
        v
PostgreSQL no EasyPanel
  ├─ dados de transcrição e identidade
  ├─ schema `support` isolado para atendimento
  └─ schema `data_studio` para consultas salvas e execuções
```

O Data Studio administrativo explora o catálogo e oferece um construtor visual PostgreSQL protegido, SQL Editor manual, Saved Queries parametrizadas e diagramas ER, conforme `DATA_STUDIO_ARCHITECTURE.md`. Valores são parametrizados; mutações exigem plano confirmado, transação e auditoria. Scheduler, jobs, eventos, entregas e integrações externas permanecem posteriores à v0.28.

## Aplicação desktop

- **UI:** React 19, TypeScript e Vite, empacotados em Tauri 2 para Windows.
- **Shell nativo:** Rust expõe comandos assíncronos para o worker, evita bloquear a janela e mantém o túnel SSH persistente quando aplicável.
- **Worker:** Python empacotado com PyInstaller como sidecar; comunica progresso e resultado por NDJSON, sem servidor HTTP local, portas ou CORS.
- **Persistência local:** cada instalação pode usar SQLite embutido; a instalação administrativa também pode usar PostgreSQL pela ligação protegida já configurada.
- **Identidade:** e-mail/senha, Google OAuth e GitHub Device Flow; administração exige elevação MFA por TOTP ou código por e-mail.

## Serviços centrais

`services/api` é uma API FastAPI publicada exclusivamente por HTTPS. O PostgreSQL não é exposto para clientes da aplicação; a API usa a rede interna do EasyPanel.

- Recuperação de senha usa códigos e tokens de uso único guardados somente como hash.
- MFA administrativo usa sessões opacas revogáveis; segredos TOTP são cifrados no servidor.
- Telemetria é opcional e aceita apenas identificador anónimo com hash, versão, motor, duração, custo estimado, região e código de erro. Transcripts, mídia, caminhos e credenciais são rejeitados pelo contrato.
- O suporte é um domínio próprio, isolado no schema PostgreSQL em inglês `support`.

## Dados e privacidade

| Dado | Regra de armazenamento |
|---|---|
| Vídeo bruto | Permanece no caminho local de origem; nunca é copiado automaticamente para GitHub, VPS ou Drive. |
| Áudio temporário | Cache local removível; só vai a um motor cloud após escolha explícita do utilizador. |
| Transcript raw | Artefacto de referência imutável. |
| Transcript clean e derivados | Identificados como derivados; guardados localmente primeiro. |
| Histórico remoto | Escrita best-effort no PostgreSQL; a falha da VPS não pode impedir a preservação local. |
| Credenciais | Windows Credential Manager no desktop; variáveis protegidas no EasyPanel para serviços. Nunca Git, logs ou chat. |
| Evidências de suporte | Metadados e hashes no banco; o contrato prevê binários em spool temporário e arquivo verificado no Google Drive autorizado. O volume persistente e o job final ainda são backlog operacional. |

## Banco e domínios

Novos domínios usam schemas PostgreSQL separados e nomeados em inglês. Não se misturam suporte, estudo, chat ou integrações no schema `public`.

O suporte segue hub-and-spoke: `support.tickets` é a matriz e satélites preservam descrição, comentários, anexos, status, atribuições, notificações e auditoria. Anexos não são BLOBs no banco.

## Operação

- Backups do PostgreSQL são gerados diariamente, validados e copiados ao Google Drive autorizado; a retenção automática é apenas local.
- O firewall da base é refeito após reinícios do Docker.
- Os scripts operacionais versionados ficam em `ops/vps/`; segredos e configurações reais ficam fora do Git.
- Para painéis externos autorizados, a operação usa exclusivamente o navegador interno do Codex já aberto pelo utilizador.

## Estado e próximos domínios

Entregues: transcrição, Biblioteca, identidade, MFA, administração, telemetria consentida, suporte e Data Studio até diagramas ER. As frentes imediatas registradas são concluir a infraestrutura de evidências, tornar a telemetria agregada mais acionável, evoluir Saved Queries para execução central e amadurecer a operação de suporte. Os próximos domínios de conteúdo são contexto/decisões/ações/riscos, estudo e chat ancorado no material. Integrações e webhooks só serão implementados após a definição de eventos e contratos reais.
