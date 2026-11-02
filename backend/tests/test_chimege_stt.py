from __future__ import annotations

import io
import wave
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.responses import Response

from app.core import billing, chimege
from app.core import stt_history
from app.core import users as users_mod
from app.core.user_auth import set_user_cookie
from app.core.users import upsert_google_user
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
    monkeypatch.setattr(billing, "persist_dir", lambda: persist)
    monkeypatch.setattr(users_mod, "persist_dir", lambda: persist)
    monkeypatch.setattr(stt_history, "persist_dir", lambda: persist)
    yield


def _auth_client(user_id: str = "stt-user-1", email: str = "stt@example.com") -> TestClient:
    upsert_google_user(sub=user_id, email=email, name="STT")
    client = TestClient(app)
    probe = Response()
    set_user_cookie(probe, user_id)
    cookie_header = probe.headers.get("set-cookie", "")
    token = cookie_header.split("mw_user=", 1)[1].split(";", 1)[0]
    client.cookies.set("mw_user", token)
    client.headers.update({"X-MW-Device-Id": "sttdevice01aa"})
    return client


def test_public_status_disabled_by_default():
    client = TestClient(app)
    response = client.get("/api/v1/stt/status")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["price_mnt_per_hour"] == 7000
    assert "checkout_ready" in body


def test_checkout_requires_login():
    chimege.update_admin(token="test-token", set_prepaid_seconds=3600)
    client = TestClient(app)
    response = client.post(
        "/api/v1/stt/checkout",
        json={"duration_seconds": 60, "filename": "a.wav"},
    )
    assert response.status_code == 401


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


def _paid_stt_order(
    *,
    duration_seconds: float = 12.5,
    user_id: str = "stt-user-1",
    email: str = "stt@example.com",
) -> tuple[str, str]:
    created = billing.create_stt_checkout(
        duration_seconds=duration_seconds,
        filename="sample.wav",
        price_mnt_per_hour=7000,
        user_id=user_id,
        email=email,
    )
    order = created["order"]
    token = str(order["access_token"])
    paid = billing.mark_order_paid(str(order["id"]), qpay_payment_id="test-stt")
    assert paid is not None
    assert paid["status"] == "paid"
    assert paid.get("product_kind") == "stt"
    return str(order["id"]), token


def test_transcribe_requires_login(monkeypatch: pytest.MonkeyPatch):
    chimege.update_admin(token="test-token", set_prepaid_seconds=3600)
    monkeypatch.setattr(
        "app.core.stt_jobs.submit_long",
        lambda audio, token: {"uuid": "job-1", "duration": 12.5},
    )
    client = TestClient(app)
    wav = _silent_wav(1.0)
    response = client.post(
        "/api/v1/stt/transcribe",
        files={"file": ("sample.wav", wav, "audio/wav")},
    )
    assert response.status_code == 401


def test_transcribe_requires_payment(monkeypatch: pytest.MonkeyPatch):
    chimege.update_admin(token="test-token", set_prepaid_seconds=3600)
    monkeypatch.setattr(
        "app.core.stt_jobs.submit_long",
        lambda audio, token: {"uuid": "job-1", "duration": 12.5},
    )
    client = _auth_client()
    wav = _silent_wav(1.0)
    response = client.post(
        "/api/v1/stt/transcribe",
        files={"file": ("sample.wav", wav, "audio/wav")},
    )
    assert response.status_code == 402


def test_transcribe_proxies_without_saving_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    chimege.update_admin(token="test-token", set_prepaid_seconds=3600)

    def fake_submit(audio: bytes, token: str):
        assert token == "test-token"
        assert len(audio) > 1000
        return {"uuid": "job-1", "duration": 12.5}

    # Background job calls submit_long from stt_jobs (not routes_stt).
    monkeypatch.setattr("app.core.stt_jobs.submit_long", fake_submit)
    order_id, access_token = _paid_stt_order(duration_seconds=12.5)
    client = _auth_client()
    wav = _silent_wav(1.0)
    response = client.post(
        "/api/v1/stt/transcribe",
        data={"order_id": order_id, "access_token": access_token},
        files={"file": ("sample.wav", wav, "audio/wav")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["pending"] is True
    assert body["uuid"].startswith("pending:")
    assert body["order_id"] == order_id
    # Amount is the prepaid QPay quote (1 minute minimum at 7000/hr ≈ 117).
    assert body["mnt"] == 117
    persist_files = list((tmp_path / "persist").rglob("*"))
    assert not any(p.suffix.lower() in {".wav", ".mp3", ".m4a"} for p in persist_files)

    # Wait for background Chimege submit to bind the real UUID.
    import time

    from app.core import billing as billing_mod
    from app.core import stt_jobs

    deadline = time.time() + 5
    bound = None
    while time.time() < deadline:
        bound = billing_mod.get_stt_order(order_id, access_token)
        if bound and bound.get("chimege_uuid") == "job-1":
            break
        time.sleep(0.05)
    assert bound is not None
    assert bound.get("chimege_uuid") == "job-1"

    # Polling pending uuid resolves to the Chimege job.
    monkeypatch.setattr(
        "app.api.routes_stt.fetch_transcript",
        lambda uuid, token: {"done": False, "transcription": "", "duration": 12.5},
    )
    poll = client.get(
        "/api/v1/stt/result",
        params={"uuid": body["uuid"], "order_id": order_id, "access_token": access_token},
    )
    assert poll.status_code == 200
    assert poll.json()["done"] is False
    assert poll.json()["uuid"] == "job-1"

    # Same paid order resumes the job (no second charge) until delivered.
    again = client.post(
        "/api/v1/stt/transcribe",
        data={"order_id": order_id, "access_token": access_token},
        files={"file": ("sample.wav", wav, "audio/wav")},
    )
    assert again.status_code == 200
    assert again.json()["uuid"] == "job-1"
    assert again.json()["pending"] is False

    billing_mod.complete_stt_order(
        order_id,
        access_token=access_token,
        chimege_uuid="job-1",
        transcription="сайн байна уу",
    )
    stt_jobs.discard_job(order_id)
    resumed = client.post(
        "/api/v1/stt/transcribe",
        data={"order_id": order_id, "access_token": access_token},
        files={"file": ("sample.wav", wav, "audio/wav")},
    )
    # Consumed orders with cached transcript resume delivery instead of 409.
    assert resumed.status_code == 200
    assert resumed.json()["phase"] == "delivered"
    cached = client.get(
        "/api/v1/stt/result",
        params={"uuid": "job-1", "order_id": order_id, "access_token": access_token},
    )
    assert cached.status_code == 200
    assert cached.json()["transcription"] == "сайн байна уу"
    history = client.get("/api/v1/stt/history")
    assert history.status_code == 200
    items = history.json()["items"]
    assert len(items) >= 1
    assert items[0]["preview"].startswith("сайн")


def test_checkout_quotes_by_minutes():
    chimege.update_admin(token="test-token", set_prepaid_seconds=3600)
    client = _auth_client()
    response = client.post(
        "/api/v1/stt/checkout",
        json={"duration_seconds": 125, "filename": "talk.mp3"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["billable_seconds"] == 180  # ceil 125s → 3 min
    assert body["amount_mnt"] == 350  # 3/60 * 7000
    assert body["order"]["access_token"]
    assert body["order"]["product_kind"] == "stt"
    assert body["order"]["id"]


def test_poll_result(monkeypatch: pytest.MonkeyPatch):
    chimege.update_admin(token="test-token", set_prepaid_seconds=100)

    def fake_fetch(uuid: str, token: str):
        assert uuid == "job-9"
        return {"done": True, "transcription": "сайн байна уу", "duration": 3.0}

    monkeypatch.setattr("app.api.routes_stt.fetch_transcript", fake_fetch)
    client = _auth_client()
    response = client.get("/api/v1/stt/result", params={"uuid": "job-9"})
    assert response.status_code == 200
    assert response.json()["transcription"] == "сайн байна уу"
    assert response.json()["progress_percent"] == 100


def test_normalize_transcription_rejoins_hyphen_linebreaks():
    from app.core.chimege_client import normalize_transcription

    raw = "Сайн бай\u00adна уу та бүхэн-\nтэй уулзлаа"
    assert normalize_transcription(raw) == "Сайн байна уу та бүхэнтэй уулзлаа"


def test_new_token_queues_until_previous_seconds_finish(monkeypatch: pytest.MonkeyPatch):
    chimege.update_admin(token="trial-token-aaaa", set_prepaid_seconds=3600)
    assert chimege.get_api_token() == "trial-token-aaaa"
    assert chimege.remaining_seconds() == pytest.approx(3600)

    snap = chimege.update_admin(token="paid-token-bbbb", set_prepaid_seconds=7200)
    assert chimege.get_api_token() == "trial-token-aaaa"
    assert snap["queued_count"] >= 1
    assert chimege.remaining_seconds() == pytest.approx(3600 + 7200)

    chimege.reserve_and_record_usage(duration_seconds=3599, filename="a.wav")
    assert chimege.get_api_token() == "trial-token-aaaa"
    assert chimege.active_remaining_seconds() == pytest.approx(1.0)

    chimege.reserve_and_record_usage(duration_seconds=1, filename="b.wav")
    assert chimege.get_api_token() == "paid-token-bbbb"
    assert chimege.active_remaining_seconds() == pytest.approx(7200)


def test_cannot_skip_active_leftover_for_longer_file():
    chimege.update_admin(token="trial-token-aaaa", set_prepaid_seconds=30)
    chimege.update_admin(token="paid-token-bbbb", set_prepaid_seconds=3600)
    with pytest.raises(ValueError, match="Идэвхтэй API"):
        chimege.reserve_and_record_usage(duration_seconds=60, filename="long.wav")
    assert chimege.get_api_token() == "trial-token-aaaa"


def test_activate_next_wastes_active_leftover():
    chimege.update_admin(token="trial-token-aaaa", set_prepaid_seconds=30)
    chimege.update_admin(token="paid-token-bbbb", set_prepaid_seconds=3600)
    assert chimege.get_api_token() == "trial-token-aaaa"
    snap = chimege.activate_next_slot(waste_active_leftover=True)
    assert chimege.get_api_token() == "paid-token-bbbb"
    assert snap["active_remaining_seconds"] == pytest.approx(3600)


def test_topup_existing_slot_by_index():
    chimege.update_admin(token="trial-token-aaaa", set_prepaid_seconds=1000)
    before = chimege.active_remaining_seconds()
    snap = chimege.update_admin(slot_index=0, add_prepaid_seconds=3600)
    assert snap["active_remaining_seconds"] == pytest.approx(before + 3600)
    assert chimege.get_api_token() == "trial-token-aaaa"


def test_checkout_rejects_over_active_remaining(monkeypatch: pytest.MonkeyPatch):
    chimege.update_admin(token="trial-token-aaaa", set_prepaid_seconds=30)
    chimege.update_admin(token="paid-token-bbbb", set_prepaid_seconds=3600)
    client = _auth_client()
    response = client.post(
        "/api/v1/stt/checkout",
        json={"duration_seconds": 3000, "filename": "long.m4a"},
    )
    assert response.status_code == 400
    assert "30" in response.json()["detail"] or "үлдсэн" in response.json()["detail"].lower()


def test_stt_payment_does_not_activate_plan(tmp_path, monkeypatch):
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    from app.core.users import get_user, upsert_google_user

    user = upsert_google_user(sub="stt-pay", email="stt@example.com", name="STT")
    before_plan = user.get("plan")
    before_expires = user.get("plan_expires_at")
    created = billing.create_stt_checkout(
        duration_seconds=60,
        user_id=str(user["id"]),
        email="stt@example.com",
        filename="a.wav",
        price_mnt_per_hour=7000,
    )
    billing.mark_order_paid(created["order"]["id"], qpay_payment_id="x")
    refreshed = get_user(str(user["id"]))
    assert refreshed is not None
    assert refreshed.get("plan") == before_plan
    assert refreshed.get("plan_expires_at") == before_expires
    assert refreshed.get("plan") not in {"pro_3m", "pro_year"}
