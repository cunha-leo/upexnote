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


if __name__ == "__main__":
    unittest.main()
