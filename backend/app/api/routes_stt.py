"""Speech-to-text via Chimege — proxy only; never persist uploaded audio."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core import chimege
from app.core.auth import require_admin
from app.core.chimege_client import (
    ALLOWED_SUFFIXES,
    MAX_UPLOAD_BYTES,
    ChimegeError,
    fetch_transcript,
    submit_long,
)
from app.core.devices import DEVICE_HEADER, enforce_device
from app.core.user_auth import optional_user
from app.core.users import touch_last_check

router = APIRouter(prefix="/api/v1/stt", tags=["stt"])
admin_router = APIRouter(prefix="/api/v1/admin/chimege", tags=["admin-chimege"])
_log = logging.getLogger(__name__)

AdminDep = Annotated[None, Depends(require_admin)]
UserDep = Annotated[dict | None, Depends(optional_user)]
DeviceHeader = Annotated[str | None, Header(alias=DEVICE_HEADER)]


class SttPublicStatus(BaseModel):
    enabled: bool
    remaining_seconds: float
    remaining_hours: float
    used_seconds: float
    prepaid_seconds: float
    price_mnt_per_hour: float
    low_balance: bool
    needs_renewal: bool


class SttSubmitResponse(BaseModel):
    uuid: str
    duration_seconds: float
    mnt: float
    remaining_seconds: float
    remaining_hours: float
    price_mnt_per_hour: float


class SttPollResponse(BaseModel):
    done: bool
    transcription: str = ""
    duration_seconds: float = 0.0


class ChimegeAdminUpdate(BaseModel):
    token: str | None = Field(default=None, max_length=200)
    add_prepaid_hours: float | None = Field(default=None, ge=0, le=10_000)
    set_prepaid_hours: float | None = Field(default=None, ge=0, le=10_000)
    price_mnt_per_hour: float | None = Field(default=None, gt=0, le=1_000_000)
    reset_used: bool = False


def _http_from_chimege(exc: ChimegeError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/status", response_model=SttPublicStatus)
def stt_status() -> SttPublicStatus:
    return SttPublicStatus(**chimege.public_status())


@router.post("/transcribe", response_model=SttSubmitResponse)
async def stt_transcribe(
    file: Annotated[UploadFile, File()],
    user: UserDep = None,
    x_mw_device_id: DeviceHeader = None,
) -> SttSubmitResponse:
    """Accept audio in memory → Chimege stt-long → discard bytes. No disk write."""
    status = chimege.public_status()
    if not status["enabled"]:
        raise HTTPException(
            status_code=503,
            detail="Яриа→бичвэр түр унтарсан (API тохируулаагүй).",
        )
    if status["remaining_seconds"] <= 0:
        raise HTTPException(
            status_code=402,
            detail="Урьдчилсан API эрх дууссан. Админ сунгалт хийнэ үү.",
        )

    name = (file.filename or "audio").strip() or "audio"
    lower = name.lower()
    if not any(lower.endswith(suf) for suf in ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=400,
            detail="Зөвшөөрөх өргөтгөл: wav, mp3, m4a, mp4, ogg, flac, webm…",
        )

    # Read once into RAM; never write to persist/.
    audio = await file.read(MAX_UPLOAD_BYTES + 1)
    size = len(audio)
    # Drop reference path after submit — local var goes out of scope.
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Файл хэт том (дээд хэмжээ {MAX_UPLOAD_BYTES // (1024 * 1024)}MB).",
        )
    if size < 2_000:
        raise HTTPException(status_code=400, detail="Аудио файл хэт жижиг байна.")

    if user:
        user_id = str(user.get("id") or "")
        if user_id:
            enforce_device(user_id, x_mw_device_id)
            touch_last_check(user_id)

    token = chimege.get_api_token()
    try:
        submitted = submit_long(audio, token)
    except ChimegeError as exc:
        _log.warning("chimege submit failed: %s", exc)
        raise _http_from_chimege(exc) from exc
    finally:
        # Encourage GC of large buffer ASAP.
        audio = b""

    duration = float(submitted.get("duration") or 0)
    uuid = str(submitted.get("uuid") or "")
    if duration <= 0:
        # Still bill a minimal slice so silent/odd files don't free-ride forever.
        duration = 0.5

    try:
        usage = chimege.reserve_and_record_usage(
            duration_seconds=duration,
            filename=name,
            user_id=str((user or {}).get("id") or "") or None,
            chimege_uuid=uuid,
        )
    except ValueError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc

    price = float(status["price_mnt_per_hour"])
    return SttSubmitResponse(
        uuid=uuid,
        duration_seconds=round(duration, 2),
        mnt=float(usage["mnt"]),
        remaining_seconds=float(usage["remaining_seconds"]),
        remaining_hours=float(usage["remaining_hours"]),
        price_mnt_per_hour=price,
    )


@router.get("/result", response_model=SttPollResponse)
def stt_result(uuid: str) -> SttPollResponse:
    uuid = (uuid or "").strip()
    if not uuid:
        raise HTTPException(status_code=400, detail="UUID оруулна уу.")
    token = chimege.get_api_token()
    if not token:
        raise HTTPException(status_code=503, detail="API тохируулаагүй.")
    try:
        row = fetch_transcript(uuid, token)
    except ChimegeError as exc:
        raise _http_from_chimege(exc) from exc
    return SttPollResponse(
        done=bool(row.get("done")),
        transcription=str(row.get("transcription") or ""),
        duration_seconds=float(row.get("duration") or 0),
    )


@admin_router.get("")
def admin_chimege_get(_: AdminDep) -> dict[str, Any]:
    return chimege.admin_snapshot()


@admin_router.post("")
def admin_chimege_update(body: ChimegeAdminUpdate, _: AdminDep) -> dict[str, Any]:
    add_seconds = None
    set_seconds = None
    if body.add_prepaid_hours is not None:
        add_seconds = float(body.add_prepaid_hours) * 3600.0
    if body.set_prepaid_hours is not None:
        set_seconds = float(body.set_prepaid_hours) * 3600.0
    return chimege.update_admin(
        token=body.token,
        add_prepaid_seconds=add_seconds,
        set_prepaid_seconds=set_seconds,
        price_mnt_per_hour=body.price_mnt_per_hour,
        reset_used=body.reset_used,
    )
