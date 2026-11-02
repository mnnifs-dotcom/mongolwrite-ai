"""In-memory STT submit jobs — audio stays in RAM only until Chimege accepts it."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

from app.core import chimege
from app.core.billing import (
    bind_stt_job,
    clear_stt_job,
    mark_stt_usage_recorded,
    stt_usage_already_recorded,
)
from app.core.chimege_client import ChimegeError, submit_long

_log = logging.getLogger(__name__)
_lock = threading.Lock()

# order_id → job dict. Audio bytes are dropped after Chimege submit (success or fail).
_jobs: dict[str, dict[str, Any]] = {}

PENDING_UUID_PREFIX = "pending:"


def pending_uuid(order_id: str) -> str:
    return f"{PENDING_UUID_PREFIX}{order_id}"


def is_pending_uuid(uuid: str) -> bool:
    return (uuid or "").startswith(PENDING_UUID_PREFIX)


def order_id_from_pending(uuid: str) -> str:
    if not is_pending_uuid(uuid):
        return ""
    return uuid[len(PENDING_UUID_PREFIX) :].strip()


def get_job(order_id: str) -> dict[str, Any] | None:
    with _lock:
        row = _jobs.get(order_id)
        if not row:
            return None
        # Never expose audio bytes to callers.
        return {
            "order_id": order_id,
            "phase": row.get("phase"),
            "uuid": row.get("uuid"),
            "duration": row.get("duration"),
            "error": row.get("error"),
            "started_at": row.get("started_at"),
            "mnt": row.get("mnt"),
            "remaining_seconds": row.get("remaining_seconds"),
            "remaining_hours": row.get("remaining_hours"),
            "filename": row.get("filename"),
        }


def _set_job(order_id: str, **fields: Any) -> None:
    with _lock:
        row = _jobs.setdefault(order_id, {})
        row.update(fields)


def _drop_audio(order_id: str) -> None:
    with _lock:
        row = _jobs.get(order_id)
        if row is not None:
            row["audio"] = b""
            row.pop("audio", None)


def discard_job(order_id: str) -> None:
    with _lock:
        row = _jobs.pop(order_id, None)
        if row is not None:
            row["audio"] = b""


def start_submit_job(
    *,
    order_id: str,
    access_token: str,
    audio: bytes,
    filename: str,
    token: str,
    user_id: str | None,
) -> dict[str, Any]:
    """Queue Chimege submit in a background thread; return pending snapshot immediately."""
    with _lock:
        existing = _jobs.get(order_id)
        if existing and existing.get("phase") in {"queued", "uploading"} and not existing.get("error"):
            # Already running — do not start a second upload for the same paid order.
            return get_job(order_id) or {"phase": "queued", "order_id": order_id}
        _jobs[order_id] = {
            "phase": "queued",
            "uuid": None,
            "duration": 0.0,
            "error": None,
            "started_at": time.time(),
            "audio": audio,
            "filename": filename,
            "access_token": access_token,
            "token": token,
            "user_id": user_id or "",
        }

    def _runner() -> None:
        local_audio = b""
        try:
            with _lock:
                row = _jobs.get(order_id) or {}
                local_audio = row.get("audio") or b""
                row["phase"] = "uploading"
                row["audio"] = b""  # only this thread holds the buffer now
            _log.info(
                "stt job %s uploading to Chimege bytes=%s file=%s",
                order_id,
                len(local_audio),
                filename,
            )
            submitted = submit_long(local_audio, token)
            local_audio = b""
            duration = float(submitted.get("duration") or 0) or 0.5
            uuid = str(submitted.get("uuid") or "").strip()
            if not uuid:
                raise ChimegeError("Chimege UUID ирсэнгүй.", status_code=502)
            bind_stt_job(
                order_id,
                access_token=access_token,
                chimege_uuid=uuid,
                actual_duration_seconds=duration,
            )
            if stt_usage_already_recorded(order_id, access_token):
                status = chimege.public_status()
                usage = {
                    "mnt": 0.0,
                    "remaining_seconds": float(status.get("remaining_seconds") or 0),
                    "remaining_hours": float(status.get("remaining_hours") or 0),
                }
            else:
                usage = chimege.reserve_and_record_usage(
                    duration_seconds=duration,
                    filename=filename,
                    user_id=user_id or None,
                    chimege_uuid=uuid,
                )
                mark_stt_usage_recorded(order_id, access_token=access_token)
            _set_job(
                order_id,
                phase="ready",
                uuid=uuid,
                duration=duration,
                mnt=float(usage.get("mnt") or 0),
                remaining_seconds=float(usage.get("remaining_seconds") or 0),
                remaining_hours=float(usage.get("remaining_hours") or 0),
                error=None,
            )
            _log.info("stt job %s ready uuid=%s duration=%s", order_id, uuid, duration)
        except Exception as exc:  # noqa: BLE001 — surface any submit failure to poller
            _log.warning("stt job %s failed: %s", order_id, exc)
            try:
                clear_stt_job(order_id, access_token=access_token, reason=str(exc))
            except Exception:  # noqa: BLE001
                pass
            _set_job(order_id, phase="error", error=str(exc)[:400], uuid=None)
        finally:
            local_audio = b""
            _drop_audio(order_id)

    # Prefer the running event loop's executor so FastAPI can return immediately.
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _runner)
    except RuntimeError:
        threading.Thread(target=_runner, name=f"stt-submit-{order_id[:8]}", daemon=True).start()

    return get_job(order_id) or {"phase": "queued", "order_id": order_id}


def pending_progress(job: dict[str, Any] | None) -> int:
    if not job:
        return 18
    phase = str(job.get("phase") or "")
    if phase == "ready":
        return 55
    if phase == "error":
        return 0
    started = float(job.get("started_at") or time.time())
    elapsed = max(0.0, time.time() - started)
    # Climb slowly while uploading to Chimege (large m4a can take minutes).
    if phase == "uploading":
        return min(52, 22 + int(elapsed / 8))
    return min(28, 14 + int(elapsed / 6))
