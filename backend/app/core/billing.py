"""Payment orders + QPay-ready checkout (secrets wired later)."""

from __future__ import annotations

import json
import secrets
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.plans import get_plan, is_paid_plan, list_paid_plans
from app.core.users import activate_plan_for_user
from app.engine.dictionary import persist_dir

_lock = threading.Lock()


def _orders_path() -> Path:
    return persist_dir() / "billing_orders.json"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(stamp: datetime) -> str:
    return stamp.astimezone(timezone.utc).isoformat()


def _load_orders() -> dict[str, dict[str, Any]]:
    path = _orders_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    items = raw.get("orders") if isinstance(raw, dict) else None
    if not isinstance(items, dict):
        return {}
    return {str(key): value for key, value in items.items() if isinstance(value, dict)}


def _save_orders(orders: dict[str, dict[str, Any]]) -> None:
    path = _orders_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep newest ~2000 orders.
    if len(orders) > 2000:
        ranked = sorted(
            orders.items(),
            key=lambda pair: str(pair[1].get("created_at") or ""),
            reverse=True,
        )[:2000]
        orders = dict(ranked)
    path.write_text(
        json.dumps({"orders": orders}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def qpay_configured() -> bool:
    """True when QPay credentials are present (ready to call live API)."""
    return bool(
        settings.qpay_client_id.strip()
        and settings.qpay_client_secret.strip()
        and settings.qpay_invoice_code.strip()
    )


def billing_public_status() -> dict[str, Any]:
    return {
        "plans": list_paid_plans(),
        "all_plans": [
            get_plan("free"),
            *list_paid_plans(),
        ],
        "currency": "MNT",
        "provider": "qpay",
        "checkout_ready": qpay_configured(),
        "message": (
            "QPay холбогдсон — төлбөр хийх боломжтой."
            if qpay_configured()
            else "QPay код оруулсны дараа төлбөр идэвхжинэ. Одоогоор багцууд бэлэн."
        ),
    }


def create_checkout(
    *,
    user_id: str,
    email: str,
    plan_id: str,
) -> dict[str, Any]:
    plan = get_plan(plan_id)
    if not is_paid_plan(plan["id"]):
        raise ValueError("Зөвхөн төлбөртэй багц сонгоно")
    order_id = str(uuid.uuid4())
    sender_invoice_no = f"MW-{secrets.token_hex(4).upper()}"
    stamped = _now()
    order = {
        "id": order_id,
        "sender_invoice_no": sender_invoice_no,
        "user_id": user_id,
        "email": email,
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "amount_mnt": int(plan["price_mnt"]),
        "duration_days": plan.get("duration_days"),
        "currency": "MNT",
        "provider": "qpay",
        "status": "pending",
        "qpay_invoice_id": None,
        "qpay_qr_text": None,
        "qpay_urls": [],
        "created_at": _iso(stamped),
        "updated_at": _iso(stamped),
        "paid_at": None,
        "expires_at": _iso(stamped + timedelta(hours=2)),
    }

    # Live QPay call lands here once credentials are set.
    # Until then we return a structured pending order the UI can render.
    if qpay_configured():
        order["status"] = "awaiting_qpay"
        order["note"] = "QPay invoice create — credentials present; wire API next."
    else:
        order["status"] = "pending_provider"
        order["note"] = "QPay код хүлээгдэж байна. Захиалга бүртгэгдлээ."

    with _lock:
        orders = _load_orders()
        orders[order_id] = order
        _save_orders(orders)

    return {
        "ok": True,
        "order": public_order(order),
        "checkout_ready": qpay_configured(),
        "provider": "qpay",
    }


def public_order(order: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": order.get("id"),
        "sender_invoice_no": order.get("sender_invoice_no"),
        "plan_id": order.get("plan_id"),
        "plan_name": order.get("plan_name"),
        "amount_mnt": order.get("amount_mnt"),
        "currency": order.get("currency", "MNT"),
        "status": order.get("status"),
        "qpay_qr_text": order.get("qpay_qr_text"),
        "qpay_urls": order.get("qpay_urls") or [],
        "created_at": order.get("created_at"),
        "expires_at": order.get("expires_at"),
        "note": order.get("note") or "",
    }


def get_order(order_id: str) -> dict[str, Any] | None:
    with _lock:
        row = _load_orders().get(order_id)
        return dict(row) if row else None


def find_order_by_invoice_no(sender_invoice_no: str) -> dict[str, Any] | None:
    needle = (sender_invoice_no or "").strip()
    if not needle:
        return None
    with _lock:
        for row in _load_orders().values():
            if str(row.get("sender_invoice_no")) == needle:
                return dict(row)
    return None


def mark_order_paid(order_id: str, *, qpay_payment_id: str = "") -> dict[str, Any] | None:
    """Mark invoice paid and activate the user plan (QPay callback / manual)."""
    with _lock:
        orders = _load_orders()
        order = orders.get(order_id)
        if not order:
            return None
        if order.get("status") == "paid":
            return dict(order)
        stamped = _iso(_now())
        order["status"] = "paid"
        order["paid_at"] = stamped
        order["updated_at"] = stamped
        if qpay_payment_id:
            order["qpay_payment_id"] = qpay_payment_id
        orders[order_id] = order
        _save_orders(orders)
        snapshot = dict(order)

    activate_plan_for_user(
        str(snapshot["user_id"]),
        str(snapshot["plan_id"]),
        duration_days=int(snapshot.get("duration_days") or 0) or None,
    )
    return snapshot


def list_orders_for_user(user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        rows = [dict(row) for row in _load_orders().values() if str(row.get("user_id")) == user_id]
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return [public_order(row) for row in rows[: max(1, min(limit, 100))]]
