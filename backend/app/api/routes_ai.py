from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.ai.keys import ai_enabled, save_api_key

router = APIRouter(prefix="/api/v1", tags=["ai"])


class SettingsResponse(BaseModel):
    ai_enabled: bool


class KeyRequest(BaseModel):
    key: str = Field(default="", max_length=200)


@router.get("/settings", response_model=SettingsResponse)
def get_settings() -> SettingsResponse:
    return SettingsResponse(ai_enabled=ai_enabled())


@router.post("/settings/ai-key", response_model=SettingsResponse)
def set_ai_key(body: KeyRequest) -> SettingsResponse:
    save_api_key(body.key)
    return SettingsResponse(ai_enabled=ai_enabled())
