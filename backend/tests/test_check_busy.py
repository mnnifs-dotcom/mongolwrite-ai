from __future__ import annotations

import threading

import pytest
from fastapi.testclient import TestClient

from app.engine import runtime
from app.main import app


def test_check_busy_returns_503(monkeypatch) -> None:
    """When all slots are taken past the wait budget, API fails fast — no false empty."""

    def _busy(_text: str, _style: str):
        raise runtime.CheckBusyError("slots full")

    monkeypatch.setattr(runtime, "run_engine_check", _busy)
    # routes_check imported the symbol — patch where used.
    import app.api.routes_check as routes

    monkeypatch.setattr(routes, "run_engine_check", _busy)

    client = TestClient(app)
    response = client.post(
        "/api/v1/check/deterministic",
        json={"text": "Сайн байна уу", "style": "government_official"},
    )
    assert response.status_code == 503
    detail = response.json().get("detail", "")
    assert "зэрэг" in detail or "оролдоно" in detail


def test_semaphore_timeout_raises_busy(monkeypatch) -> None:
    monkeypatch.setattr(runtime.settings, "check_queue_wait_seconds", 0.05)
    # Drain the real semaphore so acquire times out.
    slots = max(1, int(runtime.settings.check_concurrency or 3))
    for _ in range(slots):
        assert runtime._check_slots.acquire(blocking=False)

    try:
        with pytest.raises(runtime.CheckBusyError):
            runtime.run_engine_check("Сайн", "government_official")
    finally:
        for _ in range(slots):
            runtime._check_slots.release()
