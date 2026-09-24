"""Per-account device registry — max 2 concurrent browsers/devices."""

from __future__ import annotations

from typing import Any

from fastapi import Header, HTTPException

from app.core.users import (
    MAX_DEVICES,
    clear_user_devices,
    list_user_devices,
    normalize_device_id,
    register_or_touch_device,
    unregister_device,
)

DEVICE_HEADER = "X-MW-Device-Id"

__all__ = [
    "DEVICE_HEADER",
    "MAX_DEVICES",
    "clear_devices",
    "enforce_device",
    "list_devices",
    "normalize_device_id",
    "register_device_or_raise",
    "require_device_header",
    "unregister_user_device",
]


def list_devices(user_id: str) -> list[dict[str, Any]]:
    return list_user_devices(user_id)


def clear_devices(user_id: str) -> dict[str, Any] | None:
    return clear_user_devices(user_id)


def unregister_user_device(user_id: str, device_id: str | None) -> list[dict[str, Any]]:
    """Drop a device slot on logout so another browser can sign in."""
    normalized = normalize_device_id(device_id)
    if not normalized:
        return list_user_devices(user_id)
    return unregister_device(user_id, normalized)


def require_device_header(
    x_mw_device_id: str | None = Header(default=None, alias=DEVICE_HEADER),
) -> str:
    normalized = normalize_device_id(x_mw_device_id)
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="Төхөөрөмжийн мэдээлэл олдсонгүй. Хуудсыг дахин ачаална уу.",
        )
    return normalized


def register_device_or_raise(
    user_id: str,
    device_id: str,
    *,
    replace_lru: bool = False,
) -> list[dict[str, Any]]:
    try:
        return register_or_touch_device(user_id, device_id, replace_lru=replace_lru)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def enforce_device(user_id: str, device_id: str | None) -> None:
    """Require a known (or registrable) device for an authenticated session."""
    normalized = normalize_device_id(device_id)
    if not normalized:
        raise HTTPException(
            status_code=400,
            detail="Төхөөрөмжийн мэдээлэл олдсонгүй. Хуудсыг дахин ачаална уу.",
        )
    register_device_or_raise(user_id, normalized, replace_lru=False)
