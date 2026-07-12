# Arquitetura inicial

## Modelo: local-first, interface web moderna

O UpexNote terá interface de painel moderna, com temas claro e escuro, mas executará o trabalho sensível no computador do utilizador.

```text
Interface React/Tauri
        |
Worker local (Python)
        |-- seleção e leitura de arquivos locais
        |-- extração temporária de áudio
        |-- transcrição local ou chamada explícita a API cloud
        |-- futura captura WASAPI: microfone + loopback
        |
Storage local / Google Drive opcional
```

## Classificação de dados

| Dados | Destino padrão |
|---|---|
| Vídeo bruto | Local de origem. Nunca é copiado para o projeto. |
| Áudio temporário | Cache local, removido ao terminar. |
| Áudio enviado a motor cloud | Só quando o utilizador escolhe explicitamente AssemblyAI, OpenAI ou Deepgram. |
| Transcript, contexto e exportações | `storage/` no Google Drive, ignorado pelo Git. |
| Código e documentos técnicos | Git privado. |
| Credenciais | Windows Credential Manager. |

## Sincronização futura

O PostgreSQL na VPS será usado posteriormente para metadados e histórico entre dispositivos. A primeira versão não dependerá dele para abrir uma transcrição ou processar um ficheiro.
