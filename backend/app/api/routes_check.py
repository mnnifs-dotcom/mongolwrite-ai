from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.ai.keys import ai_enabled
from app.ai.provider import OpenAIProvider
from app.ai.validate import filter_bad_suggestions
from app.core.config import settings
from app.engine.improve import improve_text
from app.engine.models import Correction
from app.engine.ranker import rank_corrections
from app.engine.runtime import get_engine, run_engine_check

router = APIRouter(prefix="/api/v1/check", tags=["check"])
_ai = OpenAIProvider()
_log = logging.getLogger(__name__)


class CheckRequest(BaseModel):
    text: str = Field(default="", max_length=settings.check_max_chars)
    document_type: str = "general"
    style: str = "government_official"


class CheckResponse(BaseModel):
    corrections: list[Correction]
    word_count: int
    character_count: int
    ai_enabled: bool = False


def _word_count(text: str) -> int:
    return len([part for part in text.split() if part])


def _ai_corrections(text: str, style: str) -> list[Correction]:
    if not text.strip() or not ai_enabled():
        return []
    try:
        return filter_bad_suggestions(
            _ai.check_text(text, style=style),
            get_engine().dictionary,
        )
    except Exception:
        return []


def run_check(text: str, style: str) -> list[Correction]:
    try:
        rules = run_engine_check(text, style)
    except Exception:
        _log.exception("check failed")
        rules = []
    extra = _ai_corrections(text, style)
    return rank_corrections([*rules, *extra])


@router.post("/deterministic", response_model=CheckResponse)
def check_deterministic(body: CheckRequest) -> CheckResponse:
    try:
        corrections = run_engine_check(body.text, style=body.style)
    except Exception:
        _log.exception("check failed")
        corrections = []
    return CheckResponse(
        corrections=corrections,
        word_count=_word_count(body.text),
        character_count=len(body.text),
        ai_enabled=ai_enabled(),
    )


@router.post("/all", response_model=CheckResponse)
def check_all(body: CheckRequest) -> CheckResponse:
    corrections = run_check(body.text, body.style)
    return CheckResponse(
        corrections=corrections,
        word_count=_word_count(body.text),
        character_count=len(body.text),
        ai_enabled=ai_enabled(),
    )


@router.post("/spelling", response_model=CheckResponse)
def check_spelling(body: CheckRequest) -> CheckResponse:
    result = check_deterministic(body)
    result.corrections = [c for c in result.corrections if c.category == "SPELLING"]
    return result


@router.post("/grammar", response_model=CheckResponse)
def check_grammar(body: CheckRequest) -> CheckResponse:
    result = check_deterministic(body)
    result.corrections = [
        c for c in result.corrections if c.category in {"GRAMMAR", "REDUNDANCY"}
    ]
    return result


@router.post("/style", response_model=CheckResponse)
def check_style(body: CheckRequest) -> CheckResponse:
    result = check_deterministic(body)
    result.corrections = [
        c for c in result.corrections if c.category in {"STYLE", "FORMALITY", "CLARITY"}
    ]
    return result


class ImproveResponse(CheckResponse):
    text: str
    applied_count: int


@router.post("/improve", response_model=ImproveResponse)
def improve_document(body: CheckRequest) -> ImproveResponse:
    engine = get_engine()
    text = body.text
    applied = 0
    if ai_enabled() and text.strip():
        try:
            rewritten = _ai.rewrite_text(text, style=body.style)
            if rewritten != text:
                text = rewritten
                applied = 1
        except Exception as exc:
            raise HTTPException(status_code=502, detail="Ойлголт холбогдсонгүй") from exc
    else:
        text, applied = improve_text(engine, text, style=body.style)
    corrections = run_check(text, body.style)
    return ImproveResponse(
        text=text,
        applied_count=applied,
        corrections=corrections,
        word_count=_word_count(text),
        character_count=len(text),
        ai_enabled=ai_enabled(),
    )


@router.post("/ai", response_model=CheckResponse)
def check_ai(body: CheckRequest) -> CheckResponse:
    if not ai_enabled():
        raise HTTPException(
            status_code=503,
            detail="Ойлголт ажиллахын тулд OpenAI түлхүүр оруулна уу.",
        )
    corrections = _ai_corrections(body.text, body.style)
    return CheckResponse(
        corrections=corrections,
        word_count=_word_count(body.text),
        character_count=len(body.text),
        ai_enabled=True,
    )
