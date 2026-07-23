#!/usr/bin/env bash
# Archive UpexNote support evidence after rclone checksum verification.
#
# Required root-only environment file (/etc/upexnote-support.env):
#   UPEXNOTE_DB_CONTAINER=upexnote-db
#   UPEXNOTE_HOST_SPOOL_DIR=/opt/upexnote/support-spool
# Optional: UPEXNOTE_DRIVE_REMOTE=upexnote-drive:Projects/upexflow/upexnote/storage/support/tickets
#
# The API container writes to /data/support-spool through a host bind mount.
# This job sees the same files through UPEXNOTE_HOST_SPOOL_DIR. It NEVER reads
# rclone credentials from this repository and deletes a spool file only after
# `rclone copyto` + `rclone check` both succeed.
set -Eeuo pipefail
umask 077

readonly ENV_FILE="/etc/upexnote-support.env"
[[ -r "$ENV_FILE" ]] || { echo "support archive: missing $ENV_FILE" >&2; exit 2; }
# shellcheck disable=SC1090
source "$ENV_FILE"

: "${UPEXNOTE_DB_CONTAINER:?missing UPEXNOTE_DB_CONTAINER}"
: "${UPEXNOTE_HOST_SPOOL_DIR:?missing UPEXNOTE_HOST_SPOOL_DIR}"
readonly DRIVE_REMOTE="${UPEXNOTE_DRIVE_REMOTE:-upexnote-drive:Projects/upexflow/upexnote/storage/support/tickets}"
readonly API_SPOOL_PREFIX="/data/support-spool/"

psql_json() {
  docker exec "$UPEXNOTE_DB_CONTAINER" psql -U postgres -d upexnote -At -v ON_ERROR_STOP=1 -c "$1"
}

sql_quote() { printf "%s" "$1" | sed "s/'/''/g"; }

pending="$(psql_json "SELECT id || E'\\t' || ticket_id || E'\\t' || spool_path || E'\\t' || stored_filename FROM support.ticket_attachments WHERE archive_state IN ('pending','failed') AND spool_path IS NOT NULL ORDER BY id LIMIT 200;")"
[[ -n "$pending" ]] || exit 0

while IFS=$'\t' read -r attachment_id ticket_id spool_path stored_filename; do
  [[ -n "$attachment_id" ]] || continue
  relative="${spool_path#${API_SPOOL_PREFIX}}"
  if [[ "$relative" == "$spool_path" || "$relative" == *".."* ]]; then
    echo "support archive: rejected spool path for attachment $attachment_id" >&2
    continue
  fi
  source_path="$UPEXNOTE_HOST_SPOOL_DIR/$relative"
  [[ -f "$source_path" ]] || { echo "support archive: missing $source_path" >&2; continue; }
  ticket_number="$(psql_json "SELECT ticket_number FROM support.tickets WHERE id=${ticket_id};")"
  [[ -n "$ticket_number" ]] || { echo "support archive: missing ticket $ticket_id" >&2; continue; }
  created="$(psql_json "SELECT to_char(created_at AT TIME ZONE 'UTC','YYYY/MM') FROM support.tickets WHERE id=${ticket_id};")"
  remote_dir="$DRIVE_REMOTE/$created/$ticket_number"
  remote_file="$remote_dir/$stored_filename"
  if rclone copyto --checksum "$source_path" "$remote_file" && rclone check --one-way "$source_path" "$remote_file"; then
    qpath="$(sql_quote "$remote_file")"
    psql_json "UPDATE support.ticket_attachments SET archive_state='archived', drive_path='$qpath', archived_at=now() WHERE id=${attachment_id};" >/dev/null
    rm -- "$source_path"
    echo "support archive: archived $ticket_number attachment $attachment_id"
  else
    psql_json "UPDATE support.ticket_attachments SET archive_state='failed' WHERE id=${attachment_id};" >/dev/null || true
    echo "support archive: failed $ticket_number attachment $attachment_id" >&2
  fi
done <<< "$pending"

# Rebuild durable case files for each touched case. The JSON uses references
# only: no attachment binary, raw transcript, password or local file path.
ticket_ids="$(printf '%s\n' "$pending" | awk -F '\t' 'NF {print $2}' | sort -nu)"
while IFS= read -r ticket_id; do
  [[ -n "$ticket_id" ]] || continue
  ticket_number="$(psql_json "SELECT ticket_number FROM support.tickets WHERE id=${ticket_id};")"
  created="$(psql_json "SELECT to_char(created_at AT TIME ZONE 'UTC','YYYY/MM') FROM support.tickets WHERE id=${ticket_id};")"
  remote_dir="$DRIVE_REMOTE/$created/$ticket_number"
  tmp="$(mktemp -d)"
  trap 'rm -rf "$tmp"' EXIT
  psql_json "SELECT jsonb_build_object('ticket', jsonb_build_object('number',t.ticket_number,'subject',t.subject,'status',t.status,'category',t.category,'priority',t.priority,'created_at',t.created_at,'updated_at',t.updated_at),'requester',jsonb_build_object('username',i.username,'email',i.email,'name',i.display_name),'description',d.body,'comments',coalesce((SELECT jsonb_agg(jsonb_build_object('author_kind',c.author_kind,'author',c.author_label,'body',c.body,'created_at',c.created_at) ORDER BY c.id) FROM support.ticket_comments c WHERE c.ticket_id=t.id),'[]'::jsonb),'status_history',coalesce((SELECT jsonb_agg(jsonb_build_object('from',h.from_status,'to',h.to_status,'actor_kind',h.actor_kind,'reason',h.reason,'changed_at',h.changed_at) ORDER BY h.id) FROM support.ticket_status_history h WHERE h.ticket_id=t.id),'[]'::jsonb),'attachments',coalesce((SELECT jsonb_agg(jsonb_build_object('filename',a.original_filename,'sha256',a.sha256,'content_type',a.content_type,'bytes',a.byte_size,'archive_state',a.archive_state,'drive_path',a.drive_path,'created_at',a.created_at) ORDER BY a.id) FROM support.ticket_attachments a WHERE a.ticket_id=t.id),'[]'::jsonb)) FROM support.tickets t JOIN support.identities i ON i.id=t.identity_id JOIN support.ticket_descriptions d ON d.ticket_id=t.id WHERE t.id=${ticket_id};" > "$tmp/case.json"
  printf '# %s\n\nCanonical support case archive. See `case.json` for the complete structured history and evidence references.\n' "$ticket_number" > "$tmp/case.md"
  rclone copyto --checksum "$tmp/case.json" "$remote_dir/case.json"
  rclone copyto --checksum "$tmp/case.md" "$remote_dir/case.md"
  rm -rf "$tmp"; trap - EXIT
done <<< "$ticket_ids"
