from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.users import (
    MAX_DEVICES,
    clear_user_devices,
    list_user_devices,
    register_or_touch_device,
    touch_last_check,
    upsert_google_user,
)
from app.engine.admin_review import collect_review_words
from app.main import app


class _FakeDict:
    def __init__(self, seeded: set[str]):
        self._seeded = {w.casefold() for w in seeded}

    def in_seed(self, word: str) -> bool:
        return word.casefold() in self._seeded


def test_max_two_devices(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    upsert_google_user(sub="u1", email="a@example.com", name="A")
    register_or_touch_device("u1", "deviceaaaa1")
    register_or_touch_device("u1", "devicebbbb2")
    assert len(list_user_devices("u1")) == MAX_DEVICES
    with pytest.raises(PermissionError):
        register_or_touch_device("u1", "devicecccc3")
    # Touching an existing device is fine.
    register_or_touch_device("u1", "deviceaaaa1")
    clear_user_devices("u1")
    assert list_user_devices("u1") == []
    register_or_touch_device("u1", "devicenew01")
    assert len(list_user_devices("u1")) == 1


def test_touch_last_check(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    upsert_google_user(sub="u1", email="a@example.com", name="A")
    row = touch_last_check("u1")
    assert row is not None
    assert row.get("last_check_at")


def test_collect_review_skips_curated(monkeypatch, tmp_path) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)
    monkeypatch.setattr("app.engine.dictionary.persist_dir", lambda: persist)

    from app.engine.hunspell_candidates import persist_dir as cand_persist

    path = cand_persist() / "hunspell_candidates.json"
    path.write_text(
        '{"words": ['
        '{"word": "сайн", "folded": "сайн", "tier": "doubt", '
        '"reason": "test", "suggestion": "", "count": 1, '
        '"seen_at": "2099-01-01T00:00:00+00:00", "updated_at": "2099-01-01T00:00:00+00:00"},'
        '{"word": "шинэүг", "folded": "шинэүг", "tier": "doubt", '
        '"reason": "test", "suggestion": "", "count": 1, '
        '"seen_at": "2099-01-01T00:00:00+00:00", "updated_at": "2099-01-01T00:00:00+00:00"}'
        "]}",
        encoding="utf-8",
    )
    result = collect_review_words(dictionary=_FakeDict({"сайн"}))
    folded = {row["folded"] for row in result["items"]}
    assert "сайн" not in folded
    assert "шинэүг" in folded
    assert result["skipped_curated"] >= 1


def test_google_login_replaces_oldest_device(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "app.api.routes_auth.settings.google_client_id",
        "test-client.apps.googleusercontent.com",
    )

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
    headers1 = {"X-MW-Device-Id": "deviceaaaa01"}
    headers2 = {"X-MW-Device-Id": "devicebbbb02"}
    headers3 = {"X-MW-Device-Id": "devicecccc03"}
    assert (
        client.post(
            "/api/v1/auth/google",
            json={"access_token": "ya29.fake"},
            headers=headers1,
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/google",
            json={"access_token": "ya29.fake"},
            headers=headers2,
        ).status_code
        == 200
    )
    # Third Google login replaces the least-recently-seen device (device 1).
    allowed = client.post(
        "/api/v1/auth/google",
        json={"access_token": "ya29.fake"},
        headers=headers3,
    )
    assert allowed.status_code == 200
    ids = {item["id"] for item in list_user_devices("google-sub-1")}
    assert ids == {"devicebbbb02", "devicecccc03"}
    assert "дэмжлэг" not in str(allowed.json())

    # Logout on device 2 frees a slot without needing LRU.
    assert client.post("/api/v1/auth/logout", headers=headers2).status_code == 200
    assert {item["id"] for item in list_user_devices("google-sub-1")} == {"devicecccc03"}
    assert (
        client.post(
            "/api/v1/auth/google",
            json={"access_token": "ya29.fake"},
            headers=headers1,
        ).status_code
        == 200
    )
    assert len(list_user_devices("google-sub-1")) == 2


def test_session_check_still_blocks_unknown_device(monkeypatch, tmp_path) -> None:
    """Authenticated session checks do not silently take over a third device."""
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "app.api.routes_auth.settings.google_client_id",
        "test-client.apps.googleusercontent.com",
    )

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "sub": "google-sub-block",
                "email": "block@example.com",
                "name": "Block",
                "picture": "",
            }

    monkeypatch.setattr("app.api.routes_auth.httpx.get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)
    h1 = {"X-MW-Device-Id": "deviceaaaa01"}
    h2 = {"X-MW-Device-Id": "devicebbbb02"}
    h3 = {"X-MW-Device-Id": "devicecccc03"}
    assert client.post("/api/v1/auth/google", json={"access_token": "t"}, headers=h1).status_code == 200
    assert client.post("/api/v1/auth/google", json={"access_token": "t"}, headers=h2).status_code == 200
    # Steal cookie onto a third device id → /me must still refuse without LRU replace.
    blocked = client.get("/api/v1/auth/me", headers=h3)
    assert blocked.status_code == 403
    detail = blocked.json()["detail"]
    assert "2 төхөөрөмж" in detail
    assert "дэмжлэг" not in detail


def test_logout_unregisters_current_device(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr(
        "app.api.routes_auth.settings.google_client_id",
        "test-client.apps.googleusercontent.com",
    )

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "sub": "google-sub-2",
                "email": "two@example.com",
                "name": "Two",
                "picture": "",
            }

    monkeypatch.setattr("app.api.routes_auth.httpx.get", lambda *args, **kwargs: FakeResponse())
    client = TestClient(app)
    headers = {"X-MW-Device-Id": "deviceonly01"}
    assert (
        client.post(
            "/api/v1/auth/google",
            json={"access_token": "ya29.fake"},
            headers=headers,
        ).status_code
        == 200
    )
    assert len(list_user_devices("google-sub-2")) == 1
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 200
    assert list_user_devices("google-sub-2") == []


def test_ai_key_requires_admin(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.config.settings.admin_username", "admin")
    monkeypatch.setattr("app.core.config.settings.admin_password", "test-pass")
    monkeypatch.setattr("app.core.config.settings.secret_key", "test-secret")
    monkeypatch.setattr("app.core.config.settings.app_env", "development")
    client = TestClient(app)
    bare = client.post("/api/v1/settings/ai-key", json={"key": "sk-test"})
    assert bare.status_code == 401
    login = client.post(
        "/api/v1/admin/login",
        json={"username": "admin", "password": "test-pass"},
    )
    assert login.status_code == 200
    ok = client.post("/api/v1/settings/ai-key", json={"key": ""})
    assert ok.status_code == 200


def test_production_blocks_default_admin_password(monkeypatch) -> None:
    monkeypatch.setattr("app.core.config.settings.app_env", "production")
    monkeypatch.setattr("app.core.config.settings.admin_password", "Ilove@00")
    monkeypatch.setattr("app.core.config.settings.secret_key", "change-me-in-production")
    monkeypatch.setattr("app.core.config.settings.admin_username", "Admin write")
    client = TestClient(app)
    response = client.post(
        "/api/v1/admin/login",
        json={"username": "Admin write", "password": "Ilove@00"},
    )
    assert response.status_code == 503
