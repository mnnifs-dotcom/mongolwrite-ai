from __future__ import annotations

import io
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core import chimege
from app.main import app


def _silent_wav(seconds: float = 1.0, rate: int = 16_000) -> bytes:
    buf = io.BytesIO()
    frames = int(rate * seconds)
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * frames)
    return buf.getvalue()


@pytest.fixture(autouse=True)
def _isolate_chimege(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    persist = tmp_path / "persist"
    persist.mkdir()
    monkeypatch.setattr(chimege, "persist_dir", lambda: persist)
    monkeypatch.setattr(chimege, "_token_path", lambda: tmp_path / ".chimege_token")
    monkeypatch.setattr(chimege.settings, "chimege_api_token", "")
    yield


def test_public_status_disabled_by_default():
    client = TestClient(app)
    response = client.get("/api/v1/stt/status")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["price_mnt_per_hour"] == 7000


def test_admin_sets_token_and_prepaid():
    snap = chimege.update_admin(token="abc123tokenXYZ", set_prepaid_seconds=7200)
    assert snap["has_token"] is True
    assert snap["remaining_hours"] == pytest.approx(2.0)
    assert "…" in snap["token_masked"]

    status = chimege.public_status()
    assert status["enabled"] is True
    assert status["remaining_seconds"] == pytest.approx(7200)


def test_usage_deducts_at_7000_per_hour():
    chimege.update_admin(token="tok", set_prepaid_seconds=3600)
    usage = chimege.reserve_and_record_usage(
        duration_seconds=1800,
        filename="talk.wav",
        chimege_uuid="u-1",
    )
    assert usage["mnt"] == pytest.approx(3500.0)
    assert usage["remaining_seconds"] == pytest.approx(1800.0)


def test_insufficient_prepaid_raises():
    chimege.update_admin(token="tok", set_prepaid_seconds=10)
    with pytest.raises(ValueError):
        chimege.reserve_and_record_usage(duration_seconds=60, filename="x.wav")


def test_transcribe_proxies_without_saving_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    chimege.update_admin(token="test-token", set_prepaid_seconds=3600)

    def fake_submit(audio: bytes, token: str):
        assert token == "test-token"
        assert len(audio) > 1000
        return {"uuid": "job-1", "duration": 12.5}

    monkeypatch.setattr("app.api.routes_stt.submit_long", fake_submit)
    client = TestClient(app)
    wav = _silent_wav(1.0)
    response = client.post(
        "/api/v1/stt/transcribe",
        files={"file": ("sample.wav", wav, "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["uuid"] == "job-1"
    assert body["duration_seconds"] == 12.5
    assert body["mnt"] == pytest.approx(round((12.5 / 3600) * 7000, 2))
    # No audio file should appear under persist.
    persist_files = list((tmp_path / "persist").rglob("*"))
    assert not any(p.suffix.lower() in {".wav", ".mp3", ".m4a"} for p in persist_files)


def test_poll_result(monkeypatch: pytest.MonkeyPatch):
    chimege.update_admin(token="test-token", set_prepaid_seconds=100)

    def fake_fetch(uuid: str, token: str):
        assert uuid == "job-9"
        return {"done": True, "transcription": "сайн байна уу", "duration": 3.0}

    monkeypatch.setattr("app.api.routes_stt.fetch_transcript", fake_fetch)
    client = TestClient(app)
    response = client.get("/api/v1/stt/result", params={"uuid": "job-9"})
    assert response.status_code == 200
    assert response.json()["transcription"] == "сайн байна уу"
