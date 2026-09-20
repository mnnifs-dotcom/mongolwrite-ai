from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.plans import get_plan, list_plans
from app.core.users import public_user, upsert_google_user
from app.main import app


def test_plans_catalog() -> None:
    plans = list_plans()
    assert {row["id"] for row in plans} == {"free", "pro_3m", "pro_year"}
    assert get_plan("pro_year")["price_mnt"] == 19_900
    assert get_plan("pro_3m")["price_mnt"] == 6_000


def test_upsert_google_user(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    first = upsert_google_user(sub="abc", email="a@example.com", name="A", picture="")
    assert first["plan"] == "free"
    second = upsert_google_user(sub="abc", email="a@example.com", name="A2", picture="")
    assert second["name"] == "A2"
    pub = public_user(second)
    assert pub["email"] == "a@example.com"
    assert pub["entitlements"]["check_max_chars"] == 300_000


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


def test_admin_users_list_and_plan(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.config.settings.admin_username", "admin")
    monkeypatch.setattr("app.core.config.settings.admin_password", "test-pass")
    monkeypatch.setattr("app.core.config.settings.secret_key", "test-secret")

    from app.core.users import set_user_plan, upsert_google_user

    upsert_google_user(sub="u1", email="free@example.com", name="Free User")
    upsert_google_user(sub="u2", email="pro@example.com", name="Pro User")
    set_user_plan("u2", "pro_year", plan_expires_at="2099-12-31")

    client = TestClient(app)
    assert client.get("/api/v1/admin/users").status_code == 401
    login = client.post(
        "/api/v1/admin/login",
        json={"username": "admin", "password": "test-pass"},
    )
    assert login.status_code == 200

    listed = client.get("/api/v1/admin/users").json()
    assert listed["counts"]["total"] == 2
    assert listed["counts"]["paid"] == 1
    assert listed["counts"]["free"] == 1
    emails = {row["email"] for row in listed["items"]}
    assert emails == {"free@example.com", "pro@example.com"}

    paid = client.get("/api/v1/admin/users?plan=paid").json()
    assert paid["total"] == 1
    assert paid["items"][0]["email"] == "pro@example.com"
    assert paid["items"][0]["is_paid"] is True
    assert paid["items"][0]["plan_expires_at"]

    patched = client.patch(
        "/api/v1/admin/users/u1/plan",
        json={"plan": "pro_3m", "plan_expires_at": "2099-01-15"},
    )
    assert patched.status_code == 200
    assert patched.json()["user"]["is_paid"] is True
    assert patched.json()["user"]["plan"] == "pro_3m"
