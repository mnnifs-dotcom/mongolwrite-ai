from __future__ import annotations

from app.engine import metrics


def test_mark_ready_clears_boot_spikes() -> None:
    metrics._samples.clear()
    metrics._ready = False
    metrics._heal_scheduled = False
    metrics._on_heal = None
    metrics.record(9000)
    metrics.record(8500)
    before = metrics.snapshot()
    assert before["status"] == "starting"
    assert "юу ч дарах хэрэггүй" in before["advice"]
    metrics.mark_ready(warmup_ms=400)
    after = metrics.snapshot()
    assert after["ready"] is True
    assert after["status"] == "ready"
    assert after["outlier_24h"] == 0
    assert "юу ч дарах хэрэггүй" in after["advice"]


def test_ready_spike_schedules_auto_heal() -> None:
    metrics._samples.clear()
    metrics._ready = True
    metrics._heal_scheduled = False
    called: list[bool] = []
    metrics.set_heal_handler(lambda: called.append(True))
    metrics.record(120)
    metrics.record(9500)
    snap = metrics.snapshot()
    # Spike must not flip status to a scary warning that needs an admin click.
    assert snap["status"] == "ready"
    assert snap["checks_24h"] == 1
    # Give the heal thread a moment.
    import time

    for _ in range(20):
        if called:
            break
        time.sleep(0.05)
    assert called
