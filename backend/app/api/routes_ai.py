from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.ai.keys import ai_enabled, save_api_key
from app.core.config import settings
from app.core.plans import effective_check_max_chars
from app.core.user_auth import optional_user

router = APIRouter(prefix="/api/v1", tags=["ai"])


class SettingsResponse(BaseModel):
    ai_enabled: bool
    check_max_chars: int = 1_500
    google_client_id: str | None = None


class KeyRequest(BaseModel):
    key: str = Field(default="", max_length=200)


@router.get("/settings", response_model=SettingsResponse)
def get_settings(
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> SettingsResponse:
    return SettingsResponse(
        ai_enabled=ai_enabled(),
        check_max_chars=effective_check_max_chars(user),
        google_client_id=settings.google_client_id or None,
    )


@router.post("/settings/ai-key", response_model=SettingsResponse)
def set_ai_key(
    body: KeyRequest,
    user: Annotated[dict | None, Depends(optional_user)] = None,
) -> SettingsResponse:
    save_api_key(body.key)
    return SettingsResponse(
        ai_enabled=ai_enabled(),
        check_max_chars=effective_check_max_chars(user),
        google_client_id=settings.google_client_id or None,
    )
