"""Payment orders + live QPay checkout."""

from __future__ import annotations

import json
import logging
import math
import secrets
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.plans import get_plan, is_purchasable_plan, list_paid_plans
from app.core.qpay import QPayError, check_invoice_paid, create_invoice
from app.core.users import activate_plan_for_user
from app.engine.dictionary import persist_dir

_lock = threading.Lock()
_log = logging.getLogger(__name__)

# Speech-to-text one-shot invoices (no plan activation).
STT_PRODUCT_KIND = "stt"
STT_MIN_BILLABLE_SECONDS = 60.0
STT_DURATION_SLACK = 1.25  # allow Chimege duration slightly over quoted length


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


def _append_event(order: dict[str, Any], kind: str, detail: str = "") -> None:
    events = order.get("events")
    if not isinstance(events, list):
        events = []
    events.append(
        {
            "at": _iso(_now()),
            "kind": kind,
            "detail": detail[:240],
        }
    )
    order["events"] = events[-50:]


def _save_orders(orders: dict[str, dict[str, Any]]) -> None:
    path = _orders_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    # Keep newest ~5000 orders for dispute / audit retention (гэрээ 6.2.6).
    if len(orders) > 5000:
        ranked = sorted(
            orders.items(),
            key=lambda pair: str(pair[1].get("created_at") or ""),
            reverse=True,
        )[:5000]
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
    from app.core.qpay import callback_url

    ready = qpay_configured()
    return {
        "plans": list_paid_plans(),
        "all_plans": [
            get_plan("free"),
            *list_paid_plans(),
        ],
        "currency": "MNT",
        "provider": "qpay",
        "checkout_ready": ready,
        "callback_url": callback_url() if ready else None,
        "message": (
            "QPay холбогдсон — QR болон банкны аппаар төлөх боломжтой."
            if ready
            else "QPay мерчантын код оруулсны дараа төлбөр идэвхжинэ. Одоогоор багцууд бэлэн."
        ),
    }


def create_checkout(
    *,
    user_id: str,
    email: str,
    plan_id: str,
) -> dict[str, Any]:
    plan = get_plan(plan_id)
    if not is_purchasable_plan(plan["id"]):
        raise ValueError("Зөвхөн төлбөртэй багц сонгоно")
    order_id = str(uuid.uuid4())
    # Docs: sender_invoice_no must be unique — never reuse.
    sender_invoice_no = f"MW-{order_id.replace('-', '').upper()[:20]}"
    stamped = _now()
    order: dict[str, Any] = {
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
        "qpay_qr_image": None,
        "qpay_short_url": None,
        "qpay_urls": [],
        "created_at": _iso(stamped),
        "updated_at": _iso(stamped),
        "paid_at": None,
        "expires_at": _iso(stamped + timedelta(hours=2)),
        "product": f"MongolWrite · {plan['name']}",
        "events": [],
    }
    _append_event(order, "created", f"plan={plan['id']} amount={plan['price_mnt']}")

    if qpay_configured():
        try:
            invoice = create_invoice(
                sender_invoice_no=sender_invoice_no,
                amount_mnt=int(plan["price_mnt"]),
                description=f"MongolWrite · {plan['name']}",
                receiver_code="terminal",
                order_id=order_id,
            )
            order["status"] = "awaiting_payment"
            order["qpay_invoice_id"] = invoice["invoice_id"]
            order["qpay_qr_text"] = invoice.get("qr_text")
            order["qpay_qr_image"] = invoice.get("qr_image")
            order["qpay_short_url"] = invoice.get("short_url")
            order["qpay_urls"] = invoice.get("urls") or []
            order["note"] = "QPay нэхэмжлэх үүссэн. QR эсвэл банкны аппаар төлнө үү."
            _append_event(order, "invoice_created", str(invoice["invoice_id"]))
        except QPayError as exc:
            _log.exception("QPay invoice create failed")
            order["status"] = "provider_error"
            order["note"] = str(exc)
            _append_event(order, "invoice_error", str(exc))
    else:
        order["status"] = "pending_provider"
        order["note"] = "QPay код хүлээгдэж байна. Захиалга бүртгэгдлээ."
        _append_event(order, "pending_provider")

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


def public_order(order: dict[str, Any], *, include_access_token: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": order.get("id"),
        "sender_invoice_no": order.get("sender_invoice_no"),
        "plan_id": order.get("plan_id"),
        "plan_name": order.get("plan_name"),
        "amount_mnt": order.get("amount_mnt"),
        "currency": order.get("currency", "MNT"),
        "status": order.get("status"),
        "product_kind": order.get("product_kind") or "plan",
        "duration_seconds": order.get("duration_seconds"),
        "consumed": bool(order.get("consumed")),
        "chimege_uuid": order.get("chimege_uuid"),
        "qpay_invoice_id": order.get("qpay_invoice_id"),
        "qpay_qr_text": order.get("qpay_qr_text"),
        "qpay_qr_image": order.get("qpay_qr_image"),
        "qpay_short_url": order.get("qpay_short_url"),
        "qpay_urls": order.get("qpay_urls") or [],
        "created_at": order.get("created_at"),
        "expires_at": order.get("expires_at"),
        "paid_at": order.get("paid_at"),
        "note": order.get("note") or "",
    }
    if include_access_token and order.get("access_token"):
        out["access_token"] = order.get("access_token")
    return out


def stt_billable_seconds(duration_seconds: float) -> float:
    """Round up to whole minutes; minimum one minute."""
    seconds = max(0.0, float(duration_seconds))
    minutes = max(1, int(math.ceil(seconds / 60.0)))
    return float(minutes * 60)


def create_stt_checkout(
    *,
    duration_seconds: float,
    user_id: str = "",
    email: str = "",
    filename: str = "",
    price_mnt_per_hour: float,
) -> dict[str, Any]:
    """Create a QPay invoice for one speech→text conversion. Pay before convert."""
    if float(duration_seconds) <= 0:
        raise ValueError("Файлын үргэлжлэх хугацаа олдсонгүй.")
    billable = stt_billable_seconds(duration_seconds)
    rate = float(price_mnt_per_hour)
    if rate <= 0:
        raise ValueError("Үнэ тохируулаагүй.")
    amount_mnt = max(1, int(round((billable / 3600.0) * rate)))
    order_id = str(uuid.uuid4())
    access_token = secrets.token_urlsafe(24)
    sender_invoice_no = f"ST-{order_id.replace('-', '').upper()[:20]}"
    stamped = _now()
    minutes = int(billable // 60)
    product = f"MongolWrite · Яриа→бичвэр · {minutes} мин"
    order: dict[str, Any] = {
        "id": order_id,
        "sender_invoice_no": sender_invoice_no,
        "user_id": (user_id or "")[:80],
        "email": (email or "")[:200],
        "plan_id": "stt",
        "plan_name": "Яриа→бичвэр",
        "product_kind": STT_PRODUCT_KIND,
        "amount_mnt": amount_mnt,
        "duration_seconds": billable,
        "quoted_duration_seconds": round(float(duration_seconds), 2),
        "filename": (filename or "")[:120],
        "access_token": access_token,
        "consumed": False,
        "chimege_uuid": None,
        "duration_days": None,
        "currency": "MNT",
        "provider": "qpay",
        "status": "pending",
        "qpay_invoice_id": None,
        "qpay_qr_text": None,
        "qpay_qr_image": None,
        "qpay_short_url": None,
        "qpay_urls": [],
        "created_at": _iso(stamped),
        "updated_at": _iso(stamped),
        "paid_at": None,
        "expires_at": _iso(stamped + timedelta(hours=2)),
        "product": product,
        "events": [],
    }
    _append_event(order, "created", f"stt seconds={billable} amount={amount_mnt}")

    if qpay_configured():
        try:
            invoice = create_invoice(
                sender_invoice_no=sender_invoice_no,
                amount_mnt=amount_mnt,
                description=product[:255],
                receiver_code="terminal",
                order_id=order_id,
            )
            order["status"] = "awaiting_payment"
            order["qpay_invoice_id"] = invoice["invoice_id"]
            order["qpay_qr_text"] = invoice.get("qr_text")
            order["qpay_qr_image"] = invoice.get("qr_image")
            order["qpay_short_url"] = invoice.get("short_url")
            order["qpay_urls"] = invoice.get("urls") or []
            order["note"] = "QPay нэхэмжлэх үүссэн. Төлсний дараа бичвэр бэлтгэнэ."
            _append_event(order, "invoice_created", str(invoice["invoice_id"]))
        except QPayError as exc:
            _log.exception("QPay STT invoice create failed")
            order["status"] = "provider_error"
            order["note"] = str(exc)
            _append_event(order, "invoice_error", str(exc))
    else:
        order["status"] = "pending_provider"
        order["note"] = "QPay код хүлээгдэж байна. Захиалга бүртгэгдлээ."
        _append_event(order, "pending_provider")

    with _lock:
        orders = _load_orders()
        orders[order_id] = order
        _save_orders(orders)

    return {
        "ok": True,
        "order": public_order(order, include_access_token=True),
        "checkout_ready": qpay_configured(),
        "provider": "qpay",
        "billable_seconds": billable,
        "amount_mnt": amount_mnt,
        "price_mnt_per_hour": rate,
    }


def _access_token_ok(expected: str, provided: str) -> bool:
    left = (expected or "").encode("utf-8")
    right = (provided or "").strip().encode("utf-8")
    if not left or len(left) != len(right):
        return False
    return secrets.compare_digest(left, right)


def get_stt_order(order_id: str, access_token: str) -> dict[str, Any] | None:
    order = get_order(order_id)
    if not order or order.get("product_kind") != STT_PRODUCT_KIND:
        return None
    expected = str(order.get("access_token") or "")
    if not _access_token_ok(expected, access_token):
        return None
    return order


def bind_stt_job(
    order_id: str,
    *,
    access_token: str,
    chimege_uuid: str,
    actual_duration_seconds: float,
) -> dict[str, Any]:
    """Attach Chimege job to a paid order. Not consumed until transcript is delivered."""
    with _lock:
        orders = _load_orders()
        order = orders.get(order_id)
        if not order or order.get("product_kind") != STT_PRODUCT_KIND:
            raise ValueError("Төлбөрийн захиалга олдсонгүй.")
        expected = str(order.get("access_token") or "")
        if not _access_token_ok(expected, access_token):
            raise ValueError("Төлбөрийн эрх буруу.")
        if order.get("status") != "paid":
            raise ValueError("Эхлээд төлбөрөө төлнө үү.")
        if order.get("consumed"):
            raise ValueError("Энэ төлбөрөөр аль хэдийн хөрвүүлсэн.")
        existing_uuid = str(order.get("chimege_uuid") or "").strip()
        if existing_uuid and existing_uuid == (chimege_uuid or "").strip():
            return dict(order)
        if existing_uuid:
            # Keep the first submitted job — client can resume polling it.
            return dict(order)
        paid_seconds = float(order.get("duration_seconds") or 0)
        actual = max(0.0, float(actual_duration_seconds))
        overrun = bool(paid_seconds > 0 and actual > paid_seconds * STT_DURATION_SLACK + 1)
        stamped = _iso(_now())
        order["chimege_uuid"] = (chimege_uuid or "")[:80]
        order["actual_duration_seconds"] = round(actual, 2)
        order["duration_overrun"] = overrun
        order["updated_at"] = stamped
        order["note"] = "Төлбөр амжилттай · бичвэр бэлтгэж байна."
        _append_event(order, "submitted", chimege_uuid or "")
        orders[order_id] = order
        _save_orders(orders)
        return dict(order)


def complete_stt_order(
    order_id: str,
    *,
    access_token: str,
    chimege_uuid: str = "",
) -> dict[str, Any]:
    """Mark paid STT order delivered after transcript is ready (safe to call twice)."""
    with _lock:
        orders = _load_orders()
        order = orders.get(order_id)
        if not order or order.get("product_kind") != STT_PRODUCT_KIND:
            raise ValueError("Төлбөрийн захиалга олдсонгүй.")
        expected = str(order.get("access_token") or "")
        if not _access_token_ok(expected, access_token):
            raise ValueError("Төлбөрийн эрх буруу.")
        if order.get("status") != "paid":
            raise ValueError("Эхлээд төлбөрөө төлнө үү.")
        if order.get("consumed"):
            return dict(order)
        stamped = _iso(_now())
        if chimege_uuid and not order.get("chimege_uuid"):
            order["chimege_uuid"] = chimege_uuid[:80]
        order["consumed"] = True
        order["delivered_at"] = stamped
        order["updated_at"] = stamped
        order["note"] = "Бичвэр амжилттай бэлтгэгдлээ."
        _append_event(order, "delivered", str(order.get("chimege_uuid") or ""))
        orders[order_id] = order
        _save_orders(orders)
        return dict(order)


def consume_stt_order(
    order_id: str,
    *,
    access_token: str,
    chimege_uuid: str,
    actual_duration_seconds: float,
) -> dict[str, Any]:
    """Deprecated alias — binds the job; delivery completes separately."""
    return bind_stt_job(
        order_id,
        access_token=access_token,
        chimege_uuid=chimege_uuid,
        actual_duration_seconds=actual_duration_seconds,
    )


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


def find_order_by_qpay_invoice_id(invoice_id: str) -> dict[str, Any] | None:
    needle = (invoice_id or "").strip()
    if not needle:
        return None
    with _lock:
        for row in _load_orders().values():
            if str(row.get("qpay_invoice_id") or "") == needle:
                return dict(row)
    return None


def mark_order_paid(order_id: str, *, qpay_payment_id: str = "") -> dict[str, Any] | None:
    """Mark invoice paid; activate plan for subscription orders only (not STT)."""
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
        is_stt = order.get("product_kind") == STT_PRODUCT_KIND
        order["note"] = (
            "Төлбөр амжилттай. Одоо бичвэр болгоно."
            if is_stt
            else "Төлбөр амжилттай. Эрх идэвхжүүлэгдлээ."
        )
        if qpay_payment_id:
            order["qpay_payment_id"] = qpay_payment_id
        _append_event(order, "paid", qpay_payment_id or "")
        orders[order_id] = order
        _save_orders(orders)
        snapshot = dict(order)

    if snapshot.get("product_kind") != STT_PRODUCT_KIND:
        user_id = str(snapshot.get("user_id") or "").strip()
        plan_id = str(snapshot.get("plan_id") or "").strip()
        if user_id and plan_id and plan_id != "stt":
            activate_plan_for_user(
                user_id,
                plan_id,
                duration_days=int(snapshot.get("duration_days") or 0) or None,
            )
    return snapshot


def sync_order_payment(order: dict[str, Any]) -> dict[str, Any]:
    """Ask QPay whether this order's invoice is paid; activate if confirmed."""
    if order.get("status") == "paid":
        return order
    invoice_id = str(order.get("qpay_invoice_id") or "").strip()
    if not invoice_id:
        return order
    if not qpay_configured():
        return order
    try:
        result = check_invoice_paid(invoice_id)
    except QPayError:
        _log.exception("QPay payment check failed for %s", invoice_id)
        return order
    if not result.get("paid"):
        return order
    updated = mark_order_paid(
        str(order["id"]),
        qpay_payment_id=str(result.get("payment_id") or ""),
    )
    return updated or order


def list_orders_for_user(user_id: str, *, limit: int = 20) -> list[dict[str, Any]]:
    with _lock:
        rows = [dict(row) for row in _load_orders().values() if str(row.get("user_id")) == user_id]
    rows.sort(key=lambda row: str(row.get("created_at") or ""), reverse=True)
    return [public_order(row) for row in rows[: max(1, min(limit, 100))]]
