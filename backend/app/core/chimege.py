"""Chimege STT prepaid config + usage (no audio persisted)."""

from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.engine.dictionary import persist_dir

# End-user display/charge rate (MNT per hour of audio).
PRICE_MNT_PER_HOUR = 7_000
# Soft warning when prepaid remaining drops below this (seconds).
LOW_BALANCE_SECONDS = 30 * 60
# Keep a short usage audit (no transcript / no audio).
_MAX_USAGE_ROWS = 2_000

_lock = threading.Lock()


def _path() -> Path:
    return persist_dir() / "chimege.json"


def _token_path() -> Path:
    """Optional secret file (chmod 600), same idea as OpenAI key."""
    return Path(__file__).resolve().parents[3] / "data" / ".chimege_token"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty() -> dict[str, Any]:
    return {
        "api_token": "",
        "prepaid_seconds": 0.0,
        "used_seconds": 0.0,
        "price_mnt_per_hour": PRICE_MNT_PER_HOUR,
        "usage": [],
        "updated_at": None,
    }


def _load() -> dict[str, Any]:
    path = _path()
    if not path.is_file():
        return _empty()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty()
    if not isinstance(raw, dict):
        return _empty()
    out = _empty()
    out["api_token"] = str(raw.get("api_token") or "").strip()
    try:
        out["prepaid_seconds"] = max(0.0, float(raw.get("prepaid_seconds") or 0))
    except (TypeError, ValueError):
        out["prepaid_seconds"] = 0.0
    try:
        out["used_seconds"] = max(0.0, float(raw.get("used_seconds") or 0))
    except (TypeError, ValueError):
        out["used_seconds"] = 0.0
    try:
        price = float(raw.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR)
        out["price_mnt_per_hour"] = price if price > 0 else PRICE_MNT_PER_HOUR
    except (TypeError, ValueError):
        out["price_mnt_per_hour"] = PRICE_MNT_PER_HOUR
    usage = raw.get("usage")
    if isinstance(usage, list):
        out["usage"] = [row for row in usage if isinstance(row, dict)][-_MAX_USAGE_ROWS:]
    out["updated_at"] = raw.get("updated_at")
    return out


def _save(data: dict[str, Any]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "api_token": str(data.get("api_token") or "").strip(),
        "prepaid_seconds": float(data.get("prepaid_seconds") or 0),
        "used_seconds": float(data.get("used_seconds") or 0),
        "price_mnt_per_hour": float(data.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR),
        "usage": list(data.get("usage") or [])[-_MAX_USAGE_ROWS:],
        "updated_at": _now(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_token_file() -> str:
    path = _token_path()
    if not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _write_token_file(token: str) -> None:
    path = _token_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    cleaned = token.strip()
    if cleaned:
        path.write_text(cleaned + "\n", encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
    elif path.exists():
        path.unlink()


def _token_from_data(data: dict[str, Any]) -> str:
    token = str(data.get("api_token") or "").strip()
    if token:
        return token
    file_token = _read_token_file()
    if file_token:
        return file_token
    return str(getattr(settings, "chimege_api_token", "") or "").strip()


def get_api_token() -> str:
    """Resolve token: persist JSON → secret file → env."""
    with _lock:
        data = _load()
        return _token_from_data(data)


def set_api_token(token: str) -> None:
    cleaned = token.strip()
    with _lock:
        data = _load()
        data["api_token"] = cleaned
        _save(data)
    _write_token_file(cleaned)


def mask_token(token: str) -> str:
    value = token.strip()
    if not value:
        return ""
    if len(value) <= 10:
        return "•" * len(value)
    return f"{value[:6]}…{value[-4:]}"


def remaining_seconds(data: dict[str, Any] | None = None) -> float:
    row = data if data is not None else _load()
    prepaid = float(row.get("prepaid_seconds") or 0)
    used = float(row.get("used_seconds") or 0)
    return max(0.0, prepaid - used)


def seconds_to_mnt(seconds: float, price_per_hour: float | None = None) -> float:
    rate = float(price_per_hour if price_per_hour is not None else PRICE_MNT_PER_HOUR)
    return round((max(0.0, seconds) / 3600.0) * rate, 2)


def public_status() -> dict[str, Any]:
    with _lock:
        data = _load()
        token = _token_from_data(data)
        remaining = remaining_seconds(data)
        price = float(data.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR)
        return {
            "enabled": bool(token),
            "remaining_seconds": round(remaining, 2),
            "remaining_hours": round(remaining / 3600.0, 3),
            "used_seconds": round(float(data.get("used_seconds") or 0), 2),
            "prepaid_seconds": round(float(data.get("prepaid_seconds") or 0), 2),
            "price_mnt_per_hour": price,
            "low_balance": remaining <= LOW_BALANCE_SECONDS,
            "needs_renewal": remaining <= 0 or not token,
        }


def admin_snapshot() -> dict[str, Any]:
    with _lock:
        data = _load()
        token = _token_from_data(data)
    remaining = remaining_seconds(data)
    price = float(data.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR)
    usage = list(reversed(data.get("usage") or []))[:100]
    return {
        "has_token": bool(token),
        "token_masked": mask_token(token),
        "prepaid_seconds": round(float(data.get("prepaid_seconds") or 0), 2),
        "used_seconds": round(float(data.get("used_seconds") or 0), 2),
        "remaining_seconds": round(remaining, 2),
        "remaining_hours": round(remaining / 3600.0, 3),
        "prepaid_mnt_spent": seconds_to_mnt(float(data.get("used_seconds") or 0), price),
        "remaining_mnt_value": seconds_to_mnt(remaining, price),
        "price_mnt_per_hour": price,
        "low_balance": remaining <= LOW_BALANCE_SECONDS,
        "needs_renewal": remaining <= 0 or not token,
        "updated_at": data.get("updated_at"),
        "usage": usage,
    }


def update_admin(
    *,
    token: str | None = None,
    add_prepaid_seconds: float | None = None,
    set_prepaid_seconds: float | None = None,
    price_mnt_per_hour: float | None = None,
    reset_used: bool = False,
) -> dict[str, Any]:
    with _lock:
        data = _load()
        if token is not None:
            data["api_token"] = token.strip()
            _write_token_file(token)
        if set_prepaid_seconds is not None:
            data["prepaid_seconds"] = max(0.0, float(set_prepaid_seconds))
        if add_prepaid_seconds is not None:
            data["prepaid_seconds"] = max(
                0.0, float(data.get("prepaid_seconds") or 0) + float(add_prepaid_seconds)
            )
        if price_mnt_per_hour is not None and float(price_mnt_per_hour) > 0:
            data["price_mnt_per_hour"] = float(price_mnt_per_hour)
        if reset_used:
            data["used_seconds"] = 0.0
        _save(data)
    return admin_snapshot()


def reserve_and_record_usage(
    *,
    duration_seconds: float,
    filename: str,
    user_id: str | None = None,
    chimege_uuid: str | None = None,
) -> dict[str, Any]:
    """Deduct prepaid balance for a completed submit. Raises ValueError if insufficient."""
    duration = max(0.0, float(duration_seconds))
    with _lock:
        data = _load()
        remaining = remaining_seconds(data)
        if duration > remaining + 0.05:
            raise ValueError(
                f"Урьдчилсан эрх хүрэхгүй (үлдсэн {remaining:.0f} сек, хэрэгтэй {duration:.0f} сек)."
            )
        data["used_seconds"] = float(data.get("used_seconds") or 0) + duration
        price = float(data.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR)
        row = {
            "at": _now(),
            "duration_seconds": round(duration, 2),
            "mnt": seconds_to_mnt(duration, price),
            "filename": (filename or "")[:120],
            "user_id": (user_id or "")[:80] or None,
            "uuid": (chimege_uuid or "")[:80] or None,
        }
        usage = list(data.get("usage") or [])
        usage.append(row)
        data["usage"] = usage[-_MAX_USAGE_ROWS:]
        _save(data)
        remaining_after = remaining_seconds(data)
    return {
        "duration_seconds": round(duration, 2),
        "mnt": seconds_to_mnt(duration, price),
        "remaining_seconds": round(remaining_after, 2),
        "remaining_hours": round(remaining_after / 3600.0, 3),
    }
