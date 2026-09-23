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


def test_missing_word_harvested_and_added_to_lexicon(monkeypatch, tmp_path) -> None:
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

    # Invented word — not in curated lexicon; should still be harvested as doubt.
    coined = "хязгаарлагдмалтэстүг"
    harvest = client.post(
        "/api/v1/admin/candidates/harvest",
        json={"text": f"Энэ {coined} үгийг шалгана."},
    )
    assert harvest.status_code == 200
    items = client.get("/api/v1/admin/candidates").json()["items"]
    folded = {row["folded"] for row in items}
    assert coined in folded

    approved = client.post("/api/v1/admin/candidates/approve", json={"words": [coined]})
    assert approved.status_code == 200
    body = approved.json()
    assert body["added_count"] >= 1 or body.get("recorded_count", 0) >= 1

    from app.engine.runtime import get_engine

    assert get_engine().dictionary.in_seed(coined)
    assert coined in user_dict.read_text(encoding="utf-8")

    overview = client.get("/api/v1/admin/overview").json()
    assert "reliable_items" in overview["candidates"] or "doubt_items" in overview["candidates"]
    assert any(row["folded"] == coined for row in overview.get("added_words") or [])

    added = client.get("/api/v1/admin/added-words").json()
    assert added["count"] >= 1
    assert added["items"][0]["folded"] == coined

    # Second approval of another word appears first (newest first).
    second = "хоёрдахьтэстүг"
    client.post("/api/v1/admin/candidates/harvest", json={"text": second})
    client.post("/api/v1/admin/candidates/approve", json={"words": [second]})
    ordered = client.get("/api/v1/admin/added-words").json()["items"]
    assert ordered[0]["folded"] == second
    assert ordered[1]["folded"] == coined


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


def test_clear_orthography_errors_not_harvested(monkeypatch, tmp_path) -> None:
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

    # Clear rule misses — must NOT enter Hunspell admin queue.
    clear_errors = "ажиллажбайна үзэжбайна ягаад байхгуй өдрээс"
    client.post("/api/v1/admin/candidates/harvest", json={"text": clear_errors})
    folded = {
        row["folded"] for row in client.get("/api/v1/admin/candidates").json()["items"]
    }
    for word in ("ажиллажбайна", "үзэжбайна", "ягаад", "байхгуй"):
        assert word not in folded

    # Invented gap word should still be queued for admin judgment.
    coined = "эргэлзээтэйтэстүг"
    client.post("/api/v1/admin/candidates/harvest", json={"text": coined})
    folded = {
        row["folded"] for row in client.get("/api/v1/admin/candidates").json()["items"]
    }
    assert coined in folded


def test_obvious_junk_not_harvested_or_listed(monkeypatch, tmp_path) -> None:
    persist = tmp_path / "persist"
    persist.mkdir()
    user_dict = tmp_path / "user_dictionary.txt"
    user_dict.write_text("", encoding="utf-8")
    monkeypatch.setattr("app.engine.dictionary.user_dictionary_path", lambda: user_dict)
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)

    import app.engine.runtime as runtime

    runtime._engine = None

    from app.engine.hunspell_candidates import is_obvious_junk, prune_clear_error_candidates

    junk = ["ррүү", "үоүоүүрхг", "рр", "ррү", "рш", "ршрү"]
    for word in junk:
        assert is_obvious_junk(word), word

    # Real-looking coined word should NOT be junk.
    assert not is_obvious_junk("эргэлзээтэйтэстүг")

    client = TestClient(app)
    _login(client, monkeypatch, persist)

    client.post(
        "/api/v1/admin/candidates/harvest",
        json={"text": " ".join(junk) + " эргэлзээтэйтэстүг"},
    )
    folded = {
        row["folded"] for row in client.get("/api/v1/admin/candidates").json()["items"]
    }
    for word in junk:
        assert word not in folded
    assert "эргэлзээтэйтэстүг" in folded

    # Pre-seed the queue with junk (simulates old data) — prune must drop it.
    import json

    path = persist / "hunspell_candidates.json"
    path.write_text(
        json.dumps(
            {
                "words": [
                    {
                        "word": "ррүү",
                        "folded": "ррүү",
                        "tier": "doubt",
                        "reason": "old",
                        "suggestion": "",
                        "count": 31,
                        "seen_at": "2026-01-01T00:00:00+00:00",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    },
                    {
                        "word": "үоүоүүрхг",
                        "folded": "үоүоүүрхг",
                        "tier": "doubt",
                        "reason": "old",
                        "suggestion": "",
                        "count": 21,
                        "seen_at": "2026-01-01T00:00:00+00:00",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    },
                    {
                        "word": "эргэлзээтэйтэстүг",
                        "folded": "эргэлзээтэйтэстүг",
                        "tier": "doubt",
                        "reason": "keep",
                        "suggestion": "",
                        "count": 1,
                        "seen_at": "2026-01-01T00:00:00+00:00",
                        "updated_at": "2026-01-01T00:00:00+00:00",
                    },
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    removed = prune_clear_error_candidates()
    assert removed >= 2
    overview = client.get("/api/v1/admin/overview").json()
    doubt_folded = {row["folded"] for row in overview["candidates"].get("doubt_items") or []}
    assert "ррүү" not in doubt_folded
    assert "үоүоүүрхг" not in doubt_folded
    assert "эргэлзээтэйтэстүг" in doubt_folded


def test_typing_prefixes_of_known_lemmas_are_not_candidates() -> None:
    """«сургуу» while typing «сургууль» must never enter the review queue."""
    from app.engine.dictionary import DictionaryProvider
    from app.engine.hunspell_candidates import classify_candidate, extract_missing_words
    from app.engine.pipeline import LanguageEngine

    dictionary = DictionaryProvider(frozenset({"сургууль", "аав"}))
    engine = LanguageEngine(dictionary)

    for fragment in ("су", "сур", "сургу", "сургуу", "сургуул"):
        assert dictionary.is_proper_prefix_of_known(fragment), fragment
        assert classify_candidate(dictionary, fragment) is None, fragment

    # Full curated lemma is not a "typing prefix" of its own case expansions.
    assert not dictionary.is_proper_prefix_of_known("сургууль")
    # Progressive mid-word buffer: unfinished trailing token is skipped.
    for text in ("сур", "сургуу", "сургуул", "сургууль"):
        assert extract_missing_words(engine, text, skip_unfinished_trailing=True) == []

    # Finished lemma must not be harvested as a "missing" word.
    assert extract_missing_words(engine, "сургууль ", skip_unfinished_trailing=True) == []
    assert extract_missing_words(engine, "сургууль.") == []


def test_live_harvest_skips_unfinished_trailing_token(monkeypatch, tmp_path) -> None:
    """Check-path harvest must not queue mid-typing prefixes from progressive input."""
    persist = tmp_path / "persist"
    persist.mkdir()
    user_dict = tmp_path / "user_dictionary.txt"
    user_dict.write_text("", encoding="utf-8")
    monkeypatch.setattr("app.engine.dictionary.user_dictionary_path", lambda: user_dict)
    monkeypatch.setattr("app.engine.hunspell_candidates.persist_dir", lambda: persist)

    from app.engine.dictionary import DictionaryProvider
    from app.engine.hunspell_candidates import (
        harvest_safe,
        list_candidates,
        record_from_text,
        _flush_pending,
    )
    from app.engine.pipeline import LanguageEngine

    dictionary = DictionaryProvider(frozenset({"сургууль", "өөдөр"}))
    engine = LanguageEngine(dictionary)

    for prefix in ("сур", "сургуу", "сургуул", "сургууль"):
        harvest_safe(engine, prefix)
    _flush_pending()
    folded = {row["folded"] for row in list_candidates()}
    for junk in ("сур", "сургуу", "сургуул"):
        assert junk not in folded, junk

    # Finished sentence with a real unknown word still harvests that word.
    coined = "эргэлзээтэйтэстүг"
    record_from_text(engine, f"сургууль {coined}.", skip_unfinished_trailing=True)
    _flush_pending()
    folded = {row["folded"] for row in list_candidates()}
    assert coined in folded
    assert "сургууль" not in folded
