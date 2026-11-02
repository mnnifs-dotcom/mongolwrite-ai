"""Chimege STT prepaid config + usage (no audio persisted).

Tokens are a queue: finish every leftover second on the current API
before the next paid token becomes active.
"""

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


def _slot(token: str = "", prepaid: float = 0.0, used: float = 0.0) -> dict[str, Any]:
    return {
        "token": str(token or "").strip(),
        "prepaid_seconds": max(0.0, float(prepaid or 0)),
        "used_seconds": max(0.0, float(used or 0)),
    }


def _slot_remaining(slot: dict[str, Any]) -> float:
    prepaid = float(slot.get("prepaid_seconds") or 0)
    used = float(slot.get("used_seconds") or 0)
    return max(0.0, prepaid - used)


def _normalize_slots(raw_slots: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_slots, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw_slots:
        if not isinstance(item, dict):
            continue
        token = str(item.get("token") or "").strip()
        if not token:
            continue
        try:
            prepaid = max(0.0, float(item.get("prepaid_seconds") or 0))
        except (TypeError, ValueError):
            prepaid = 0.0
        try:
            used = max(0.0, float(item.get("used_seconds") or 0))
        except (TypeError, ValueError):
            used = 0.0
        out.append(_slot(token, prepaid, used))
    return out


def _empty() -> dict[str, Any]:
    return {
        "slots": [],
        # Legacy fields kept for migration / older readers.
        "api_token": "",
        "prepaid_seconds": 0.0,
        "used_seconds": 0.0,
        "price_mnt_per_hour": PRICE_MNT_PER_HOUR,
        "usage": [],
        "updated_at": None,
    }


def _migrate_legacy(raw: dict[str, Any]) -> list[dict[str, Any]]:
    slots = _normalize_slots(raw.get("slots"))
    if slots:
        return slots
    token = str(raw.get("api_token") or "").strip()
    if not token:
        token = _read_token_file() or str(getattr(settings, "chimege_api_token", "") or "").strip()
    if not token:
        return []
    try:
        prepaid = max(0.0, float(raw.get("prepaid_seconds") or 0))
    except (TypeError, ValueError):
        prepaid = 0.0
    try:
        used = max(0.0, float(raw.get("used_seconds") or 0))
    except (TypeError, ValueError):
        used = 0.0
    return [_slot(token, prepaid, used)]


def _sync_legacy_fields(data: dict[str, Any]) -> None:
    """Mirror active slot into legacy keys for simpler status math."""
    active = _active_slot(data.get("slots") or [])
    if active is None:
        data["api_token"] = ""
        data["prepaid_seconds"] = 0.0
        data["used_seconds"] = 0.0
        return
    data["api_token"] = str(active.get("token") or "")
    data["prepaid_seconds"] = float(active.get("prepaid_seconds") or 0)
    data["used_seconds"] = float(active.get("used_seconds") or 0)


def _active_index(slots: list[dict[str, Any]]) -> int | None:
    """First slot that still has remaining seconds (never skip leftover)."""
    for idx, slot in enumerate(slots):
        if _slot_remaining(slot) > 0.05 and str(slot.get("token") or "").strip():
            return idx
    # If all spent but slots exist, keep the last token visible for renewal UI.
    for idx in range(len(slots) - 1, -1, -1):
        if str(slots[idx].get("token") or "").strip():
            return idx
    return None


def _active_slot(slots: list[dict[str, Any]]) -> dict[str, Any] | None:
    idx = _active_index(slots)
    if idx is None:
        return None
    return slots[idx]


def _load() -> dict[str, Any]:
    path = _path()
    if not path.is_file():
        data = _empty()
        env_token = str(getattr(settings, "chimege_api_token", "") or "").strip()
        file_token = _read_token_file()
        token = file_token or env_token
        if token:
            data["slots"] = [_slot(token, 0.0, 0.0)]
            _sync_legacy_fields(data)
        return data
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return _empty()
    if not isinstance(raw, dict):
        return _empty()
    out = _empty()
    out["slots"] = _migrate_legacy(raw)
    try:
        price = float(raw.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR)
        out["price_mnt_per_hour"] = price if price > 0 else PRICE_MNT_PER_HOUR
    except (TypeError, ValueError):
        out["price_mnt_per_hour"] = PRICE_MNT_PER_HOUR
    usage = raw.get("usage")
    if isinstance(usage, list):
        out["usage"] = [row for row in usage if isinstance(row, dict)][-_MAX_USAGE_ROWS:]
    out["updated_at"] = raw.get("updated_at")
    _sync_legacy_fields(out)
    return out


def _save(data: dict[str, Any]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    slots = _normalize_slots(data.get("slots"))
    data["slots"] = slots
    _sync_legacy_fields(data)
    payload = {
        "slots": slots,
        "api_token": str(data.get("api_token") or "").strip(),
        "prepaid_seconds": float(data.get("prepaid_seconds") or 0),
        "used_seconds": float(data.get("used_seconds") or 0),
        "price_mnt_per_hour": float(data.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR),
        "usage": list(data.get("usage") or [])[-_MAX_USAGE_ROWS:],
        "updated_at": _now(),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    active = _active_slot(slots)
    _write_token_file(str(active.get("token") or "") if active else "")


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
    active = _active_slot(list(data.get("slots") or []))
    if active and str(active.get("token") or "").strip():
        return str(active["token"]).strip()
    file_token = _read_token_file()
    if file_token:
        return file_token
    return str(getattr(settings, "chimege_api_token", "") or "").strip()


def get_api_token() -> str:
    """Active queue token (current leftover must finish before next)."""
    with _lock:
        return _token_from_data(_load())


def set_api_token(token: str) -> None:
    update_admin(token=token)


def mask_token(token: str) -> str:
    value = token.strip()
    if not value:
        return ""
    if len(value) <= 10:
        return "•" * len(value)
    return f"{value[:6]}…{value[-4:]}"


def remaining_seconds(data: dict[str, Any] | None = None) -> float:
    """Total remaining across the whole queue (current + queued)."""
    row = data if data is not None else _load()
    total = 0.0
    for slot in list(row.get("slots") or []):
        total += _slot_remaining(slot)
    return total


def active_remaining_seconds(data: dict[str, Any] | None = None) -> float:
    row = data if data is not None else _load()
    active = _active_slot(list(row.get("slots") or []))
    if not active:
        return 0.0
    return _slot_remaining(active)


def seconds_to_mnt(seconds: float, price_per_hour: float | None = None) -> float:
    rate = float(price_per_hour if price_per_hour is not None else PRICE_MNT_PER_HOUR)
    return round((max(0.0, seconds) / 3600.0) * rate, 2)


def _queue_snapshot(slots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    active_idx = _active_index(slots)
    out: list[dict[str, Any]] = []
    for idx, slot in enumerate(slots):
        rem = _slot_remaining(slot)
        out.append(
            {
                "index": idx,
                "token_masked": mask_token(str(slot.get("token") or "")),
                "prepaid_seconds": round(float(slot.get("prepaid_seconds") or 0), 2),
                "used_seconds": round(float(slot.get("used_seconds") or 0), 2),
                "remaining_seconds": round(rem, 2),
                "remaining_hours": round(rem / 3600.0, 3),
                "active": idx == active_idx and rem > 0.05,
                "queued": active_idx is not None and idx > active_idx,
                "exhausted": rem <= 0.05,
            }
        )
    return out


def public_status() -> dict[str, Any]:
    with _lock:
        data = _load()
        token = _token_from_data(data)
        remaining = remaining_seconds(data)
        active_rem = active_remaining_seconds(data)
        price = float(data.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR)
        used_total = sum(float(s.get("used_seconds") or 0) for s in data.get("slots") or [])
        prepaid_total = sum(float(s.get("prepaid_seconds") or 0) for s in data.get("slots") or [])
        return {
            "enabled": bool(token),
            "remaining_seconds": round(remaining, 2),
            "remaining_hours": round(remaining / 3600.0, 3),
            "active_remaining_seconds": round(active_rem, 2),
            "used_seconds": round(used_total, 2),
            "prepaid_seconds": round(prepaid_total, 2),
            "price_mnt_per_hour": price,
            "low_balance": remaining <= LOW_BALANCE_SECONDS,
            "needs_renewal": remaining <= 0 or not token,
        }


def admin_snapshot() -> dict[str, Any]:
    with _lock:
        data = _load()
        token = _token_from_data(data)
        slots = list(data.get("slots") or [])
    remaining = remaining_seconds(data)
    active_rem = active_remaining_seconds(data)
    price = float(data.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR)
    used_total = sum(float(s.get("used_seconds") or 0) for s in slots)
    prepaid_total = sum(float(s.get("prepaid_seconds") or 0) for s in slots)
    usage = list(reversed(data.get("usage") or []))[:100]
    queue = _queue_snapshot(slots)
    queued = [row for row in queue if row["queued"]]
    return {
        "has_token": bool(token),
        "token_masked": mask_token(token),
        "prepaid_seconds": round(prepaid_total, 2),
        "used_seconds": round(used_total, 2),
        "remaining_seconds": round(remaining, 2),
        "remaining_hours": round(remaining / 3600.0, 3),
        "active_remaining_seconds": round(active_rem, 2),
        "prepaid_mnt_spent": seconds_to_mnt(used_total, price),
        "remaining_mnt_value": seconds_to_mnt(remaining, price),
        "price_mnt_per_hour": price,
        "low_balance": remaining <= LOW_BALANCE_SECONDS,
        "needs_renewal": remaining <= 0 or not token,
        "updated_at": data.get("updated_at"),
        "usage": usage,
        "queue": queue,
        "queued_count": len(queued),
        "queue_note": (
            "Өмнөх API-ийн үлдэгдэл секунд дууссаны дараа дараагийн token автоматаар идэвхжинэ."
            if queued
            else "Идэвхтэй API-ийн үлдэгдлийг бүрэн дуустал ашиглана — секунд үлдээнэ үгүй."
        ),
    }


def activate_next_slot(*, waste_active_leftover: bool = True) -> dict[str, Any]:
    """Move to the next queued token. Optionally burns leftover on the active slot."""
    with _lock:
        data = _load()
        slots = list(data.get("slots") or [])
        idx = _active_index(slots)
        if idx is None:
            raise ValueError("Идэвхтэй API байхгүй.")
        if idx >= len(slots) - 1:
            raise ValueError("Дараалалд хүлээгдэж буй token байхгүй.")
        if waste_active_leftover:
            # Exhaust current prepaid so _active_index advances to the next slot.
            slots[idx]["used_seconds"] = float(slots[idx].get("prepaid_seconds") or 0)
        else:
            rem = _slot_remaining(slots[idx])
            if rem > 0.05:
                raise ValueError(
                    f"Идэвхтэй API дээр {rem:.0f} сек үлдсэн. "
                    f"Үлдэгдэл алгасахыг зөвшөөрөх эсвэл богино файлаар дуусга."
                )
        data["slots"] = slots
        _save(data)
    return admin_snapshot()


def update_admin(
    *,
    token: str | None = None,
    add_prepaid_seconds: float | None = None,
    set_prepaid_seconds: float | None = None,
    price_mnt_per_hour: float | None = None,
    reset_used: bool = False,
    activate_next: bool = False,
) -> dict[str, Any]:
    if activate_next:
        return activate_next_slot(waste_active_leftover=True)

    with _lock:
        data = _load()
        slots = list(data.get("slots") or [])
        cleaned = token.strip() if token is not None else None

        prepaid_target_idx: int | None = None

        if cleaned:
            active_idx = _active_index(slots)
            active = slots[active_idx] if active_idx is not None else None
            active_rem = _slot_remaining(active) if active else 0.0
            same_as_active = bool(active and active.get("token") == cleaned)
            if same_as_active and active_idx is not None:
                prepaid_target_idx = active_idx
            elif active and active_rem > 0.05:
                # Finish leftover seconds on current API first — queue the next token.
                prepaid_for_next = 0.0
                if set_prepaid_seconds is not None:
                    prepaid_for_next = max(0.0, float(set_prepaid_seconds))
                elif add_prepaid_seconds is not None:
                    prepaid_for_next = max(0.0, float(add_prepaid_seconds))
                slots.append(_slot(cleaned, prepaid_for_next, 0.0))
                prepaid_target_idx = len(slots) - 1
                add_prepaid_seconds = None
                set_prepaid_seconds = None
            else:
                # No leftover — start the new token now.
                new_prepaid = 0.0
                if set_prepaid_seconds is not None:
                    new_prepaid = max(0.0, float(set_prepaid_seconds))
                elif add_prepaid_seconds is not None:
                    new_prepaid = max(0.0, float(add_prepaid_seconds))
                elif active:
                    # Preserve unused budget only if replacing exhausted same-pool edge case.
                    new_prepaid = 0.0
                slots.append(_slot(cleaned, new_prepaid, 0.0))
                prepaid_target_idx = len(slots) - 1
                add_prepaid_seconds = None
                set_prepaid_seconds = None

        if not slots and cleaned:
            slots = [_slot(cleaned, 0.0, 0.0)]
            prepaid_target_idx = 0

        if prepaid_target_idx is None:
            prepaid_target_idx = _active_index(slots)
            if prepaid_target_idx is None and slots:
                prepaid_target_idx = len(slots) - 1

        if prepaid_target_idx is not None and prepaid_target_idx < len(slots):
            if set_prepaid_seconds is not None:
                slots[prepaid_target_idx]["prepaid_seconds"] = max(
                    0.0, float(set_prepaid_seconds)
                )
                if reset_used:
                    slots[prepaid_target_idx]["used_seconds"] = 0.0
            if add_prepaid_seconds is not None:
                slots[prepaid_target_idx]["prepaid_seconds"] = max(
                    0.0,
                    float(slots[prepaid_target_idx].get("prepaid_seconds") or 0)
                    + float(add_prepaid_seconds),
                )
            if reset_used and set_prepaid_seconds is None:
                slots[prepaid_target_idx]["used_seconds"] = 0.0

        if price_mnt_per_hour is not None and float(price_mnt_per_hour) > 0:
            data["price_mnt_per_hour"] = float(price_mnt_per_hour)

        data["slots"] = slots
        _save(data)
    return admin_snapshot()


def reserve_and_record_usage(
    *,
    duration_seconds: float,
    filename: str,
    user_id: str | None = None,
    chimege_uuid: str | None = None,
) -> dict[str, Any]:
    """Deduct from the active slot only. Raises if that slot cannot cover duration."""
    duration = max(0.0, float(duration_seconds))
    with _lock:
        data = _load()
        slots = list(data.get("slots") or [])
        idx = _active_index(slots)
        if idx is None:
            raise ValueError("API token/урьдчилсан эрх байхгүй.")
        active = slots[idx]
        remaining = _slot_remaining(active)
        # Only the active token's leftover can be spent now — never skip ahead.
        if duration > remaining + 0.05:
            raise ValueError(
                f"Идэвхтэй API-ийн үлдэгдэл хүрэхгүй "
                f"(үлдсэн {remaining:.0f} сек, хэрэгтэй {duration:.0f} сек). "
                f"Үлдэгдлээ дуусгаад дараагийн API автоматаар идэвхжинэ."
            )
        active["used_seconds"] = float(active.get("used_seconds") or 0) + duration
        slots[idx] = active
        data["slots"] = slots
        price = float(data.get("price_mnt_per_hour") or PRICE_MNT_PER_HOUR)
        row = {
            "at": _now(),
            "duration_seconds": round(duration, 2),
            "mnt": seconds_to_mnt(duration, price),
            "filename": (filename or "")[:120],
            "user_id": (user_id or "")[:80] or None,
            "uuid": (chimege_uuid or "")[:80] or None,
            "token_masked": mask_token(str(active.get("token") or "")),
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
