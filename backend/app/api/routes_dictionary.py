from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.engine.learn import learn_accepted_words
from app.engine.runtime import get_engine

router = APIRouter(prefix="/api/v1/dictionary", tags=["dictionary"])


class LearnRequest(BaseModel):
    text: str = Field(default="", max_length=500_000)


class WordsRequest(BaseModel):
    words: list[str] = Field(default_factory=list, max_length=5000)


class LearnResponse(BaseModel):
    added: list[str]
    added_count: int


@router.post("/learn", response_model=LearnResponse)
def learn(body: LearnRequest) -> LearnResponse:
    added = learn_accepted_words(get_engine(), body.text)
    return LearnResponse(added=added, added_count=len(added))


@router.post("/words", response_model=LearnResponse)
def add_words(body: WordsRequest) -> LearnResponse:
    added = get_engine().dictionary.add_words(body.words)
    return LearnResponse(added=added, added_count=len(added))
