from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, Response

from app.core.config import settings

_COOKIE = "mw_admin"
_SESSION_HOURS = 24 * 7


def _sign(token: str) -> str:
    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{token}.{digest}"


def _verify(value: str) -> bool:
    if "." not in value:
        return False
    token, _, digest = value.partition(".")
    expected = hmac.new(
        settings.secret_key.encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, expected)


def credentials_ok(username: str, password: str) -> bool:
    if not settings.admin_password:
        return False
    return secrets.compare_digest(username, settings.admin_username) and secrets.compare_digest(
        password, settings.admin_password
    )


def set_session_cookie(response: Response) -> None:
    token = _sign(secrets.token_urlsafe(24))
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
    if not session or not _verify(session):
        raise HTTPException(status_code=401, detail="Админ нэвтрэх шаардлагатай")
