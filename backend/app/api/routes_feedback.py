from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.feedback import add_feedback

router = APIRouter(prefix="/api/v1/feedback", tags=["feedback"])


class FeedbackRequest(BaseModel):
    category: str = Field(default="other", max_length=40)
    message: str = Field(default="", max_length=4000)
    word: str = Field(default="", max_length=200)
    email: str = Field(default="", max_length=200)
    page: str = Field(default="", max_length=200)


class FeedbackResponse(BaseModel):
    ok: bool = True
    id: str


@router.post("", response_model=FeedbackResponse)
def create_feedback(body: FeedbackRequest) -> FeedbackResponse:
    try:
        row = add_feedback(
            category=body.category,
            message=body.message,
            word=body.word,
            email=body.email,
            page=body.page,
        )
    except ValueError as exc:
        if str(exc) == "message_too_short":
            raise HTTPException(status_code=422, detail="Тайлбар хэт богино байна") from exc
        raise HTTPException(status_code=400, detail="Invalid feedback") from exc
    return FeedbackResponse(ok=True, id=str(row["id"]))
