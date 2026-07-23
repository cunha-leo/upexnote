"""Small stdlib HTTPS client for the versioned UpexNote API.

Payloads arrive from the desktop over worker stdin. This module never logs or
echoes passwords, reset codes, tokens, or response bodies from unknown errors.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
import mimetypes
import uuid
from pathlib import Path


if getattr(sys, "frozen", False):
    _appdata = Path(os.environ.get("APPDATA", str(Path.home())))
    _candidates = [
        _appdata / "UpexNote" / "api_config.json",
        Path(sys.executable).resolve().parent / "api_config.json",
    ]
    API_CONFIG_PATH = next((path for path in _candidates if path.exists()), _candidates[-1])
else:
    API_CONFIG_PATH = Path(__file__).resolve().parent / "api_config.json"


class ApiConfigurationError(RuntimeError):
    pass


def _load_base_url() -> str:
    try:
        config = json.loads(API_CONFIG_PATH.read_text(encoding="utf-8"))
        base_url = str(config["base_url"]).strip().rstrip("/")
    except Exception as exc:
        raise ApiConfigurationError("api_not_configured") from exc
    if not base_url.startswith("https://"):
        raise ApiConfigurationError("api_https_required")
    return base_url


class UpexNoteApiClient:
    def __init__(self, base_url: str | None = None, timeout: int = 20):
        self.base_url = (base_url or _load_base_url()).rstrip("/")
        self.timeout = timeout

    def _post(self, path: str, payload: dict, authorization: str | None = None) -> dict:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if authorization:
            headers["Authorization"] = f"Bearer {authorization}"
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result if isinstance(result, dict) else {"ok": False, "error": "invalid_response"}
        except urllib.error.HTTPError as exc:
            if exc.code == 400:
                return {"ok": False, "error": "invalid_or_expired"}
            return {"ok": False, "error": "service_unavailable"}
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return {"ok": False, "error": "service_unavailable"}

    def request_reset(self, email: str) -> dict:
        return self._post("/v1/auth/reset/request", {"email": email})

    def verify_reset(self, email: str, code: str) -> dict:
        return self._post("/v1/auth/reset/verify", {"email": email, "code": code})

    def complete_reset(self, email: str, reset_token: str, new_password: str) -> dict:
        return self._post(
            "/v1/auth/reset/complete",
            {"email": email, "reset_token": reset_token, "new_password": new_password},
        )

    def request_admin_challenge(
        self, email: str, admin_secret: str, prefer_email: bool = False
    ) -> dict:
        return self._post(
            "/v1/admin/elevation/challenge",
            {"email": email, "admin_secret": admin_secret, "prefer_email": prefer_email},
        )

    def verify_admin_factor(self, email: str, code: str) -> dict:
        return self._post("/v1/admin/elevation/verify", {"email": email, "code": code})

    def validate_admin_session(self, email: str, elevation_token: str) -> dict:
        return self._post(
            "/v1/admin/elevation/validate",
            {"email": email, "elevation_token": elevation_token},
        )

    def revoke_admin_session(self, email: str, elevation_token: str) -> dict:
        return self._post(
            "/v1/admin/elevation/revoke",
            {"email": email, "elevation_token": elevation_token},
        )

    def begin_totp_enrollment(self, email: str, elevation_token: str) -> dict:
        return self._post(
            "/v1/admin/elevation/totp/enroll",
            {"email": email, "elevation_token": elevation_token},
        )

    def confirm_totp_enrollment(self, email: str, elevation_token: str, code: str) -> dict:
        return self._post(
            "/v1/admin/elevation/totp/confirm",
            {"email": email, "elevation_token": elevation_token, "code": code},
        )

    def exchange_installation_token(self, installation_id: str, app_version: str) -> dict:
        return self._post("/v1/tokens/exchange", {
            "installation_id": installation_id, "consent": True, "app_version": app_version,
        })

    def send_telemetry(self, event: dict, installation_token: str) -> dict:
        return self._post("/v1/telemetry/events", event, authorization=installation_token)

    def telemetry_overview(self, email: str, elevation_token: str, days: int) -> dict:
        return self._post("/v1/telemetry/overview", {"email": email, "elevation_token": elevation_token, "days": days})

    def support(self, operation: str, payload: dict) -> dict:
        routes = {
            "identity": "/v1/support/identity", "create": "/v1/support/tickets",
            "list": "/v1/support/tickets/list", "detail": "/v1/support/tickets/detail",
            "comment": "/v1/support/tickets/comment", "admin-list": "/v1/support/admin/tickets",
            "admin-detail": "/v1/support/admin/tickets/detail", "admin-comment": "/v1/support/admin/tickets/comment",
            "admin-status": "/v1/support/admin/tickets/status", "admin-assignment": "/v1/support/admin/tickets/assignment",
        }
        path = routes.get(operation)
        if not path:
            return {"ok": False, "error": "unsupported_operation"}
        return self._post(path, payload)

    def support_attachment(self, payload: dict, file_path: str) -> dict:
        """Bounded multipart upload; the worker never prints the file path or bytes."""
        path = Path(file_path)
        try:
            raw = path.read_bytes()
        except OSError:
            return {"ok": False, "error": "evidence_unavailable"}
        if len(raw) > 10 * 1024 * 1024:
            return {"ok": False, "error": "evidence_too_large"}
        boundary = "----UpexNote" + uuid.uuid4().hex
        parts: list[bytes] = []
        def field(name: str, value: object) -> None:
            parts.extend([f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(), str(value).encode("utf-8"), b"\r\n"])
        for key in ("email", "username", "display_name", "client_secret", "ticket_id"):
            field(key, payload.get(key, ""))
        content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        parts.extend([f"--{boundary}\r\n".encode(), f'Content-Disposition: form-data; name="file"; filename="{path.name}"\r\n'.encode(), f"Content-Type: {content_type}\r\n\r\n".encode(), raw, b"\r\n", f"--{boundary}--\r\n".encode()])
        request = urllib.request.Request(self.base_url + "/v1/support/tickets/attachment", data=b"".join(parts), method="POST", headers={"Accept": "application/json", "Content-Type": f"multipart/form-data; boundary={boundary}"})
        try:
            with urllib.request.urlopen(request, timeout=max(self.timeout, 45)) as response:
                result = json.loads(response.read().decode("utf-8")); return result if isinstance(result, dict) else {"ok": False, "error": "invalid_response"}
        except urllib.error.HTTPError as exc:
            return {"ok": False, "error": "evidence_too_large" if exc.code == 413 else "unsupported_evidence_type" if exc.code == 415 else "service_unavailable"}
        except (urllib.error.URLError, TimeoutError, OSError, ValueError):
            return {"ok": False, "error": "service_unavailable"}
