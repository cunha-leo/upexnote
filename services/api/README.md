# UpexNote API

FastAPI service for the central, versioned UpexNote API. Release `0.1.0`
delivers the password-reset flow and reserves explicit `/v1` routes for admin
elevation, installation telemetry, and Phase 2 tokens/webhooks.

## Local tests

```powershell
cd services/api
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest
```

Tests use in-memory fakes. They do not need database or SMTP credentials.

## EasyPanel deployment

Create an **App** service named `upexnote-api` in the existing `upexnote`
project. Use the GitHub repository and branch `main`, Dockerfile
`services/api/Dockerfile`, build context `services/api`, and proxy port `8000`.
Attach the HTTPS domain to that proxy. Do not publish a raw service port and do
not expose PostgreSQL.

Configure every variable named in `.env.example` in EasyPanel's environment
editor. Real values must never be committed, pasted into build arguments, or
written to logs. `UPEXNOTE_RESET_HMAC_SECRET` must be an independent random
secret of at least 32 characters.

The service reaches PostgreSQL only through the EasyPanel internal network at
the service host configured by `UPEXNOTE_DB_HOST` (default `upexnote-db`). The
schema migration is idempotent and runs on API startup.
