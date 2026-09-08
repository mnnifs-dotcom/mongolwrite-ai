from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class Category(StrEnum):
    SPELLING = "SPELLING"
    GRAMMAR = "GRAMMAR"
    PUNCTUATION = "PUNCTUATION"
    WORD_CHOICE = "WORD_CHOICE"
    STYLE = "STYLE"
    FORMALITY = "FORMALITY"
    CLARITY = "CLARITY"
    REDUNDANCY = "REDUNDANCY"
    TERMINOLOGY = "TERMINOLOGY"
    AI_REWRITE = "AI_REWRITE"


class Source(StrEnum):
    RULE = "RULE"
    DICTIONARY = "DICTIONARY"
    AI = "AI"


class Severity(StrEnum):
    ERROR = "error"
    WARNING = "warning"
    SUGGESTION = "suggestion"


class Correction(BaseModel):
    id: str
    category: Category
    original_text: str
    suggested_text: str
    explanation: str
    confidence: float = Field(ge=0, le=1)
    start: int
    end: int
    source: Source
    rule_id: str
    severity: Severity
    suggestions: list[str] = Field(default_factory=list)
