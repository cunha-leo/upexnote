from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.admin_service import AdminElevationService
from app.config import Settings
from app.dependencies import get_admin_elevation_service, get_reset_service
from app.main import create_app
from app.service import PasswordResetService
from tests.fakes import FakeAdminRepository, FakeMailer, FakeRepository


def settings() -> Settings:
    return Settings(
        db_host="unused", db_port=5432, db_name="unused", db_user="unused",
        db_password="correct-admin-secret",
        reset_hmac_secret="test-secret-with-more-than-thirty-two-characters",
        smtp_host="unused", smtp_port=587, smtp_username="unused", smtp_password="unused",
        smtp_from_email="no-reply@example.com", smtp_from_name="UpexNote",
        smtp_starttls=True, smtp_ssl=False,
        reset_ttl_seconds=600, reset_token_ttl_seconds=600, reset_max_attempts=5,
        reset_rate_window_seconds=900, reset_rate_email_max=3, reset_rate_ip_max=10,
        admin_code_ttl_seconds=600, admin_session_ttl_seconds=28800,
        admin_max_attempts=5, admin_rate_window_seconds=900,
        admin_rate_email_max=3, admin_rate_ip_max=10,
    )


@pytest.fixture
def flow():
    cfg = settings()
    repository = FakeAdminRepository()
    mailer = FakeMailer()
    admin_service = AdminElevationService(cfg, repository, mailer)
    reset_service = PasswordResetService(cfg, FakeRepository(), FakeMailer())
    app = create_app(initialize_schema=False)
    app.dependency_overrides[get_admin_elevation_service] = lambda: admin_service
    app.dependency_overrides[get_reset_service] = lambda: reset_service
    with TestClient(app) as client:
        yield client, repository, mailer


def test_email_factor_issues_valid_revocable_session(flow):
    client, repository, mailer = flow
    challenge = client.post("/v1/admin/elevation/challenge", json={
        "email": "owner@example.com", "admin_secret": "correct-admin-secret"
    })
    assert challenge.status_code == 202
    assert challenge.json()["factor"] == "email"
    assert len(mailer.deliveries) == 1

    code = mailer.deliveries[0][1]
    verified = client.post("/v1/admin/elevation/verify", json={
        "email": "owner@example.com", "code": code
    })
    assert verified.status_code == 200
    token = verified.json()["elevation_token"]
    assert verified.json()["totp_enrolled"] is False

    valid = client.post("/v1/admin/elevation/validate", json={
        "email": "owner@example.com", "elevation_token": token
    }).json()
    assert valid["valid"] is True and valid["user_id"] == repository.user_id
    assert valid["totp_enrolled"] is False

    assert client.post("/v1/admin/elevation/revoke", json={
        "email": "owner@example.com", "elevation_token": token
    }).status_code == 200
    assert client.post("/v1/admin/elevation/validate", json={
        "email": "owner@example.com", "elevation_token": token
    }).json()["valid"] is False


def test_wrong_admin_secret_is_generic_and_sends_nothing(flow):
    client, _, mailer = flow
    response = client.post("/v1/admin/elevation/challenge", json={
        "email": "owner@example.com", "admin_secret": "wrong"
    })
    assert response.status_code == 202
    assert response.json()["factor"] == "email"
    assert mailer.deliveries == []


def test_totp_is_primary_but_email_remains_recovery(flow):
    client, repository, mailer = flow
    repository.totp_enrolled = True
    primary = client.post("/v1/admin/elevation/challenge", json={
        "email": "owner@example.com", "admin_secret": "correct-admin-secret"
    })
    assert primary.json()["factor"] == "totp"
    assert mailer.deliveries == []
    verified = client.post("/v1/admin/elevation/verify", json={
        "email": "owner@example.com", "code": "654321"
    })
    assert verified.status_code == 200
    assert verified.json()["factor"] == "totp"
    status = client.post("/v1/admin/elevation/validate", json={
        "email": "owner@example.com", "elevation_token": verified.json()["elevation_token"]
    }).json()
    assert status["totp_enrolled"] is True

    recovery = client.post("/v1/admin/elevation/challenge", json={
        "email": "owner@example.com", "admin_secret": "correct-admin-secret",
        "prefer_email": True,
    })
    assert recovery.json()["factor"] == "email"
    assert len(mailer.deliveries) == 1


def test_totp_enrollment_requires_session_and_confirmation(flow):
    client, repository, mailer = flow
    client.post("/v1/admin/elevation/challenge", json={
        "email": "owner@example.com", "admin_secret": "correct-admin-secret"
    })
    token = client.post("/v1/admin/elevation/verify", json={
        "email": "owner@example.com", "code": mailer.deliveries[0][1]
    }).json()["elevation_token"]

    enrollment = client.post("/v1/admin/elevation/totp/enroll", json={
        "email": "owner@example.com", "elevation_token": token
    })
    assert enrollment.status_code == 200
    assert enrollment.json()["qr_data_url"].startswith("data:image/svg+xml;base64,")
    assert len(enrollment.json()["manual_key"]) >= 32

    bad = client.post("/v1/admin/elevation/totp/confirm", json={
        "email": "owner@example.com", "elevation_token": token, "code": "000000"
    })
    assert bad.status_code == 400
    good = client.post("/v1/admin/elevation/totp/confirm", json={
        "email": "owner@example.com", "elevation_token": token, "code": "123456"
    })
    assert good.status_code == 200
    assert repository.totp_enrolled is True
