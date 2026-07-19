"""Cryptographic primitives shared by the password-reset flow."""

from __future__ import annotations

import hashlib
import hmac
import secrets


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def keyed_hash(value: str, secret: str, purpose: str) -> str:
    message = f"{purpose}\0{value}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def hash_password(password: str, salt: str) -> str:
    """Keep byte-for-byte compatibility with accounts.py::_hash_password."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
    ).hex()


def new_password_credentials(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16).hex()
    return salt, hash_password(password, salt)
