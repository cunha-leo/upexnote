from __future__ import annotations

import json
import unittest
from unittest.mock import patch
import urllib.error

from transcription.api_client import UpexNoteApiClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


class ApiClientTests(unittest.TestCase):
    @patch("transcription.api_client.urllib.request.urlopen")
    def test_complete_sends_secrets_in_json_body_not_url(self, urlopen):
        urlopen.return_value = FakeResponse({"ok": True})
        client = UpexNoteApiClient("https://api.example.test")
        result = client.complete_reset("owner@example.com", "one-time-token", "new-password")
        self.assertTrue(result["ok"])
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://api.example.test/v1/auth/reset/complete")
        self.assertNotIn("one-time-token", request.full_url)
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["reset_token"], "one-time-token")
        self.assertEqual(body["new_password"], "new-password")

    @patch("transcription.api_client.urllib.request.urlopen")
    def test_http_400_is_sanitized(self, urlopen):
        urlopen.side_effect = urllib.error.HTTPError(
            "https://api.example.test/v1/auth/reset/verify", 400, "bad", {}, None
        )
        result = UpexNoteApiClient("https://api.example.test").verify_reset(
            "owner@example.com", "123456"
        )
        self.assertEqual(result, {"ok": False, "error": "invalid_or_expired"})

    @patch("transcription.api_client.urllib.request.urlopen")
    def test_admin_challenge_keeps_secret_in_json_and_supports_email_fallback(self, urlopen):
        urlopen.return_value = FakeResponse({"message": "accepted", "factor": "email"})
        client = UpexNoteApiClient("https://api.example.test")
        result = client.request_admin_challenge(
            "owner@example.com", "administrator-secret", prefer_email=True
        )
        self.assertEqual(result["factor"], "email")
        request = urlopen.call_args.args[0]
        self.assertEqual(
            request.full_url, "https://api.example.test/v1/admin/elevation/challenge"
        )
        self.assertNotIn("administrator-secret", request.full_url)
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["admin_secret"], "administrator-secret")
        self.assertTrue(body["prefer_email"])

    @patch("transcription.api_client.urllib.request.urlopen")
    def test_admin_validation_keeps_session_token_in_json_body(self, urlopen):
        urlopen.return_value = FakeResponse({"valid": True, "user_id": 2})
        result = UpexNoteApiClient("https://api.example.test").validate_admin_session(
            "owner@example.com", "opaque-session-token"
        )
        self.assertTrue(result["valid"])
        request = urlopen.call_args.args[0]
        self.assertNotIn("opaque-session-token", request.full_url)
        body = json.loads(request.data.decode("utf-8"))
        self.assertEqual(body["elevation_token"], "opaque-session-token")


if __name__ == "__main__":
    unittest.main()
