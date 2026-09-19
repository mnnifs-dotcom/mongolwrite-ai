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


def public_user(row: dict[str, Any]) -> dict[str, Any]:
    plan = get_plan(str(row.get("plan") or DEFAULT_PLAN))
    return {
        "id": row.get("id", ""),
        "email": row.get("email", ""),
        "name": row.get("name", ""),
        "picture": row.get("picture", ""),
        "plan": plan["id"],
        "plan_name": plan["name"],
        "entitlements": {
            "check_max_chars": plan["check_max_chars"],
            "checks_per_day": plan["checks_per_day"],
            "features": list(plan["features"]),
        },
    }
