from __future__ import annotations

from app.engine import pending


def test_pop_pending_many(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.engine.pending.persist_dir", lambda: tmp_path)
    assert pending.record_skip("авлагын")
    assert pending.record_skip("амаржаны")
    assert pending.record_skip("амьтнаас")
    assert len(pending.list_pending()) == 3

    popped = pending.pop_pending_many(["авлагын", "амьтнаас", "байхгүй"])
    assert {item["folded"] for item in popped} == {"авлагын", "амьтнаас"}
    remaining = {item["folded"] for item in pending.list_pending()}
    assert remaining == {"амаржаны"}

    empty = pending.pop_pending_many([])
    assert empty == []
