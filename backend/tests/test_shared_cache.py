from __future__ import annotations

from app.core import shared_cache
from app.engine.dictionary import DictionaryProvider
from app.engine.metrics import snapshot
from app.engine.runtime import run_engine_check


def test_shared_cache_memory_fallback(monkeypatch) -> None:
    shared_cache.reset_for_tests()
    monkeypatch.setattr("app.core.shared_cache.settings.redis_url", "")
    assert shared_cache.get_hunspell_membership("тест") is None
    shared_cache.set_hunspell_membership("тест", True)  # no-op without Redis
    stats = shared_cache.cache_stats()
    assert stats["enabled"] is False
    assert stats["connected"] is False
    assert stats["backend"] == "memory"


def test_contains_records_l1_hits(monkeypatch) -> None:
    shared_cache.reset_for_tests()
    monkeypatch.setattr("app.core.shared_cache.settings.redis_url", "")
    d = DictionaryProvider(frozenset({"монгол"}), use_hunspell=False, frequency={})
    assert d.contains("монгол")
    # Second call on an unknown form with no hunspell stays False after probe.
    assert not d.contains("xyzzyqq")
    assert not d.contains("xyzzyqq")
    stats = shared_cache.cache_stats()
    assert stats["l1_hits"] >= 1


def test_metrics_snapshot_includes_cache() -> None:
    snap = snapshot()
    assert "cache" in snap
    assert "hit_pct" in snap["cache"]
    assert snap["check_concurrency"] >= 1


def test_concurrent_check_still_works() -> None:
    found = run_engine_check("Сайн байна уу", "government_official")
    assert isinstance(found, list)
