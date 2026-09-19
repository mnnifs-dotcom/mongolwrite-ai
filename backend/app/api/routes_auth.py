from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.plans import list_plans
from app.core.user_auth import (
    clear_user_cookie,
    optional_user,
    require_user,
    set_user_cookie,
)
from app.core.users import public_user, upsert_google_user

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class GoogleLoginRequest(BaseModel):
    credential: str = Field(min_length=20, max_length=10_000)


def _verify_google_credential(credential: str) -> dict[str, Any]:
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
    sub = str(info.get("sub") or "").strip()
    email = str(info.get("email") or "").strip()
    if not sub or not email:
        raise HTTPException(status_code=401, detail="Google бүртгэл дутуу")
    return info


@router.post("/google")
def login_google(body: GoogleLoginRequest, response: Response) -> dict[str, Any]:
    info = _verify_google_credential(body.credential)
    row = upsert_google_user(
        sub=str(info["sub"]),
        email=str(info.get("email") or ""),
        name=str(info.get("name") or ""),
        picture=str(info.get("picture") or ""),
    )
    set_user_cookie(response, str(row["id"]))
    return {"ok": True, "user": public_user(row)}


@router.get("/me")
def me(user: Annotated[dict | None, Depends(optional_user)]) -> dict[str, Any]:
    if not user:
        return {
            "authenticated": False,
            "user": None,
            "google_client_id": settings.google_client_id or None,
            "plans": list_plans(),
        }
    return {
        "authenticated": True,
        "user": user,
        "google_client_id": settings.google_client_id or None,
        "plans": list_plans(),
    }


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    clear_user_cookie(response)
    return {"ok": True}


@router.get("/billing/plans")
def billing_plans() -> dict[str, Any]:
    return {"plans": list_plans(), "checkout_ready": False}


@router.post("/billing/checkout")
def billing_checkout(
    _: Annotated[dict, Depends(require_user)],
) -> dict[str, Any]:
    # Placeholder until a payment provider is wired.
    raise HTTPException(
        status_code=501,
        detail="Төлбөр тун удахгүй. Одоогоор Google-ээр нэвтэрч үнэгүй ашиглана.",
    )
