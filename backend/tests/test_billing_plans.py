from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.billing import create_checkout, mark_order_paid, qpay_configured
from app.core.plans import get_plan, list_paid_plans, list_plans
from app.core.users import activate_plan_for_user, plan_is_active, public_user, upsert_google_user
from app.main import app


def test_plans_catalog() -> None:
    plans = list_plans()
    assert {row["id"] for row in plans} == {"free", "pro_3m", "pro_year"}
    assert get_plan("free")["check_max_chars"] == 1_000_000
    assert get_plan("pro_3m")["price_mnt"] == 6_000
    assert get_plan("pro_3m")["check_max_chars"] == 1_000_000
    assert get_plan("pro_year")["price_mnt"] == 19_900
    assert get_plan("pro")["id"] == "pro_year"  # legacy alias
    paid = list_paid_plans()
    assert [row["id"] for row in paid] == ["pro_3m", "pro_year"]


def test_settings_exposes_million_char_ceiling() -> None:
    client = TestClient(app)
    settings = client.get("/api/v1/settings")
    assert settings.status_code == 200
    assert settings.json()["check_max_chars"] == 1_000_000

    ok = client.post(
        "/api/v1/check/deterministic",
        json={"text": "сайн байна уу", "document_type": "general", "style": "government_official"},
    )
    assert ok.status_code == 200


def test_billing_plans_endpoint() -> None:
    client = TestClient(app)
    response = client.get("/api/v1/billing/plans")
    assert response.status_code == 200
    body = response.json()
    assert body["currency"] == "MNT"
    assert body["provider"] == "qpay"
    assert body["checkout_ready"] is False
    ids = {row["id"] for row in body["plans"]}
    assert ids == {"pro_3m", "pro_year"}


def test_checkout_requires_login(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.billing.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    client = TestClient(app)
    denied = client.post("/api/v1/billing/checkout", json={"plan_id": "pro_year"})
    assert denied.status_code in {401, 403}


def test_checkout_and_callback_activates_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.billing.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    monkeypatch.setattr("app.core.config.settings.qpay_client_id", "")
    monkeypatch.setattr("app.core.config.settings.qpay_client_secret", "")
    monkeypatch.setattr("app.core.config.settings.qpay_invoice_code", "")
    assert qpay_configured() is False

    user = upsert_google_user(sub="pay1", email="pay@example.com", name="Pay")
    assert public_user(user)["plan"] == "free"

    result = create_checkout(user_id="pay1", email="pay@example.com", plan_id="pro_3m")
    order = result["order"]
    assert order["amount_mnt"] == 6_000
    assert order["plan_id"] == "pro_3m"
    assert order["status"] in {"pending_provider", "pending", "awaiting_qpay"}

    paid = mark_order_paid(order["id"], qpay_payment_id="test-pay")
    assert paid is not None
    assert paid["status"] == "paid"

    from app.core.users import get_user

    row = get_user("pay1")
    assert row is not None
    assert plan_is_active(row)
    assert public_user(row)["plan"] == "pro_3m"
    assert public_user(row)["is_paid"] is True


def test_activate_year_plan(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("app.core.users.persist_dir", lambda: tmp_path)
    upsert_google_user(sub="y1", email="y@example.com")
    row = activate_plan_for_user("y1", "pro_year")
    assert row is not None
    assert plan_is_active(row)
    assert public_user(row)["plan"] == "pro_year"
