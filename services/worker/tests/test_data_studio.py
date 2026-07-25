import unittest

from transcription import data_studio


class DataStudioSafetyTests(unittest.TestCase):
    def test_secret_bearing_column_names_are_protected(self):
        for name in (
            "password_hash", "code_hash", "token_digest", "totp_secret",
            "api_key", "provider_id", "credential_value",
        ):
            with self.subTest(name=name):
                self.assertTrue(data_studio._protected(name))

    def test_regular_business_columns_remain_visible(self):
        for name in ("id", "email", "created_at", "ticket_number", "status"):
            with self.subTest(name=name):
                self.assertFalse(data_studio._protected(name))


if __name__ == "__main__":
    unittest.main()
