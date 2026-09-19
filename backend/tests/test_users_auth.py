from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.plans import get_plan, list_plans
from app.core.users import public_user, upsert_google_user
from app.main import app


def test_plans_catalog() -> None:
    plans = list_plans()
    assert {row["id"] for row in plans} == {"free", "pro"}
    assert get_plan("pro")["price_mnt"] == 9_900


def test_upsert_google_user(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    first = upsert_google_user(sub="abc", email="a@example.com", name="A", picture="")
    assert first["plan"] == "free"
    second = upsert_google_user(sub="abc", email="a@example.com", name="A2", picture="")
    assert second["name"] == "A2"
    pub = public_user(second)
    assert pub["email"] == "a@example.com"
    assert pub["entitlements"]["check_max_chars"] > 0


def test_google_login_requires_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.api.routes_auth.settings.google_client_id", "test-client.apps.googleusercontent.com")
    client = TestClient(app)
    empty = client.post("/api/v1/auth/google", json={})
    assert empty.status_code == 400


def test_google_login_access_token(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.api.routes_auth.settings.google_client_id", "test-client.apps.googleusercontent.com")

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "sub": "google-sub-1",
                "email": "user@example.com",
                "name": "Test User",
                "picture": "https://example.com/a.png",
            }

    monkeypatch.setattr("app.api.routes_auth.httpx.get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)
    response = client.post("/api/v1/auth/google", json={"access_token": "ya29.fake-token-value"})
    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["user"]["email"] == "user@example.com"
    assert "mw_user" in response.cookies
