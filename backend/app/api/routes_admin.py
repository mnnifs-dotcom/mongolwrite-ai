from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from app.core.auth import (
    clear_session_cookie,
    credentials_ok,
    require_admin,
    set_session_cookie,
)
from app.core.config import settings
from app.engine.hunspell_candidates import (
    approve_words,
    counts,
    list_candidates,
    record_from_text,
    reject_words,
)
from app.engine.runtime import get_engine

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
AdminDep = Annotated[None, Depends(require_admin)]


class LoginRequest(BaseModel):
    username: str = Field(default="", max_length=80)
    password: str = Field(default="", max_length=200)


class WordsAction(BaseModel):
    words: list[str] = Field(default_factory=list, max_length=2000)


class HarvestRequest(BaseModel):
    text: str = Field(default="", max_length=500_000)


@router.post("/login")
def login(body: LoginRequest, response: Response) -> dict[str, bool]:
    if not settings.admin_password:
        raise HTTPException(status_code=503, detail="Админ нууц үг тохируулаагүй")
    if not credentials_ok(body.username, body.password):
        raise HTTPException(status_code=401, detail="Нэвтрэх нэр эсвэл нууц үг буруу")
    set_session_cookie(response)
    return {"ok": True}


@router.post("/logout")
def logout(response: Response) -> dict[str, bool]:
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me")
def me(_: AdminDep) -> dict[str, str]:
    return {"role": "admin", "username": settings.admin_username}


@router.get("/overview")
def overview(_: AdminDep) -> dict[str, Any]:
    engine = get_engine()
    cand = counts()
    return {
        "lexicon": {
            "seed": len(engine.dictionary._seed),
            "has_hunspell": engine.dictionary.has_hunspell,
        },
        "candidates": cand,
        "admin_username": settings.admin_username,
        "check_max_chars": settings.check_max_chars,
    }


@router.get("/candidates")
def candidates(
    _: AdminDep,
    tier: Literal["reliable", "doubt", ""] = "",
) -> dict[str, Any]:
    items = list_candidates(tier or None)
    return {"items": items, "count": len(items), "counts": counts()}


@router.post("/candidates/approve")
def candidates_approve(body: WordsAction, _: AdminDep) -> dict[str, Any]:
    if not body.words:
        raise HTTPException(status_code=400, detail="Үг сонгоогүй")
    result = approve_words(get_engine(), body.words)
    return {**result, "counts": counts()}


@router.post("/candidates/reject")
def candidates_reject(body: WordsAction, _: AdminDep) -> dict[str, Any]:
    if not body.words:
        raise HTTPException(status_code=400, detail="Үг сонгоогүй")
    result = reject_words(body.words)
    return {**result, "counts": counts()}


@router.post("/candidates/harvest")
def candidates_harvest(body: HarvestRequest, _: AdminDep) -> dict[str, Any]:
    """Manual harvest from pasted text (also runs automatically on checks)."""
    queued = record_from_text(get_engine(), body.text)
    return {"queued": queued, "counts": counts()}
