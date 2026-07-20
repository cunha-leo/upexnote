from __future__ import annotations

import base64

from app.security import (
    decrypt_totp_secret,
    encrypt_totp_secret,
    totp_code,
    totp_uri,
    verify_totp,
)


def test_totp_matches_rfc_6238_sha1_vector_truncated_to_six_digits():
    # RFC 6238 SHA-1 secret (ASCII "12345678901234567890"), t=59 -> 94287082.
    # Standard authenticator apps use the same HOTP result truncated to 6 digits.
    secret = base64.b32encode(b"12345678901234567890").decode("ascii").rstrip("=")
    assert totp_code(secret, at_time=59) == "287082"
    assert verify_totp(secret, "287082", at_time=59, window=0)


def test_totp_secret_is_encrypted_at_rest_and_uri_is_authenticator_compatible():
    secret = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
    master = "independent-test-secret-with-at-least-32-characters"
    encrypted = encrypt_totp_secret(secret, master)
    assert secret not in encrypted
    assert decrypt_totp_secret(encrypted, master) == secret
    uri = totp_uri(secret, "owner@example.com")
    assert uri.startswith("otpauth://totp/UpexNote%3Aowner%40example.com?")
    assert "issuer=UpexNote" in uri and "digits=6" in uri and "period=30" in uri
