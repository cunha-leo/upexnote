"""Cryptographic primitives shared by the password-reset flow."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import base64
import struct
import time
from io import BytesIO
from urllib.parse import quote

from cryptography.fernet import Fernet, InvalidToken
import qrcode
import qrcode.image.svg


def normalize_email(email: str) -> str:
    return email.strip().casefold()


def generate_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")


def keyed_hash(value: str, secret: str, purpose: str) -> str:
    message = f"{purpose}\0{value}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).hexdigest()


def constant_time_equal(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def _totp_key(secret: str) -> bytes:
    padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(padded, casefold=True)


def totp_code(secret: str, at_time: int | None = None) -> str:
    counter = int((time.time() if at_time is None else at_time) // 30)
    digest = hmac.new(_totp_key(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{value % 1_000_000:06d}"


def verify_totp(secret: str, code: str, at_time: int | None = None, window: int = 1) -> bool:
    now = int(time.time() if at_time is None else at_time)
    return any(
        constant_time_equal(totp_code(secret, now + offset * 30), code)
        for offset in range(-window, window + 1)
    )


def _fernet(master_secret: str) -> Fernet:
    key = hashlib.sha256(("upexnote-totp-v1\0" + master_secret).encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt_totp_secret(secret: str, master_secret: str) -> str:
    return _fernet(master_secret).encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_totp_secret(ciphertext: str, master_secret: str) -> str:
    try:
        return _fernet(master_secret).decrypt(ciphertext.encode("ascii")).decode("ascii")
    except InvalidToken as exc:
        raise ValueError("invalid_totp_secret") from exc


def totp_uri(secret: str, email: str) -> str:
    issuer = "UpexNote"
    label = quote(f"{issuer}:{email}", safe="")
    return (
        f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}"
        "&algorithm=SHA1&digits=6&period=30"
    )


def qr_svg_data_url(value: str) -> str:
    image = qrcode.make(value, image_factory=qrcode.image.svg.SvgPathImage, box_size=8, border=3)
    stream = BytesIO()
    image.save(stream)
    encoded = base64.b64encode(stream.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def hash_password(password: str, salt: str) -> str:
    """Keep byte-for-byte compatibility with accounts.py::_hash_password."""
    return hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), 120_000
    ).hex()


def new_password_credentials(password: str) -> tuple[str, str]:
    salt = secrets.token_bytes(16).hex()
    return salt, hash_password(password, salt)
