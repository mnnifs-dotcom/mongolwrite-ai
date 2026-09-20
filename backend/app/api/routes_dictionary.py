from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.auth import require_admin
from app.engine.learn import learn_accepted_words
from app.engine.pending import record_skip
from app.engine.runtime import get_engine

router = APIRouter(prefix="/api/v1/dictionary", tags=["dictionary"])
AdminDep = Annotated[None, Depends(require_admin)]


class LearnRequest(BaseModel):
    text: str = Field(default="", max_length=1_000_000)


class WordsRequest(BaseModel):
    words: list[str] = Field(default_factory=list, max_length=5000)


class SkipRequest(BaseModel):
    word: str = Field(default="", max_length=80)
    rule_id: str = Field(default="", max_length=80)


class LearnResponse(BaseModel):
    added: list[str]
    added_count: int


@router.post("/skip")
def skip_word(body: SkipRequest) -> dict[str, bool]:
    """User skipped a spelling mark without fixing — queue for admin."""
    return {"ok": record_skip(body.word, body.rule_id)}


@router.post("/learn", response_model=LearnResponse)
def learn(body: LearnRequest, _: AdminDep) -> LearnResponse:
    added = learn_accepted_words(get_engine(), body.text)
    return LearnResponse(added=added, added_count=len(added))


@router.post("/words", response_model=LearnResponse)
def add_words(body: WordsRequest, _: AdminDep) -> LearnResponse:
    dictionary = get_engine().dictionary
    added = dictionary.add_words(body.words)
    if not added:
        added = dictionary.ensure_curated(body.words)
    return LearnResponse(added=added, added_count=len(added))
