"""R03.1 BUG-03: FastAPI support ticket payload must preserve Unicode.
No production DB or real account credentials are used.
"""
from fastapi.testclient import TestClient
from app.main import create_app
from app.dependencies import get_support_repository

ACCENTED = "Isso é um teste — ação, coração, português."

class FakeUnicodeSupportRepository:
    def identity(self, *, email, username, display_name, client_secret):
        return {"id": 1, "email": email, "username": username,
                "display_name": display_name or "Teste"}

    def ticket_detail(self, ticket_id, identity_id=None):
        assert ticket_id == 1
        return {"id": 1, "description": ACCENTED,
                "comments": [{"id": 1, "body": ACCENTED}]}

    def add_comment(self, ticket_id, *, body, author_kind, author_identity_id, author_label):
        assert ticket_id == 1
        assert body == ACCENTED
        return {"id": 2, "body": body, "author_kind": author_kind}

def test_support_detail_fastapi_utf8_roundtrip():
    app = create_app(initialize_schema=False)
    app.dependency_overrides[get_support_repository] = lambda: FakeUnicodeSupportRepository()
    with TestClient(app) as client:
        response = client.post("/v1/support/tickets/detail", json={
            "email": "test@example.test", "username": "test",
            "client_secret": "test-secret-at-least-32-characters-long",
            "ticket_id": 1,
        })
    assert response.status_code == 200
    assert response.json()["ticket"]["description"] == ACCENTED
    assert response.json()["ticket"]["comments"][0]["body"] == ACCENTED

def test_support_comment_fastapi_utf8_roundtrip():
    app = create_app(initialize_schema=False)
    app.dependency_overrides[get_support_repository] = lambda: FakeUnicodeSupportRepository()
    with TestClient(app) as client:
        response = client.post("/v1/support/tickets/comment", json={
            "email": "test@example.test", "username": "test",
            "client_secret": "test-secret-at-least-32-characters-long",
            "ticket_id": 1, "body": ACCENTED,
        })
    assert response.status_code == 200
    assert response.json()["comment"]["body"] == ACCENTED
