# Support module architecture

## Boundary

Support is a product department, not an extension of transcriptions or
telemetry. Its PostgreSQL objects live exclusively in the `support` schema.
Future departments (for example `study` and `chat`) must receive their own
schemas; product tables must not be mixed into `public`.

## Data model: matrix and satellites

`support.tickets` is the matrix/hub. It owns only the stable identity and
indexes needed to find a case: immutable ticket number, customer identity,
current lifecycle status, priority/category, creation and change dates.

The hub is surrounded by narrow satellites:

| Object | Purpose |
| --- | --- |
| `support.ticket_metadata` | version, application/build, platform and other technical context supplied with a case |
| `support.ticket_descriptions` | immutable opening description (one row per ticket) |
| `support.ticket_comments` | chronological customer and team conversation |
| `support.ticket_attachments` | safe file metadata, SHA-256, content type, storage/archive state and Drive reference; never binary data |
| `support.ticket_status_history` | every lifecycle transition and its actor/reason |
| `support.ticket_notifications` | durable outbound-mail queue and delivery results |
| `support.ticket_audit` | append-only operational audit for reconstruction and administration |
| `support.identities` | support user directory: username, e-mail, display name, lifecycle (`active`/`cancelled`), role, creation/change/cancellation timestamps and a hashed opaque device credential |
| `support.ticket_assignments` | current and historical responsibility: who assigned, who was assigned, when, and why |

Every interaction stores its actor identity and actor role (`customer`,
`support`, `admin` or `system`) plus its own timestamp. The ticket hub keeps
the requester and current assignee for fast queues; history satellites retain
who created, changed, replied, assigned, resolved or cancelled each case. No
ticket, comment or attachment is hard-deleted by routine operations.

## Evidence and archive contract

An uploaded image/PDF is validated by type and size and lands only in a
temporary VPS spool. The database keeps its hash and reference, not the file.
The VPS archive job copies it to the dedicated Drive folder, checks checksum,
generates/updates both `case.json` (machine-readable) and `case.md`
(human-readable), then marks the attachment archived and removes only the
verified temporary copy.

Drive folder convention:

`Projects/upexflow/upexnote/storage/support/tickets/YYYY/MM/UN-000001/`

The case files include ticket title, original description, status history,
comments, attachment hashes and Drive-relative image references. A resolved or
closed case therefore remains analysable later without consuming VPS storage.

## E-mail and lifecycle

`support@upexflow.com` is the support-facing alias. The platform remains the
case system of record; e-mail sends notifications for new cases and replies.
Inbound e-mail is processed by a dedicated job into the same conversation,
never as a second parallel history.

Initial statuses: `open`, `in_progress`, `pending_customer`, `resolved`, and
`closed`. Automatic closure is intentionally not enabled until a retention
rule is agreed; closing never deletes the archive.
