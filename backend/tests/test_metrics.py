from __future__ import annotations

from app.engine import metrics


def test_mark_ready_clears_cold_outliers() -> None:
    metrics._samples.clear()
    metrics._ready = False
    metrics.record(9000)
    metrics.record(8500)
    metrics.record(120)
    before = metrics.snapshot()
    assert before["outlier_24h"] >= 2
    assert before["status"] == "starting"
    metrics.mark_ready(warmup_ms=400)
    after = metrics.snapshot()
    assert after["ready"] is True
    assert after["status"] == "ready"
    assert after["outlier_24h"] == 0
    assert "бэлэн" in after["advice"].casefold()
