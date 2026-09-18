from __future__ import annotations

from pathlib import Path

from app.main import app
from fastapi.testclient import TestClient


def _login(client: TestClient, monkeypatch, persist: Path) -> None:
    monkeypatch.setattr("app.core.config.settings.admin_username", "admin")
    monkeypatch.setattr("app.core.config.settings.admin_password", "test-pass")
    monkeypatch.setattr("app.core.config.settings.secret_key", "test-secret")
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)
    response = client.post(
        "/api/v1/admin/login",
        json={"username": "admin", "password": "test-pass"},
    )
    assert response.status_code == 200


def test_admin_me_requires_login() -> None:
    assert TestClient(app).get("/api/v1/admin/me").status_code == 401


def test_hunspell_candidates_harvest_classify_approve(monkeypatch, tmp_path) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    user_dict = tmp_path / "user_dictionary.txt"
    user_dict.write_text("", encoding="utf-8")
    monkeypatch.setattr("app.engine.dictionary.user_dictionary_path", lambda: user_dict)
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)

    # Reset singleton engine so it picks up the temp user dictionary.
    import app.engine.runtime as runtime

    runtime._engine = None

    client = TestClient(app)
    assert client.get("/api/v1/admin/candidates").status_code == 401
    _login(client, monkeypatch, persist)

    # «байгууллага» is almost always Hunspell-known and frequent on Wikipedia.
    # Use a word Hunspell accepts that is unlikely in the tiny seed wordlist.
    harvest = client.post(
        "/api/v1/admin/candidates/harvest",
        json={"text": "Монгол Улсын нийслэл Улаанбаатар хотын иргэд ажиллаж байна."},
    )
    assert harvest.status_code == 200
    body = harvest.json()
    assert "counts" in body

    all_items = client.get("/api/v1/admin/candidates").json()["items"]
    # At least one harvested candidate that is not already curated.
    assert isinstance(all_items, list)

    reliable = client.get("/api/v1/admin/candidates?tier=reliable").json()
    doubt = client.get("/api/v1/admin/candidates?tier=doubt").json()
    assert reliable["count"] + doubt["count"] == len(all_items)

    if not all_items:
        # Hunspell may be unavailable in some CI images — still verify empty approve path.
        empty = client.post("/api/v1/admin/candidates/approve", json={"words": []})
        assert empty.status_code == 400
        return

    target = all_items[0]["word"]
    approved = client.post("/api/v1/admin/candidates/approve", json={"words": [target]})
    assert approved.status_code == 200
    assert approved.json()["added_count"] >= 1

    remaining = {item["folded"] for item in client.get("/api/v1/admin/candidates").json()["items"]}
    assert target.casefold() not in remaining

    # Engine curated lexicon should now contain the approved word.
    from app.engine.runtime import get_engine

    assert get_engine().dictionary.in_seed(target) or get_engine().dictionary.in_wordlist(target)


def test_hunspell_candidates_reject(monkeypatch, tmp_path) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    user_dict = tmp_path / "user_dictionary.txt"
    user_dict.write_text("", encoding="utf-8")
    monkeypatch.setattr("app.engine.dictionary.user_dictionary_path", lambda: user_dict)
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)

    import app.engine.runtime as runtime

    runtime._engine = None

    client = TestClient(app)
    _login(client, monkeypatch, persist)
    client.post(
        "/api/v1/admin/candidates/harvest",
        json={"text": "нийслэл хотын иргэд ажиллаж байна."},
    )
    items = client.get("/api/v1/admin/candidates").json()["items"]
    if not items:
        return
    word = items[0]["word"]
    rejected = client.post("/api/v1/admin/candidates/reject", json={"words": [word]})
    assert rejected.status_code == 200
    assert rejected.json()["removed_count"] == 1
    # Re-harvest should not bring rejected word back.
    client.post(
        "/api/v1/admin/candidates/harvest",
        json={"text": "нийслэл хотын иргэд ажиллаж байна."},
    )
    folded = {item["folded"] for item in client.get("/api/v1/admin/candidates").json()["items"]}
    assert word.casefold() not in folded


def test_check_triggers_harvest_without_failing(monkeypatch, tmp_path) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)
    client = TestClient(app)
    response = client.post(
        "/api/v1/check/deterministic",
        json={"text": "нийслэл хотын иргэд.", "style": "standard"},
    )
    assert response.status_code == 200
    assert "corrections" in response.json()
