"""Thin Chimege HTTP client — audio stays in memory only, never written to disk."""

from __future__ import annotations

from typing import Any

import httpx

CHIMEGE_BASE = "https://api.chimege.com/v1.2"
# Proxy budget: stream through RAM then discard. Keep modest to protect Fly shared VM.
MAX_UPLOAD_BYTES = 40 * 1024 * 1024
ALLOWED_SUFFIXES = (
    ".wav",
    ".mp3",
    ".m4a",
    ".mp4",
    ".aac",
    ".ogg",
    ".flac",
    ".webm",
    ".wma",
)


class ChimegeError(RuntimeError):
    def __init__(self, message: str, *, status_code: int = 502, error_code: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code


def submit_long(audio: bytes, token: str) -> dict[str, Any]:
    """POST /stt-long → {uuid, duration}. Audio buffer is caller-owned; not stored."""
    if not token.strip():
        raise ChimegeError("Chimege API token байхгүй.", status_code=503, error_code="1001")
    if len(audio) < 2_000:
        raise ChimegeError("Аудио файл хэт жижиг байна.", status_code=400, error_code="2002")
    if len(audio) > MAX_UPLOAD_BYTES:
        raise ChimegeError(
            f"Файл хэт том (дээд хэмжээ {MAX_UPLOAD_BYTES // (1024 * 1024)}MB).",
            status_code=413,
            error_code="2001",
        )
    headers = {
        "Content-Type": "application/octet-stream",
        "Token": token.strip(),
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(120.0, connect=15.0)) as client:
            response = client.post(f"{CHIMEGE_BASE}/stt-long", content=audio, headers=headers)
    except httpx.HTTPError as exc:
        raise ChimegeError(f"Chimege холболт салсан: {exc}", status_code=502) from exc

    if response.status_code == 403:
        code = response.headers.get("Error-Code") or response.headers.get("error-code")
        raise ChimegeError(
            response.text.strip() or "Chimege API token хүчингүй.",
            status_code=403,
            error_code=str(code) if code else "1000",
        )
    if response.status_code >= 400:
        raise ChimegeError(
            response.text.strip() or "Chimege хөрвүүлэлт амжилтгүй.",
            status_code=502,
            error_code=str(response.status_code),
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise ChimegeError("Chimege хариу буруу JSON.", status_code=502) from exc
    uuid = str(payload.get("uuid") or "").strip()
    if not uuid:
        raise ChimegeError("Chimege UUID ирсэнгүй.", status_code=502)
    try:
        duration = float(payload.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return {"uuid": uuid, "duration": max(0.0, duration)}


def fetch_transcript(uuid: str, token: str) -> dict[str, Any]:
    """GET /stt-long-transcript. Does not store result."""
    if not token.strip():
        raise ChimegeError("Chimege API token байхгүй.", status_code=503, error_code="1001")
    if not uuid.strip():
        raise ChimegeError("UUID байхгүй.", status_code=400)
    headers = {"Token": token.strip(), "UUID": uuid.strip()}
    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            response = client.get(f"{CHIMEGE_BASE}/stt-long-transcript", headers=headers)
    except httpx.HTTPError as exc:
        raise ChimegeError(f"Chimege холболт салсан: {exc}", status_code=502) from exc

    if response.status_code == 403:
        code = response.headers.get("Error-Code") or response.headers.get("error-code")
        raise ChimegeError(
            response.text.strip() or "Chimege API token хүчингүй.",
            status_code=403,
            error_code=str(code) if code else "1000",
        )
    if response.status_code >= 400:
        raise ChimegeError(
            response.text.strip() or "Чөлөөт бичвэр уншигдсангүй.",
            status_code=502,
        )
    try:
        payload = response.json()
    except ValueError as exc:
        raise ChimegeError("Chimege хариу буруу JSON.", status_code=502) from exc

    # API sometimes returns a list with one object, sometimes a bare object.
    if isinstance(payload, list):
        row = payload[0] if payload and isinstance(payload[0], dict) else {}
    elif isinstance(payload, dict):
        row = payload
    else:
        row = {}

    if row.get("message") and "uuid" in str(row.get("message")).lower():
        raise ChimegeError(
            "Хөрвүүлэлтийн UUID олдсонгүй эсвэл аль хэдийн дууссан.",
            status_code=404,
        )

    done = bool(row.get("done"))
    text = str(row.get("transcription") or "")
    try:
        duration = float(row.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0.0
    return {"done": done, "transcription": text, "duration": max(0.0, duration)}
