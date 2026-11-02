from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.devices import DEVICE_HEADER, enforce_device, register_device_or_raise, unregister_user_device
from app.core.plans import list_plans
from app.core.user_auth import (
    clear_user_cookie,
    optional_user,
    set_user_cookie,
)
from app.core.users import public_user, upsert_google_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    credential: str = Field(default="", max_length=10_000)
    access_token: str = Field(default="", max_length=10_000)


def _identity_from_info(info: dict[str, Any]) -> dict[str, str]:
    sub = str(info.get("sub") or "").strip()
    email = str(info.get("email") or "").strip()
    if not sub or not email:
        raise HTTPException(status_code=401, detail="Google бүртгэл дутуу")
    return {
        "sub": sub,
        "email": email,
        "name": str(info.get("name") or "").strip(),
        "picture": str(info.get("picture") or "").strip(),
    }


def _verify_google_credential(credential: str) -> dict[str, str]:
    client_id = settings.google_client_id.strip()
    if not client_id:
        raise HTTPException(status_code=503, detail="Google нэвтрэлт тохируулаагүй")
    try:
        from google.auth.transport import requests as google_requests
        from google.oauth2 import id_token
    except ImportError as exc:  # pragma: no cover
        raise HTTPException(status_code=503, detail="Google auth сан суугаагүй") from exc
    try:
        info = id_token.verify_oauth2_token(
            credential,
            google_requests.Request(),
            client_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Google нэвтрэлт амжилтгүй") from exc
    if info.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=401, detail="Google нэвтрэлт амжилтгүй")
    return _identity_from_info(info)


def _verify_google_access_token(access_token: str) -> dict[str, str]:
    if not settings.google_client_id.strip():
        raise HTTPException(status_code=503, detail="Google нэвтрэлт тохируулаагүй")
    try:
        response = httpx.get(
            "https://www.googleapis.com/oauth2/v3/userinfo",
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10.0,
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=401, detail="Google нэвтрэлт амжилтгүй") from exc
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Google нэвтрэлт амжилтгүй")
    try:
        info = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=401, detail="Google нэвтрэлт амжилтгүй") from exc
    if not isinstance(info, dict):
        raise HTTPException(status_code=401, detail="Google нэвтрэлт амжилтгүй")
    return _identity_from_info(info)


@router.post("/google")
def login_google(
    body: GoogleLoginRequest,
    response: Response,
    x_mw_device_id: Annotated[str | None, Header(alias=DEVICE_HEADER)] = None,
) -> dict[str, Any]:
    access_token = body.access_token.strip()
    credential = body.credential.strip()
    if access_token:
        identity = _verify_google_access_token(access_token)
    elif credential:
        identity = _verify_google_credential(credential)
    else:
        raise HTTPException(status_code=400, detail="Token дутуу")
    row = upsert_google_user(
        sub=identity["sub"],
        email=identity["email"],
        name=identity["name"],
        picture=identity["picture"],
    )
    register_device_or_raise(str(row["id"]), x_mw_device_id or "")
    set_user_cookie(response, str(row["id"]))
    return {"ok": True, "user": public_user(row)}


@router.get("/me")
def me(
    user: Annotated[dict | None, Depends(optional_user)],
    x_mw_device_id: Annotated[str | None, Header(alias=DEVICE_HEADER)] = None,
) -> dict[str, Any]:
    if not user:
        return {
            "authenticated": False,
            "user": None,
            "google_client_id": settings.google_client_id or None,
            "plans": list_plans(),
        }
    enforce_device(str(user["id"]), x_mw_device_id)
    return {
        "authenticated": True,
        "user": user,
        "google_client_id": settings.google_client_id or None,
        "plans": list_plans(),
    }


@router.post("/logout")
def logout(
    response: Response,
    user: Annotated[dict | None, Depends(optional_user)] = None,
    x_mw_device_id: Annotated[str | None, Header(alias=DEVICE_HEADER)] = None,
) -> dict[str, bool]:
    """End the session and free this browser's device slot."""
    if user:
        unregister_user_device(str(user["id"]), x_mw_device_id)
    clear_user_cookie(response)
    return {"ok": True}
