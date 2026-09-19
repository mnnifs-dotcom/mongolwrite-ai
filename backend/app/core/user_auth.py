"""Cookie sessions for Google-authenticated end users (separate from admin)."""

from __future__ import annotations

import hashlib
import hmac
from typing import Annotated

from fastapi import Cookie, HTTPException, Response

from app.core.config import settings
from app.core.users import get_user, public_user

_COOKIE = "mw_user"
_SESSION_HOURS = 24 * 30


def _sign(payload: str) -> str:
    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{digest}"


def _verify_and_extract(value: str) -> str | None:
    if "." not in value:
        return None
    payload, _, digest = value.partition(".")
    expected = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(digest, expected):
        return None
    if not payload.startswith("u:"):
        return None
    return payload[2:]


def set_user_cookie(response: Response, user_id: str) -> None:
    token = _sign(f"u:{user_id}")
    response.set_cookie(
        key=_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=_SESSION_HOURS * 3600,
        path="/",
    )


def clear_user_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
    )


def optional_user(
    session: Annotated[str | None, Cookie(alias=_COOKIE)] = None,
) -> dict | None:
    if not session:
        return None
    user_id = _verify_and_extract(session)
    if not user_id:
        return None
    row = get_user(user_id)
    if not row:
        return None
    return public_user(row)


def require_user(
    session: Annotated[str | None, Cookie(alias=_COOKIE)] = None,
) -> dict:
    user = optional_user(session)
    if not user:
        raise HTTPException(status_code=401, detail="Нэвтрэх шаардлагатай")
    return user
