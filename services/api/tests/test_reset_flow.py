from __future__ import annotations

import hashlib

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.dependencies import get_reset_service, get_telemetry_service, get_installation_token_service
from app.main import create_app
from app.service import PasswordResetService
from app.telemetry_service import TelemetryService
from app.token_service import InstallationTokenService
from tests.fakes import FakeMailer, FakeRepository


def settings() -> Settings:
    return Settings(
        db_host="unused",
        db_port=5432,
        db_name="unused",
        db_user="unused",
        db_password="unused",
        reset_hmac_secret="test-secret-with-more-than-thirty-two-characters",
        smtp_host="unused",
        smtp_port=587,
        smtp_username="unused",
        smtp_password="unused",
        smtp_from_email="no-reply@example.com",
        smtp_from_name="UpexNote",
        smtp_starttls=True,
        smtp_ssl=False,
        reset_ttl_seconds=600,
        reset_token_ttl_seconds=600,
        reset_max_attempts=5,
        reset_rate_window_seconds=900,
        reset_rate_email_max=3,
        reset_rate_ip_max=10,
        admin_code_ttl_seconds=600,
        admin_session_ttl_seconds=28800,
        admin_max_attempts=5,
        admin_rate_window_seconds=900,
        admin_rate_email_max=3,
        admin_rate_ip_max=10,
    )


@pytest.fixture
def flow():
    repository = FakeRepository()
    mailer = FakeMailer()
    service = PasswordResetService(settings(), repository, mailer)
    class TelemetryRepository:
        def __init__(self): self.events = []
        def ensure_schema(self): pass
        def ingest(self, **kwargs): self.events.append(kwargs)
    telemetry_repository = TelemetryRepository()
    class TokenRepository:
        def __init__(self): self.tokens = set()
        def ensure_schema(self): pass
        def issue(self, **kwargs): self.tokens.add((kwargs["installation_hash"], kwargs["token_hash"]))
        def valid(self, **kwargs): return (kwargs["installation_hash"], kwargs["token_hash"]) in self.tokens
    token_service = InstallationTokenService(settings(), TokenRepository())
    app = create_app(initialize_schema=False)
    app.dependency_overrides[get_reset_service] = lambda: service
    app.dependency_overrides[get_telemetry_service] = lambda: TelemetryService(settings(), telemetry_repository)
    app.dependency_overrides[get_installation_token_service] = lambda: token_service
    with TestClient(app) as client:
        yield client, repository, mailer


def test_full_reset_flow_is_one_time_and_accounts_compatible(flow):
    client, repository, mailer = flow
    response = client.post("/v1/auth/reset/request", json={"email": "OWNER@example.com"})
    assert response.status_code == 202
    assert len(mailer.deliveries) == 1
    code = mailer.deliveries[0][1]

    response = client.post(
        "/v1/auth/reset/verify", json={"email": "owner@example.com", "code": code}
    )
    assert response.status_code == 200
    token = response.json()["reset_token"]

    response = client.post(
        "/v1/auth/reset/complete",
        json={
            "email": "owner@example.com",
            "reset_token": token,
            "new_password": "A-new-safe-password-2026",
        },
    )
    assert response.status_code == 200
    expected = hashlib.pbkdf2_hmac(
        "sha256",
        b"A-new-safe-password-2026",
        bytes.fromhex(repository.user.salt),
        120_000,
    ).hex()
    assert repository.user.password_hash == expected
    assert len(repository.user.salt) == 32

    replay = client.post(
        "/v1/auth/reset/complete",
        json={
            "email": "owner@example.com",
            "reset_token": token,
            "new_password": "Another-safe-password-2026",
        },
    )
    assert replay.status_code == 400


def test_request_never_reveals_if_account_exists(flow):
    client, _, mailer = flow
    known = client.post("/v1/auth/reset/request", json={"email": "owner@example.com"})
    missing = client.post("/v1/auth/reset/request", json={"email": "missing@example.com"})
    assert known.status_code == missing.status_code == 202
    assert known.json() == missing.json()
    assert len(mailer.deliveries) == 1


def test_code_is_invalidated_after_five_failed_attempts(flow):
    client, _, mailer = flow
    client.post("/v1/auth/reset/request", json={"email": "owner@example.com"})
    real_code = mailer.deliveries[0][1]
    wrong_code = "000000" if real_code != "000000" else "999999"
    for _ in range(5):
        response = client.post(
            "/v1/auth/reset/verify",
            json={"email": "owner@example.com", "code": wrong_code},
        )
        assert response.status_code == 400
    correct_after_lockout = client.post(
        "/v1/auth/reset/verify",
        json={"email": "owner@example.com", "code": real_code},
    )
    assert correct_after_lockout.status_code == 400


def test_rate_limit_keeps_generic_response(flow):
    client, _, mailer = flow
    responses = [
        client.post("/v1/auth/reset/request", json={"email": "owner@example.com"})
        for _ in range(4)
    ]
    assert all(response.status_code == 202 for response in responses)
    assert all(response.json() == responses[0].json() for response in responses)
    assert len(mailer.deliveries) == 3


def test_v1_capabilities_are_explicit(flow):
    client, _, _ = flow
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert client.get("/v1").json()["capabilities"]["password_reset"] == "available"
    assert client.get("/v1").json()["capabilities"]["admin_elevation"] == "available"
    assert client.get("/v1").json()["capabilities"]["telemetry"] == "available"
    assert client.post("/v1/tokens/exchange").status_code == 422


def test_telemetry_requires_explicit_consent_and_rejects_unexpected_content(flow):
    client, _, _ = flow
    event = {
        "installation_id": "11111111-1111-4111-8111-111111111111",
        "consent": True,
        "event": "transcription_completed",
        "app_version": "0.20.0",
        "engine": "assemblyai",
        "duration_seconds": 42,
        "estimated_cost_micros": 120000,
        "region": "PT",
    }
    token = client.post("/v1/tokens/exchange", json={"installation_id": event["installation_id"], "consent": True, "app_version": event["app_version"]}).json()["access_token"]
    assert client.post("/v1/telemetry/events", json=event, headers={"Authorization": f"Bearer {token}"}).status_code == 202
    assert client.post("/v1/telemetry/events", json={**event, "transcript": "never"}, headers={"Authorization": f"Bearer {token}"}).status_code == 422
