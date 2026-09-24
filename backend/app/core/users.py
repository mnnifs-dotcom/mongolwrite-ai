"""Persisted Google-authenticated users (volume JSON)."""

from __future__ import annotations

import json
import re
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from app.core.plans import DEFAULT_PLAN, get_plan, is_paid_plan, normalize_plan_id
from app.engine.dictionary import persist_dir

_lock = threading.Lock()
MAX_DEVICES = 2
DEVICE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{8,128}$")


def _users_path() -> Path:
    return persist_dir() / "users.json"


def _load() -> dict[str, dict[str, Any]]:
    path = _users_path()
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    users = raw.get("users") if isinstance(raw, dict) else None
    if not isinstance(users, dict):
        return {}
    return {str(key): value for key, value in users.items() if isinstance(value, dict)}


def _save(users: dict[str, dict[str, Any]]) -> None:
    path = _users_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"users": users}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp


def plan_is_active(row: dict[str, Any], *, now: datetime | None = None) -> bool:
    """Paid plan still valid (no expiry, or expiry in the future)."""
    plan_id = normalize_plan_id(str(row.get("plan") or DEFAULT_PLAN))
    if plan_id == DEFAULT_PLAN or plan_id == "free" or not is_paid_plan(plan_id):
        return False
    expires = _parse_iso(str(row.get("plan_expires_at") or "") or None)
    if expires is None:
        return True
    current = now or datetime.now(timezone.utc)
    return expires > current


def _default_expiry_for_plan(plan_id: str) -> str | None:
    plan = get_plan(plan_id)
    days = plan.get("duration_days")
    if not days:
        return None
    stamp = datetime.now(timezone.utc) + timedelta(days=int(days))
    return stamp.isoformat()


def set_user_plan(
    user_id: str,
    plan: str,
    *,
    plan_expires_at: str | None = None,
    auto_duration: bool = False,
) -> dict[str, Any] | None:
    """Update plan + optional ISO expiry.

    When auto_duration=True and no expiry given, paid plans get duration_days from catalog.
    """
    plan_id = get_plan(plan)["id"]
    expires: str | None
    if plan_id == "free":
        expires = None
    elif plan_expires_at is None:
        expires = _default_expiry_for_plan(plan_id) if auto_duration else None
    else:
        text = str(plan_expires_at).strip()
        if not text:
            expires = _default_expiry_for_plan(plan_id) if auto_duration else None
        else:
            parsed = _parse_iso(text)
            if parsed is None:
                raise ValueError("Төлбөрийн дуусах огноо буруу")
            expires = parsed.astimezone(timezone.utc).isoformat()
    with _lock:
        users = _load()
        row = users.get(user_id)
        if not row:
            return None
        row["plan"] = plan_id
        row["plan_expires_at"] = expires
        users[user_id] = row
        _save(users)
        return dict(row)


def activate_plan_for_user(
    user_id: str,
    plan_id: str,
    *,
    duration_days: int | None = None,
) -> dict[str, Any] | None:
    """Activate a paid plan from now + duration (billing callback)."""
    plan = get_plan(plan_id)
    if plan["id"] == "free":
        return set_user_plan(user_id, "free")
    days = duration_days if duration_days and duration_days > 0 else plan.get("duration_days")
    expires: str | None = None
    if days:
        stamp = datetime.now(timezone.utc) + timedelta(days=int(days))
        expires = stamp.isoformat()
    return set_user_plan(user_id, plan["id"], plan_expires_at=expires)


def upsert_google_user(
    *,
    sub: str,
    email: str,
    name: str = "",
    picture: str = "",
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        users = _load()
        existing = users.get(sub)
        if existing:
            existing["email"] = email or existing.get("email", "")
            existing["name"] = name or existing.get("name", "")
            existing["picture"] = picture or existing.get("picture", "")
            existing["last_login_at"] = now
            row = existing
        else:
            row = {
                "id": sub,
                "email": email,
                "name": name,
                "picture": picture,
                "plan": DEFAULT_PLAN,
                "plan_expires_at": None,
                "created_at": now,
                "last_login_at": now,
            }
            users[sub] = row
        _save(users)
        return dict(row)


def get_user(user_id: str) -> dict[str, Any] | None:
    with _lock:
        row = _load().get(user_id)
        return dict(row) if row else None


def update_user_fields(user_id: str, **fields: Any) -> dict[str, Any] | None:
    """Patch arbitrary persisted fields on a user row."""
    with _lock:
        users = _load()
        row = users.get(user_id)
        if not row:
            return None
        for key, value in fields.items():
            row[key] = value
        users[user_id] = row
        _save(users)
        return dict(row)


def touch_last_check(user_id: str) -> dict[str, Any] | None:
    """Record the latest spelling-check timestamp for admin visibility."""
    now = datetime.now(timezone.utc).isoformat()
    return update_user_fields(user_id, last_check_at=now)


def normalize_device_id(raw: str | None) -> str | None:
    value = (raw or "").strip()
    if not value or not DEVICE_ID_RE.fullmatch(value):
        return None
    return value


def _devices_from_row(row: dict[str, Any]) -> list[dict[str, Any]]:
    devices = row.get("devices")
    if not isinstance(devices, list):
        return []
    out: list[dict[str, Any]] = []
    for item in devices:
        if not isinstance(item, dict):
            continue
        device_id = normalize_device_id(str(item.get("id") or ""))
        if not device_id:
            continue
        out.append(
            {
                "id": device_id,
                "first_seen_at": str(item.get("first_seen_at") or ""),
                "last_seen_at": str(item.get("last_seen_at") or ""),
            }
        )
    return out


def list_user_devices(user_id: str) -> list[dict[str, Any]]:
    row = get_user(user_id)
    if not row:
        return []
    return _devices_from_row(row)


def clear_user_devices(user_id: str) -> dict[str, Any] | None:
    """Admin helper: wipe registered devices so the user can sign in again."""
    return update_user_fields(user_id, devices=[])


def unregister_device(user_id: str, device_id: str) -> list[dict[str, Any]]:
    """Remove one device from the account registry (e.g. on logout)."""
    normalized = normalize_device_id(device_id)
    if not normalized:
        return list_user_devices(user_id)
    with _lock:
        users = _load()
        row = users.get(user_id)
        if not row:
            return []
        devices = [item for item in _devices_from_row(row) if item["id"] != normalized]
        row["devices"] = devices
        users[user_id] = row
        _save(users)
        return list(devices)


def register_or_touch_device(user_id: str, device_id: str) -> list[dict[str, Any]]:
    """Register a device or refresh last_seen. Raises PermissionError at the 2-device cap."""
    normalized = normalize_device_id(device_id)
    if not normalized:
        raise ValueError("Төхөөрөмжийн мэдээлэл олдсонгүй. Хуудсыг дахин ачаална уу.")
    now = datetime.now(timezone.utc).isoformat()
    with _lock:
        users = _load()
        row = users.get(user_id)
        if not row:
            raise ValueError("Нэвтрэх шаардлагатай")
        devices = _devices_from_row(row)
        for item in devices:
            if item["id"] == normalized:
                item["last_seen_at"] = now
                row["devices"] = devices
                users[user_id] = row
                _save(users)
                return list(devices)
        if len(devices) >= MAX_DEVICES:
            raise PermissionError(
                "Нэг бүртгэлээр зэрэг зөвхөн 2 төхөөрөмжөөс нэвтэрч болно. "
                "Өөр төхөөрөмж дээрээсээ «Гарах» дарж нэвтрэлтээ хаагаад энд дахин оролдоно уу."
            )
        devices.append(
            {
                "id": normalized,
                "first_seen_at": now,
                "last_seen_at": now,
            }
        )
        row["devices"] = devices
        users[user_id] = row
        _save(users)
        return list(devices)


def list_users(
    *,
    q: str = "",
    plan: str = "",
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    query = q.strip().casefold()
    plan_filter = plan.strip().casefold()
    with _lock:
        all_rows = [dict(row) for row in _load().values()]
    all_rows.sort(
        key=lambda row: str(row.get("last_login_at") or row.get("created_at") or ""),
        reverse=True,
    )
    rows = all_rows
    if query:
        rows = [
            row
            for row in rows
            if query in str(row.get("email") or "").casefold()
            or query in str(row.get("name") or "").casefold()
            or query in str(row.get("id") or "").casefold()
        ]
    if plan_filter in {"free", "paid", "pro", "pro_3m", "pro_year"}:
        if plan_filter == "paid":
            rows = [row for row in rows if plan_is_active(row)]
        elif plan_filter == "free":
            rows = [row for row in rows if not plan_is_active(row)]
        elif plan_filter == "pro":
            # Legacy filter: any paid SKU
            rows = [
                row
                for row in rows
                if normalize_plan_id(str(row.get("plan") or "")) in {"pro_3m", "pro_year", "pro"}
                and plan_is_active(row)
            ]
        else:
            rows = [
                row
                for row in rows
                if normalize_plan_id(str(row.get("plan") or "")) == plan_filter
            ]
    total = len(rows)
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    page = rows[offset : offset + limit]
    return {
        "items": [admin_user(row) for row in page],
        "total": total,
        "offset": offset,
        "limit": limit,
        "counts": _plan_counts(all_rows),
    }


def _plan_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    paid = sum(1 for row in rows if plan_is_active(row))
    free = len(rows) - paid
    pro_3m = sum(
        1 for row in rows if normalize_plan_id(str(row.get("plan") or "")) == "pro_3m" and plan_is_active(row)
    )
    pro_year = sum(
        1
        for row in rows
        if normalize_plan_id(str(row.get("plan") or "")) in {"pro_year", "pro"} and plan_is_active(row)
    )
    return {
        "total": len(rows),
        "free": free,
        "paid": paid,
        "pro": paid,  # backward-compatible alias = all paid
        "pro_3m": pro_3m,
        "pro_year": pro_year,
    }


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    plan = get_plan(str(row.get("plan") or DEFAULT_PLAN))
    active = plan_is_active(row) if plan["id"] != "free" else False
    effective = plan if (plan["id"] == "free" or active) else get_plan(DEFAULT_PLAN)
    return {
        "id": row.get("id", ""),
        "email": row.get("email", ""),
        "name": row.get("name", ""),
        "picture": row.get("picture", ""),
        "plan": effective["id"],
        "plan_name": effective["name"],
        "plan_expires_at": row.get("plan_expires_at"),
        "is_paid": active,
        "entitlements": {
            "check_max_chars": effective["check_max_chars"],
            "checks_per_day": effective["checks_per_day"],
            "features": list(effective["features"]),
        },
    }


def admin_user(row: dict[str, Any]) -> dict[str, Any]:
    plan = get_plan(str(row.get("plan") or DEFAULT_PLAN))
    paid = plan_is_active(row)
    expires = row.get("plan_expires_at")
    if paid:
        status = plan["name"] if plan["id"] != "free" else "Төлбөртэй"
    elif plan["id"] != "free" and expires:
        status = "Хугацаа дууссан"
    else:
        status = "Үнэгүй"
    return {
        "id": row.get("id", ""),
        "email": row.get("email", ""),
        "name": row.get("name", ""),
        "picture": row.get("picture", ""),
        "plan": plan["id"],
        "plan_name": plan["name"],
        "plan_expires_at": expires,
        "is_paid": paid,
        "status": status,
        "created_at": row.get("created_at", ""),
        "last_login_at": row.get("last_login_at", ""),
        "last_check_at": row.get("last_check_at", ""),
        "device_count": len(_devices_from_row(row)),
    }
