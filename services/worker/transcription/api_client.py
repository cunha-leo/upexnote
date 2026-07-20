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

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(
            self.base_url + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Accept": "application/json", "Content-Type": "application/json"},
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
