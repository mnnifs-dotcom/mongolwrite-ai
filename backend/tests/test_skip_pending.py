from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _login(client: TestClient, monkeypatch, persist) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    # Reload settings is hard; use existing app settings via cookie login if configured.
    # Tests use TestClient against app with env from conftest or defaults.
    from app.core.config import settings

    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "secret")
    monkeypatch.setattr(settings, "secret_key", "test-secret-key-value")
    monkeypatch.setattr("app.engine.pending.persist_dir", lambda: persist)
    monkeypatch.setattr("app.engine.dictionary.persist_dir", lambda: persist)
    monkeypatch.setattr(
        "app.engine.dictionary.user_dictionary_path",
        lambda: persist / "user_dictionary.txt",
    )
    res = client.post("/api/v1/admin/login", json={"username": "admin", "password": "secret"})
    assert res.status_code == 200


def test_skip_queues_for_admin(monkeypatch, tmp_path) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    client = TestClient(app)
    _login(client, monkeypatch, persist)

    skipped = client.post(
        "/api/v1/dictionary/skip",
        json={"word": "шинэүгтест", "rule_id": "unknown_word"},
    )
    assert skipped.status_code == 200
    assert skipped.json()["ok"] is True

    pending = client.get("/api/v1/admin/pending").json()["items"]
    assert any(row["folded"] == "шинэүгтест" for row in pending)

    approved = client.post("/api/v1/admin/pending/approve", json={"word": "шинэүгтест"})
    assert approved.status_code == 200
    assert approved.json()["added_count"] >= 1

    remaining = client.get("/api/v1/admin/pending").json()["items"]
    assert not any(row["folded"] == "шинэүгтест" for row in remaining)


def test_check_returns_only_spelling_categories(monkeypatch) -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/check/deterministic",
        json={"text": "Хүсэлт хүсэлт ирүүлсэн. Яагаад өдрөөс."},
    )
    assert response.status_code == 200
    cats = {item["category"] for item in response.json()["corrections"]}
    assert cats <= {"SPELLING"}
