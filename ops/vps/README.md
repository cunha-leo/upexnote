# Operação da VPS

Artefactos versionados dos mecanismos instalados diretamente na VPS do UpexNote.
Nenhum ficheiro deste diretório contém credenciais.

## Backup do Postgres

`upexnote-backup.sh` cria um dump comprimido e validado, envia-o ao Google
Drive por `rclone` e compara o checksum antes de aplicar a retenção local de
14 dias. Não existe eliminação automática no destino externo.

Instalação na VPS:

```text
/usr/local/sbin/upexnote-backup.sh
/etc/cron.d/upexnote-backup  (03:30 UTC)
/root/.config/rclone/rclone.conf  (modo 600; nunca versionado)
```

## Consultar e aprender com os jobs

Os jobs da VPS são tarefas Unix reais: neste caso, `cron` chama um script Bash.
Eles não dependem da aplicação desktop nem do computador do utilizador estar
ligado. Aceder à VPS por SSH permite inspecionar o agendamento, procurar
eventos e confirmar o resultado das execuções.

Comandos de consulta (não alteram dados):

```bash
# Agendamento e código ativo
cat /etc/cron.d/upexnote-backup
sed -n '1,220p' /usr/local/sbin/upexnote-backup.sh

# Backups criados: data, tamanho e o mais recente
ls -lh /root/backups/upexnote/
ls -lt /root/backups/upexnote/ | head

# Eventos do cron e pesquisa por qualquer termo útil
journalctl -u cron --since "7 days ago" | grep -i upexnote
journalctl -u cron --since "30 days ago" | grep -iE 'upexnote|rclone|error|fail'

# Verificação local de sintaxe, sem executar o backup
bash -n /usr/local/sbin/upexnote-backup.sh
```

Para executar manualmente há `sudo /usr/local/sbin/upexnote-backup.sh`; este
último comando **cria um dump e envia-o ao Drive**, portanto só deve ser usado
quando se pretende mesmo uma execução extra.

Futuros jobs podem seguir a mesma abordagem — script versionado em `ops/vps/`,
instalado explicitamente na VPS e agendado por `cron` ou `systemd timer`. Cada
um pode ganhar um identificador por execução, logs próprios, índices por data
ou verificações específicas. Isso é independente de n8n; n8n pode ser usado
mais tarde quando fizer sentido para orquestração visual e integrações.

## Firewall após restart do Docker

`docker.service.d/upexnote-firewall.conf` é instalado como drop-in de
`docker.service`. Após cada start/restart, o systemd agenda novamente o serviço
existente `upexnote-firewall.service`, que recompõe as regras `DOCKER-USER`.

O hook usa `--no-block`: uma eventual falha do script de firewall fica visível
no estado/journal de `upexnote-firewall.service`, mas não derruba o Docker.
