#!/usr/bin/env bash
# UpexNote: dump local diário + cópia off-site no Google Drive.
# Segredos permanecem no container do Postgres e no rclone.conf root-only.

set -Eeuo pipefail

readonly OUT_DIR="/root/backups/upexnote"
readonly REMOTE_DIR="upexnote-drive:Projects/upexflow/upexnote/storage/backups/postgres"
readonly TODAY="$(date -u +%F)"
readonly FINAL_PATH="${OUT_DIR}/upexnote-${TODAY}.sql.gz"
readonly TEMP_PATH="${FINAL_PATH}.partial"

cleanup() {
  rm -f -- "${TEMP_PATH}"
}
trap cleanup EXIT

mkdir -p -- "${OUT_DIR}"

container="$(docker ps --format '{{.Names}}' | grep '^upexnote_upexnote-db' | head -n 1)"
if [[ -z "${container}" ]]; then
  echo "upexnote-db container not found" >&2
  exit 1
fi

docker exec "${container}" pg_dump -U postgres upexnote | gzip -9 > "${TEMP_PATH}"
gzip -t -- "${TEMP_PATH}"
mv -f -- "${TEMP_PATH}" "${FINAL_PATH}"

rclone copyto \
  "${FINAL_PATH}" \
  "${REMOTE_DIR}/$(basename "${FINAL_PATH}")" \
  --checksum \
  --retries 3 \
  --low-level-retries 10

rclone check \
  "${OUT_DIR}" \
  "${REMOTE_DIR}" \
  --include "$(basename "${FINAL_PATH}")" \
  --one-way

# A retenção local continua em 14 dias. A cópia externa não é apagada
# automaticamente: qualquer política destrutiva no Drive exige decisão explícita.
find "${OUT_DIR}" -type f -name 'upexnote-*.sql.gz' -mtime +14 -delete

echo "$(date -u --iso-8601=seconds) backup local e off-site confirmado: $(basename "${FINAL_PATH}")"
