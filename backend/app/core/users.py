"""Persisted Google-authenticated users (volume JSON)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.plans import DEFAULT_PLAN, get_plan
from app.engine.dictionary import persist_dir

_lock = threading.Lock()


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
    """Paid/pro plan still valid (no expiry, or expiry in the future)."""
    plan_id = str(row.get("plan") or DEFAULT_PLAN)
    if plan_id == DEFAULT_PLAN or plan_id == "free":
        return False
    expires = _parse_iso(str(row.get("plan_expires_at") or "") or None)
    if expires is None:
        return True
    current = now or datetime.now(timezone.utc)
    return expires > current


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


def set_user_plan(
    user_id: str,
    plan: str,
    *,
    plan_expires_at: str | None = None,
) -> dict[str, Any] | None:
    """Update plan + optional ISO expiry. Empty expiry clears the field."""
    plan_id = get_plan(plan)["id"]
    expires: str | None
    if plan_id == "free":
        expires = None
    elif plan_expires_at is None:
        expires = None
    else:
        text = str(plan_expires_at).strip()
        if not text:
            expires = None
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
    if plan_filter in {"free", "pro", "paid"}:
        if plan_filter == "paid":
            rows = [row for row in rows if plan_is_active(row)]
        elif plan_filter == "pro":
            rows = [row for row in rows if str(row.get("plan") or "") == "pro"]
        else:
            rows = [row for row in rows if not plan_is_active(row)]
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
    return {"total": len(rows), "free": free, "paid": paid, "pro": sum(1 for r in rows if str(r.get("plan")) == "pro")}


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
        status = "Төлбөртэй"
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
    }
