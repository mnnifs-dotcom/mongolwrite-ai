from __future__ import annotations

from app.core import qpay as qpay_mod
from app.core.billing import create_checkout, find_order_by_qpay_invoice_id, sync_order_payment
from app.core.users import upsert_google_user
from app.main import app
from fastapi.testclient import TestClient


def test_token_expiry_accepts_unix_timestamp(monkeypatch) -> None:
    """QPay email: expires_in may be an absolute unix timestamp."""
    monkeypatch.setattr("app.core.config.settings.qpay_client_id", "merchant")
    monkeypatch.setattr("app.core.config.settings.qpay_client_secret", "secret")
    qpay_mod._clear_token()

    class FakeResponse:
        status_code = 200
        text = ""

        def json(self):
            return {"access_token": "tok-ts", "expires_in": 1_900_000_000}

    monkeypatch.setattr(qpay_mod.httpx, "post", lambda *a, **k: FakeResponse())
    token = qpay_mod.get_access_token()
    assert token == "tok-ts"
    assert qpay_mod._token_expires_at == 1_900_000_000.0


def test_qpay_create_invoice_and_check(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.config.settings.qpay_client_id", "merchant")
    monkeypatch.setattr("app.core.config.settings.qpay_client_secret", "secret")
    monkeypatch.setattr("app.core.config.settings.qpay_invoice_code", "MW_INVOICE")
    monkeypatch.setattr(
        "app.core.config.settings.qpay_base_url",
        "https://merchant-sandbox.qpay.mn/v2",
    )
    monkeypatch.setattr(
        "app.core.config.settings.qpay_callback_url",
        "https://mongolwrite.com/api/v1/billing/qpay/callback",
    )
    qpay_mod._clear_token()

    calls: list[str] = []

    class FakeResponse:
        def __init__(self, status_code: int, payload: dict):
            self.status_code = status_code
            self._payload = payload
            self.text = str(payload)

        def json(self):
            return self._payload

    def fake_post(url, *args, **kwargs):
        calls.append(url)
        if url.endswith("/auth/token"):
            return FakeResponse(200, {"access_token": "tok-1", "expires_in": 3600})
        if url.endswith("/invoice"):
            body = kwargs.get("json") or {}
            assert body["invoice_code"] == "MW_INVOICE"
            assert body["callback_url"].endswith("/api/v1/billing/qpay/callback")
            assert body["amount"] == 6000.0
            return FakeResponse(
                200,
                {
                    "invoice_id": "inv-abc",
                    "qr_text": "QRDATA",
                    "qr_image": "aaa",
                    "qPay_shortUrl": "https://qpay.mn/s/x",
                    "urls": [{"name": "Khan bank", "link": "khanbank://pay"}],
                },
            )
        if url.endswith("/payment/check"):
            return FakeResponse(
                200,
                {
                    "count": 1,
                    "paid_amount": 6000,
                    "rows": [{"payment_id": "pay-1"}],
                },
            )
        raise AssertionError(url)

    monkeypatch.setattr(qpay_mod.httpx, "post", fake_post)

    invoice = qpay_mod.create_invoice(
        sender_invoice_no="MW-TEST",
        amount_mnt=6000,
        description="MongolWrite · 3 сар",
    )
    assert invoice["invoice_id"] == "inv-abc"
    assert invoice["qr_text"] == "QRDATA"
    assert invoice["short_url"] == "https://qpay.mn/s/x"

    checked = qpay_mod.check_invoice_paid("inv-abc")
    assert checked["paid"] is True
    assert checked["payment_id"] == "pay-1"
    assert any("/auth/token" in u for u in calls)
    assert any("/invoice" in u for u in calls)


def test_checkout_creates_live_invoice(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.billing.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.config.settings.qpay_client_id", "merchant")
    monkeypatch.setattr("app.core.config.settings.qpay_client_secret", "secret")
    monkeypatch.setattr("app.core.config.settings.qpay_invoice_code", "MW_INVOICE")
    monkeypatch.setattr(
        "app.core.billing.create_invoice",
        lambda **kwargs: {
            "invoice_id": "inv-live-1",
            "qr_text": "QR",
            "qr_image": "img",
            "short_url": "https://qpay.mn/s/1",
            "urls": [{"name": "Golomt", "link": "golomt://x"}],
        },
    )
    upsert_google_user(sub="u-qpay", email="q@example.com")
    result = create_checkout(user_id="u-qpay", email="q@example.com", plan_id="pro_3m")
    order = result["order"]
    assert order["status"] == "awaiting_payment"
    assert order["qpay_invoice_id"] == "inv-live-1"
    assert order["qpay_qr_image"] == "img"
    assert result["checkout_ready"] is True


def test_callback_verifies_before_activate(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.billing.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.config.settings.qpay_client_id", "merchant")
    monkeypatch.setattr("app.core.config.settings.qpay_client_secret", "secret")
    monkeypatch.setattr("app.core.config.settings.qpay_invoice_code", "MW_INVOICE")
    monkeypatch.setattr(
        "app.core.billing.create_invoice",
        lambda **kwargs: {
            "invoice_id": "inv-cb-1",
            "qr_text": None,
            "qr_image": None,
            "short_url": None,
            "urls": [],
        },
    )
    upsert_google_user(sub="u-cb", email="cb@example.com")
    created = create_checkout(user_id="u-cb", email="cb@example.com", plan_id="pro_year")
    order_id = created["order"]["id"]

    monkeypatch.setattr(
        "app.api.routes_billing.check_invoice_paid",
        lambda invoice_id: {
            "paid": True,
            "count": 1,
            "paid_amount": 19900,
            "payment_id": "pay-cb",
            "rows": [],
        },
    )
    client = TestClient(app)
    response = client.post(
        "/api/v1/billing/qpay/callback",
        json={"invoice_id": "inv-cb-1"},
    )
    assert response.status_code == 200
    assert response.json()["order"]["status"] == "paid"

    from app.core.users import get_user, plan_is_active

    row = get_user("u-cb")
    assert row is not None
    assert plan_is_active(row)

    found = find_order_by_qpay_invoice_id("inv-cb-1")
    assert found is not None
    assert found["id"] == order_id


def test_sync_order_payment(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr("app.core.billing.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.config.settings.qpay_client_id", "merchant")
    monkeypatch.setattr("app.core.config.settings.qpay_client_secret", "secret")
    monkeypatch.setattr("app.core.config.settings.qpay_invoice_code", "MW_INVOICE")
    monkeypatch.setattr(
        "app.core.billing.create_invoice",
        lambda **kwargs: {
            "invoice_id": "inv-sync",
            "qr_text": None,
            "qr_image": None,
            "short_url": None,
            "urls": [],
        },
    )
    upsert_google_user(sub="u-sync", email="s@example.com")
    created = create_checkout(user_id="u-sync", email="s@example.com", plan_id="pro_3m")
    order = created["order"]
    # Rebuild full order dict for sync
    from app.core.billing import get_order

    full = get_order(order["id"])
    assert full is not None
    monkeypatch.setattr(
        "app.core.billing.check_invoice_paid",
        lambda invoice_id: {"paid": True, "payment_id": "p1", "count": 1, "paid_amount": 6000},
    )
    synced = sync_order_payment(full)
    assert synced["status"] == "paid"
