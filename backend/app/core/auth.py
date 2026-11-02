from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Response

from app.core.config import settings

_COOKIE = "mw_admin"
_SESSION_HOURS = 24 * 7
_DEFAULT_ADMIN_PASSWORD = "Ilove@00"
_DEFAULT_SECRET_KEY = "change-me-in-production"


def production_admin_misconfigured() -> bool:
    """True when production still uses ship-default secrets (must block login)."""
    if settings.app_env != "production":
        return False
    return (
        settings.secret_key == _DEFAULT_SECRET_KEY
        or not settings.admin_password
        or settings.admin_password == _DEFAULT_ADMIN_PASSWORD
    )


def _sign(payload: str) -> str:
    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{payload}.{digest}"


def _verify(value: str) -> bool:
    if "." not in value:
        return False
    payload, _, digest = value.partition(".")
    expected = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(digest, expected):
        return False
    # Prefer signed expiry: a:{unix_expiry}:{nonce}
    if payload.startswith("a:"):
        parts = payload.split(":", 2)
        if len(parts) != 3:
            return False
        try:
            expires = int(parts[1])
        except ValueError:
            return False
        return expires >= int(time.time())
    # Legacy cookies without embedded expiry are rejected (force re-login).
    return False


def credentials_ok(username: str, password: str) -> bool:
    if production_admin_misconfigured():
        return False
    expected_user = settings.admin_username
    expected_pass = settings.admin_password
    if not expected_pass:
        return False
    # compare_digest requires equal-length strings; mismatched login must be False, not 500.
    if len(username) != len(expected_user) or len(password) != len(expected_pass):
        return False
    return secrets.compare_digest(username, expected_user) and secrets.compare_digest(
        password, expected_pass
    )


def set_session_cookie(response: Response) -> None:
    expires = int(time.time()) + _SESSION_HOURS * 3600
    payload = f"a:{expires}:{secrets.token_urlsafe(24)}"
    token = _sign(payload)
    response.set_cookie(
        key=_COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=_SESSION_HOURS * 3600,
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        key=_COOKIE,
        path="/",
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
    )


def require_admin(session: Annotated[str | None, Cookie(alias=_COOKIE)] = None) -> None:
    if production_admin_misconfigured():
        raise HTTPException(
            status_code=503,
            detail="Админ нэвтрэлт тохируулаагүй (production нууц үг солиогүй)",
        )
    if not session or not _verify(session):
        raise HTTPException(status_code=401, detail="Админ нэвтрэх шаардлагатай")
