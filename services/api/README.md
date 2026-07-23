# UpexNote API

FastAPI service for the central, versioned UpexNote API. Release `0.2.0`
delivers password reset and administrative MFA. Administrative elevation uses
identity + administrator password + **TOTP or e-mail code**. TOTP is compatible
with standard authenticator apps through an `otpauth://` QR Code, while e-mail
always remains available as the recovery alternative.

Installation telemetry is privacy-preserving: it records only a hashed
installation identifier plus approved operational fields (version, engine,
duration, estimated cost, region and error code). It never accepts transcript,
audio, video, file path, credential or arbitrary diagnostic payloads.
Installations explicitly opt in, exchange their local anonymous ID for an
opaque 90-day token, then use that token to submit telemetry. Webhooks remain
reserved until their concrete product contract is defined.

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
secret of at least 32 characters. It also derives a purpose-separated
encryption key for TOTP secrets; the plaintext authenticator secret is never
stored in PostgreSQL.

The service reaches PostgreSQL only through the EasyPanel internal network at
the service host configured by `UPEXNOTE_DB_HOST` (default `upexnote-db`). The
schema migration is idempotent and runs on API startup.
