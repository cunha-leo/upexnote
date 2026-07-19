from __future__ import annotations

from dataclasses import dataclass

from app.db import CompleteResult, RequestStart, VerifyResult


class FakeMailer:
    def __init__(self):
        self.deliveries: list[tuple[str, str, int]] = []

    def send_reset_code(self, recipient: str, code: str, expires_minutes: int) -> None:
        self.deliveries.append((recipient, code, expires_minutes))


@dataclass
class FakeUser:
    id: int
    email: str
    salt: str | None = None
    password_hash: str | None = None


class FakeRepository:
    def __init__(self, known_email: str = "owner@example.com"):
        self.user = FakeUser(7, known_email)
        self.records: list[dict] = []
        self.events: list[tuple[str, bool, str]] = []

    def ensure_schema(self) -> None:
        return None

    def ping(self) -> None:
        return None

    def start_request(self, **kwargs) -> RequestStart:
        email_records = [r for r in self.records if r["email_hash"] == kwargs["email_hash"]]
        ip_records = [r for r in self.records if r["ip_hash"] == kwargs["ip_hash"]]
        accepted_by_rate = (
            len(email_records) < kwargs["email_limit"]
            and len(ip_records) < kwargs["ip_limit"]
        )
        known = kwargs["email"] == self.user.email
        record = {
            "id": len(self.records) + 1,
            "email_hash": kwargs["email_hash"],
            "ip_hash": kwargs["ip_hash"],
            "code_hash": kwargs["code_hash"] if known and accepted_by_rate else None,
            "attempts": 0,
            "invalid": False,
            "token_hash": None,
            "used": False,
        }
        for previous in self.records:
            if known and accepted_by_rate and previous["code_hash"]:
                previous["invalid"] = True
        self.records.append(record)
        accepted = bool(record["code_hash"])
        self.events.append(("password_reset_requested", accepted, kwargs["email"]))
        return RequestStart(
            accepted,
            record["id"] if accepted else None,
            self.user.id if known else None,
            self.user.email if accepted else None,
        )

    def invalidate_delivery(self, reset_id: int, email: str, user_id: int) -> None:
        self.records[reset_id - 1]["invalid"] = True
        self.events.append(("password_reset_failed", False, email))

    def verify_code(self, **kwargs) -> VerifyResult:
        candidates = [
            r for r in self.records
            if r["email_hash"] == kwargs["email_hash"]
            and r["code_hash"] and not r["invalid"] and not r["used"]
            and r["token_hash"] is None
        ]
        if not candidates:
            self.events.append(("password_reset_failed", False, kwargs["email"]))
            return VerifyResult(False, "invalid_or_expired_code")
        record = candidates[-1]
        record["attempts"] += 1
        if record["code_hash"] != kwargs["code_hash"]:
            if record["attempts"] >= kwargs["max_attempts"]:
                record["invalid"] = True
            self.events.append(("password_reset_failed", False, kwargs["email"]))
            return VerifyResult(False, "invalid_code", self.user.id)
        record["token_hash"] = kwargs["reset_token_hash"]
        return VerifyResult(True, "verified", self.user.id)

    def complete_reset(self, **kwargs) -> CompleteResult:
        candidates = [
            r for r in self.records
            if r["email_hash"] == kwargs["email_hash"]
            and r["token_hash"] == kwargs["reset_token_hash"]
            and not r["invalid"] and not r["used"]
        ]
        if not candidates:
            self.events.append(("password_reset_failed", False, kwargs["email"]))
            return CompleteResult(False, "invalid_or_expired_token")
        record = candidates[-1]
        record["used"] = True
        self.user.salt = kwargs["password_salt"]
        self.user.password_hash = kwargs["password_hash"]
        self.events.append(("password_reset_completed", True, kwargs["email"]))
        return CompleteResult(True, "completed", self.user.id)
