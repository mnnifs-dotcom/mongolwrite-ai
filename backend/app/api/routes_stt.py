"""Speech-to-text via Chimege — pay first (QPay), then proxy; never persist audio."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

from app.core import chimege
from app.core.auth import require_admin
from app.core.billing import (
    clear_stt_job,
    complete_stt_order,
    create_stt_checkout,
    get_stt_order,
    public_order,
    qpay_configured,
    reopen_stt_order_without_transcript,
    sync_order_payment,
)
from app.core.chimege_client import (
    ALLOWED_SUFFIXES,
    MAX_UPLOAD_BYTES,
    ChimegeError,
    fetch_transcript,
    is_failed_transcription,
)
from app.core.devices import DEVICE_HEADER, enforce_device
from app.core.stt_jobs import (
    discard_job,
    get_job,
    is_pending_uuid,
    order_id_from_pending,
    pending_progress,
    pending_uuid,
    start_submit_job,
)
from app.core.stt_history import get_transcript, list_transcripts, save_transcript
from app.core.user_auth import require_user
from app.core.users import touch_last_check

router = APIRouter(prefix="/api/v1/stt", tags=["stt"])
admin_router = APIRouter(prefix="/api/v1/admin/chimege", tags=["admin-chimege"])
_log = logging.getLogger(__name__)

AdminDep = Annotated[None, Depends(require_admin)]
AuthedUser = Annotated[dict, Depends(require_user)]
DeviceHeader = Annotated[str | None, Header(alias=DEVICE_HEADER)]


def _require_order_owner(order: dict[str, Any], user: dict) -> None:
    owner = str(order.get("user_id") or "").strip()
    uid = str(user.get("id") or "").strip()
    if not uid or not owner or owner != uid:
        raise HTTPException(status_code=403, detail="Энэ захиалга таных биш.")


def _save_user_transcript(order: dict[str, Any], *, text: str, chimege_uuid: str = "") -> None:
    uid = str(order.get("user_id") or "").strip()
    if not uid or not (text or "").strip():
        return
    try:
        save_transcript(
            uid,
            transcription=text,
            filename=str(order.get("filename") or ""),
            duration_seconds=float(
                order.get("actual_duration_seconds") or order.get("duration_seconds") or 0
            ),
            amount_mnt=float(order.get("amount_mnt") or 0),
            order_id=str(order.get("id") or ""),
            chimege_uuid=chimege_uuid or str(order.get("chimege_uuid") or ""),
        )
    except Exception:  # noqa: BLE001 — history must not break delivery
        _log.exception("stt history save failed order=%s", order.get("id"))


class SttPublicStatus(BaseModel):
    enabled: bool
    remaining_seconds: float
    remaining_hours: float
    active_remaining_seconds: float = 0.0
    used_seconds: float
    prepaid_seconds: float
    price_mnt_per_hour: float
    low_balance: bool
    needs_renewal: bool
    checkout_ready: bool = False


class SttCheckoutRequest(BaseModel):
    duration_seconds: float = Field(..., gt=0, le=24 * 3600)
    filename: str = Field(default="", max_length=200)


class SttSubmitResponse(BaseModel):
    uuid: str
    duration_seconds: float
    mnt: float
    remaining_seconds: float
    remaining_hours: float
    price_mnt_per_hour: float
    order_id: str = ""
    pending: bool = False
    phase: str = ""


class SttPollResponse(BaseModel):
    done: bool
    transcription: str = ""
    duration_seconds: float = 0.0
    progress_percent: int = 0
    order_completed: bool = False
    uuid: str = ""
    phase: str = ""


class ChimegeAdminUpdate(BaseModel):
    token: str | None = Field(default=None, max_length=200)
    add_prepaid_hours: float | None = Field(default=None, ge=0, le=10_000)
    set_prepaid_hours: float | None = Field(default=None, ge=0, le=10_000)
    price_mnt_per_hour: float | None = Field(default=None, gt=0, le=1_000_000)
    reset_used: bool = False


def _http_from_chimege(exc: ChimegeError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


def _estimate_progress(*, done: bool, duration_seconds: float, started_hint: float = 0.0) -> int:
    """Rough progress for UI when Chimege has no native percent."""
    if done:
        return 100
    if duration_seconds > 0:
        return 62
    return 55


@router.get("/status", response_model=SttPublicStatus)
def stt_status() -> SttPublicStatus:
    row = chimege.public_status()
    row["checkout_ready"] = qpay_configured()
    return SttPublicStatus(**row)


@router.post("/checkout")
def stt_checkout(body: SttCheckoutRequest, user: AuthedUser) -> dict[str, Any]:
    """Quote audio length → QPay invoice. Conversion starts only after payment."""
    status = chimege.public_status()
    if not status["enabled"]:
        raise HTTPException(
            status_code=503,
            detail="Яриа→бичвэр түр унтарсан (API тохируулаагүй).",
        )
    if status["remaining_seconds"] <= 0:
        raise HTTPException(
            status_code=402,
            detail="Үйлчилгээ түр ашиглах боломжгүй.",
        )
    try:
        return create_stt_checkout(
            duration_seconds=body.duration_seconds,
            user_id=str(user.get("id") or ""),
            email=str(user.get("email") or ""),
            filename=body.filename,
            price_mnt_per_hour=float(status["price_mnt_per_hour"]),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/history")
def stt_history(user: AuthedUser) -> dict[str, Any]:
    return {"items": list_transcripts(str(user.get("id") or ""))}


@router.get("/history/{item_id}")
def stt_history_item(item_id: str, user: AuthedUser) -> dict[str, Any]:
    row = get_transcript(str(user.get("id") or ""), item_id)
    if not row:
        raise HTTPException(status_code=404, detail="Бичвэр олдсонгүй")
    return {"item": row}


@router.get("/orders/{order_id}")
def stt_order_detail(order_id: str, user: AuthedUser, access_token: str = "") -> dict[str, Any]:
    order = get_stt_order(order_id, access_token)
    if not order:
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй")
    _require_order_owner(order, user)
    return {
        "order": public_order(order, include_access_token=False),
        "checkout_ready": qpay_configured(),
    }


@router.post("/orders/{order_id}/sync")
def stt_order_sync(order_id: str, user: AuthedUser, access_token: str = "") -> dict[str, Any]:
    order = get_stt_order(order_id, access_token)
    if not order:
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй")
    _require_order_owner(order, user)
    synced = sync_order_payment(order)
    # Re-fetch with token check so response stays scoped.
    fresh = get_stt_order(order_id, access_token) or synced
    return {
        "order": public_order(fresh, include_access_token=False),
        "paid": fresh.get("status") == "paid",
    }


@router.post("/transcribe", response_model=SttSubmitResponse)
async def stt_transcribe(
    file: Annotated[UploadFile, File()],
    user: AuthedUser,
    order_id: Annotated[str, Form()] = "",
    access_token: Annotated[str, Form()] = "",
    x_mw_device_id: DeviceHeader = None,
) -> SttSubmitResponse:
    """Accept paid upload quickly, then submit to Chimege in the background."""
    _log.info("stt transcribe start order=%s filename=%s", order_id, getattr(file, "filename", ""))
    status = chimege.public_status()
    if not status["enabled"]:
        raise HTTPException(
            status_code=503,
            detail="Яриа→бичвэр түр унтарсан (API тохируулаагүй).",
        )
    if status["remaining_seconds"] <= 0:
        raise HTTPException(
            status_code=402,
            detail="Үйлчилгээ түр ашиглах боломжгүй.",
        )

    order = get_stt_order(order_id, access_token)
    if not order:
        raise HTTPException(status_code=402, detail="Эхлээд төлбөрөө төлнө үү.")
    _require_order_owner(order, user)
    if order.get("status") != "paid":
        raise HTTPException(status_code=402, detail="Эхлээд төлбөрөө төлнө үү.")
    if order.get("consumed"):
        cached = str(order.get("transcription") or "").strip()
        existing_uuid = str(order.get("chimege_uuid") or "").strip()
        if cached:
            _save_user_transcript(order, text=cached, chimege_uuid=existing_uuid)
            return SttSubmitResponse(
                uuid=existing_uuid or pending_uuid(order_id),
                duration_seconds=float(
                    order.get("actual_duration_seconds") or order.get("duration_seconds") or 0
                ),
                mnt=float(order.get("amount_mnt") or 0),
                remaining_seconds=float(status["remaining_seconds"]),
                remaining_hours=float(status["remaining_hours"]),
                price_mnt_per_hour=float(status["price_mnt_per_hour"]),
                order_id=order_id,
                pending=False,
                phase="delivered",
            )
        # Legacy: marked delivered but text never cached — reopen for one free retry.
        reopened = reopen_stt_order_without_transcript(order_id, access_token=access_token)
        if not reopened or reopened.get("consumed"):
            raise HTTPException(status_code=409, detail="Энэ төлбөрөөр аль хэдийн хөрвүүлсэн.")
        order = reopened

    price = float(status["price_mnt_per_hour"])
    existing_uuid = str(order.get("chimege_uuid") or "").strip()
    # Paid but convert already submitted — resume polling the same Chimege job.
    if existing_uuid:
        return SttSubmitResponse(
            uuid=existing_uuid,
            duration_seconds=float(
                order.get("actual_duration_seconds") or order.get("duration_seconds") or 0
            ),
            mnt=float(order.get("amount_mnt") or 0),
            remaining_seconds=float(status["remaining_seconds"]),
            remaining_hours=float(status["remaining_hours"]),
            price_mnt_per_hour=price,
            order_id=order_id,
            pending=False,
            phase="ready",
        )

    inflight = get_job(order_id)
    if inflight and inflight.get("phase") == "error":
        discard_job(order_id)
        inflight = None
    if inflight and inflight.get("phase") in {"queued", "uploading", "ready"}:
        real_uuid = str(inflight.get("uuid") or "").strip()
        return SttSubmitResponse(
            uuid=real_uuid or pending_uuid(order_id),
            duration_seconds=float(
                inflight.get("duration") or order.get("duration_seconds") or 0
            ),
            mnt=float(order.get("amount_mnt") or 0),
            remaining_seconds=float(status["remaining_seconds"]),
            remaining_hours=float(status["remaining_hours"]),
            price_mnt_per_hour=price,
            order_id=order_id,
            pending=not bool(real_uuid),
            phase=str(inflight.get("phase") or "queued"),
        )

    name = (file.filename or "audio").strip() or "audio"
    lower = name.lower()
    if not any(lower.endswith(suf) for suf in ALLOWED_SUFFIXES):
        raise HTTPException(
            status_code=400,
            detail="Зөвшөөрөх өргөтгөл: wav, mp3, m4a, mp4, ogg, flac, webm…",
        )

    # Read once into RAM; never write to persist/. Return before Chimege upload.
    audio = await file.read(MAX_UPLOAD_BYTES + 1)
    size = len(audio)
    if size > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Файл хэт том (дээд хэмжээ {MAX_UPLOAD_BYTES // (1024 * 1024)}MB).",
        )
    if size < 2_000:
        raise HTTPException(status_code=400, detail="Аудио файл хэт жижиг байна.")

    user_id = str(user.get("id") or "")
    if user_id:
        enforce_device(user_id, x_mw_device_id)
        touch_last_check(user_id)

    token = chimege.get_api_token()
    if not token:
        raise HTTPException(status_code=503, detail="API тохируулаагүй.")

    job = start_submit_job(
        order_id=order_id,
        access_token=access_token,
        audio=audio,
        filename=name,
        token=token,
        user_id=user_id or None,
    )
    audio = b""
    _log.info(
        "stt transcribe accepted order=%s bytes=%s phase=%s",
        order_id,
        size,
        job.get("phase"),
    )

    return SttSubmitResponse(
        uuid=pending_uuid(order_id),
        duration_seconds=float(order.get("duration_seconds") or 0),
        mnt=float(order.get("amount_mnt") or 0),
        remaining_seconds=float(status["remaining_seconds"]),
        remaining_hours=float(status["remaining_hours"]),
        price_mnt_per_hour=price,
        order_id=order_id,
        pending=True,
        phase=str(job.get("phase") or "queued"),
    )


@router.get("/result", response_model=SttPollResponse)
def stt_result(
    user: AuthedUser,
    uuid: str,
    order_id: str = "",
    access_token: str = "",
) -> SttPollResponse:
    uuid = (uuid or "").strip()
    order_id = (order_id or "").strip()
    if is_pending_uuid(uuid) and not order_id:
        order_id = order_id_from_pending(uuid)

    # Served transcript from a completed paid order (Chimege deletes UUID quickly).
    if order_id and access_token:
        order = get_stt_order(order_id, access_token)
        if order:
            _require_order_owner(order, user)
        if order and order.get("consumed"):
            cached = str(order.get("transcription") or "").strip()
            if cached:
                _save_user_transcript(
                    order,
                    text=cached,
                    chimege_uuid=str(order.get("chimege_uuid") or uuid),
                )
                return SttPollResponse(
                    done=True,
                    transcription=cached,
                    duration_seconds=float(
                        order.get("actual_duration_seconds") or order.get("duration_seconds") or 0
                    ),
                    progress_percent=100,
                    order_completed=True,
                    uuid=str(order.get("chimege_uuid") or uuid),
                    phase="delivered",
                )

    # Background submit still running (or failed).
    if order_id:
        job = get_job(order_id)
        if job:
            phase = str(job.get("phase") or "")
            if phase == "error":
                detail = str(job.get("error") or "Хөрвүүлэлт амжилтгүй")
                discard_job(order_id)
                raise HTTPException(status_code=502, detail=detail)
            real_uuid = str(job.get("uuid") or "").strip()
            if not real_uuid:
                return SttPollResponse(
                    done=False,
                    transcription="",
                    duration_seconds=float(job.get("duration") or 0),
                    progress_percent=pending_progress(job),
                    uuid=pending_uuid(order_id),
                    phase=phase or "queued",
                )
            uuid = real_uuid

    if not uuid or is_pending_uuid(uuid):
        # Still waiting for background bind — keep polling.
        if order_id:
            order = get_stt_order(order_id, access_token) if access_token else None
            bound = str((order or {}).get("chimege_uuid") or "").strip()
            if bound:
                uuid = bound
            else:
                return SttPollResponse(
                    done=False,
                    progress_percent=24,
                    uuid=pending_uuid(order_id) if order_id else "",
                    phase="queued",
                )
        else:
            raise HTTPException(status_code=400, detail="UUID оруулна уу.")

    token = chimege.get_api_token()
    if not token:
        raise HTTPException(status_code=503, detail="API тохируулаагүй.")
    try:
        row = fetch_transcript(uuid, token)
    except ChimegeError as exc:
        if exc.status_code == 404 and order_id and access_token:
            # Dead UUID — free the paid order so the client can re-upload.
            clear_stt_job(order_id, access_token=access_token, reason=str(exc))
            discard_job(order_id)
        raise _http_from_chimege(exc) from exc

    done = bool(row.get("done"))
    duration = float(row.get("duration") or 0)
    text = str(row.get("transcription") or "")
    order_completed = False

    if done and is_failed_transcription(text):
        if order_id and access_token:
            clear_stt_job(
                order_id,
                access_token=access_token,
                reason="chimege failed transcription",
            )
            discard_job(order_id)
        raise HTTPException(
            status_code=422,
            detail="Аудиог бичвэр болгож чадсангүй. Өөр файл туршина уу.",
        )

    if done and order_id and access_token:
        try:
            completed = complete_stt_order(
                order_id,
                access_token=access_token,
                chimege_uuid=uuid,
                transcription=text,
            )
            order_completed = True
            discard_job(order_id)
            _save_user_transcript(completed, text=text, chimege_uuid=uuid)
        except ValueError:
            order_completed = False

    return SttPollResponse(
        done=done,
        transcription=text if done else "",
        duration_seconds=duration,
        progress_percent=_estimate_progress(done=done, duration_seconds=duration),
        order_completed=order_completed,
        uuid=uuid,
        phase="done" if done else "processing",
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
