from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.engine.hunspell_candidates import (
    forget_admin_added,
    list_admin_added,
    record_admin_added,
)
from fastapi.testclient import TestClient

from app.main import app


def test_list_admin_added_date_and_query(monkeypatch, tmp_path) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    user_dict = tmp_path / "user_dictionary.txt"
    user_dict.write_text("", encoding="utf-8")
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)
    monkeypatch.setattr("app.engine.dictionary.persist_dir", lambda: persist)
    monkeypatch.setattr("app.engine.dictionary.user_dictionary_path", lambda: user_dict)
    monkeypatch.setattr(
        "app.engine.dictionary.list_user_dictionary_lemmas",
        lambda: [],
    )

    older = (datetime.now(UTC) - timedelta(days=5)).isoformat()
    newer = datetime.now(UTC).isoformat()
    persist.joinpath("admin_added.json").write_text(
        __import__("json").dumps(
            {
                "words": [
                    {"word": "шинэүг", "folded": "шинэүг", "added_at": newer},
                    {"word": "хуучинүг", "folded": "хуучинүг", "added_at": older},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    all_items = list_admin_added()
    assert [row["folded"] for row in all_items] == ["шинэүг", "хуучинүг"]

    today = datetime.now(UTC).date().isoformat()
    only_new = list_admin_added(since=today, until=today)
    assert [row["folded"] for row in only_new] == ["шинэүг"]

    found = list_admin_added(q="хууч")
    assert [row["folded"] for row in found] == ["хуучинүг"]

    dropped = forget_admin_added(["шинэүг"])
    assert dropped == ["шинэүг"]
    assert [row["folded"] for row in list_admin_added()] == ["хуучинүг"]


def test_added_words_api_filters(monkeypatch, tmp_path) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    monkeypatch.setattr("app.core.config.settings.admin_username", "admin")
    monkeypatch.setattr("app.core.config.settings.admin_password", "test-pass")
    monkeypatch.setattr("app.core.config.settings.secret_key", "test-secret")
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)
    monkeypatch.setattr(
        "app.engine.dictionary.list_user_dictionary_lemmas",
        lambda: [],
    )

    day = datetime.now(UTC).date().isoformat()
    persist.joinpath("admin_added.json").write_text(
        __import__("json").dumps(
            {
                "words": [
                    {
                        "word": "шалгахүг",
                        "folded": "шалгахүг",
                        "added_at": datetime.now(UTC).isoformat(),
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    client = TestClient(app)
    assert (
        client.post(
            "/api/v1/admin/login",
            json={"username": "admin", "password": "test-pass"},
        ).status_code
        == 200
    )
    filtered = client.get(
        "/api/v1/admin/added-words",
        params={"since": day, "until": day, "q": "шалгах"},
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert body["count"] == 1
    assert body["items"][0]["folded"] == "шалгахүг"

    empty = client.get(
        "/api/v1/admin/added-words",
        params={"since": "2000-01-01", "until": "2000-01-02"},
    )
    assert empty.json()["count"] == 0
