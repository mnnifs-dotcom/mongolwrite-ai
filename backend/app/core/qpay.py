"""QPay merchant API v2 client (auth, invoice, payment check)."""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import httpx

from app.core.config import settings

_log = logging.getLogger(__name__)
_lock = threading.Lock()
_token: str | None = None
_token_expires_at = 0.0


class QPayError(RuntimeError):
    """Raised when QPay API returns an error response."""


def callback_url() -> str:
    configured = settings.qpay_callback_url.strip()
    if configured:
        return configured
    return "https://mongolwrite.com/api/v1/billing/qpay/callback"


def base_url() -> str:
    raw = (settings.qpay_base_url or "https://merchant.qpay.mn/v2").strip().rstrip("/")
    if raw.endswith("/v2"):
        return raw
    return f"{raw}/v2"


def _clear_token() -> None:
    global _token, _token_expires_at
    _token = None
    _token_expires_at = 0.0


def get_access_token(*, force: bool = False) -> str:
    """Fetch (and cache) a QPay bearer token via Basic Auth."""
    global _token, _token_expires_at
    with _lock:
        now = time.time()
        if not force and _token and now < _token_expires_at - 30:
            return _token
        username = settings.qpay_client_id.strip()
        password = settings.qpay_client_secret.strip()
        if not username or not password:
            raise QPayError("QPay нэвтрэх мэдээлэл тохируулаагүй")
        url = f"{base_url()}/auth/token"
        try:
            response = httpx.post(
                url,
                auth=(username, password),
                json={"grant_type": "client_credentials"},
                timeout=20.0,
            )
        except httpx.HTTPError as exc:
            raise QPayError(f"QPay холбогдож чадсангүй: {exc}") from exc
        if response.status_code >= 400:
            raise QPayError(f"QPay нэвтрэлт амжилтгүй ({response.status_code})")
        try:
            data = response.json()
        except ValueError as exc:
            raise QPayError("QPay нэвтрэлтийн хариу буруу") from exc
        token = str(data.get("access_token") or "").strip()
        if not token:
            raise QPayError("QPay access_token олдсонгүй")
        # QPay V2 may return expires_in as a unix timestamp (absolute) or as
        # relative seconds — detect by magnitude (>1e9 ≈ year 2001+).
        expires_in = int(data.get("expires_in") or 3500)
        if expires_in > 1_000_000_000:
            _token_expires_at = float(expires_in)
        else:
            _token_expires_at = now + max(60, expires_in)
        _token = token
        return token


def _authorized_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = get_access_token()
    url = f"{base_url()}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    except httpx.HTTPError as exc:
        raise QPayError(f"QPay хүсэлт амжилтгүй: {exc}") from exc
    if response.status_code == 401:
        # Token may have expired early — refresh once.
        _clear_token()
        token = get_access_token(force=True)
        headers["Authorization"] = f"Bearer {token}"
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
        except httpx.HTTPError as exc:
            raise QPayError(f"QPay хүсэлт амжилтгүй: {exc}") from exc
    if response.status_code >= 400:
        detail = response.text[:300]
        raise QPayError(f"QPay алдаа ({response.status_code}): {detail}")
    try:
        data = response.json()
    except ValueError as exc:
        raise QPayError("QPay хариу JSON биш") from exc
    if not isinstance(data, dict):
        raise QPayError("QPay хариу буруу")
    return data


def create_invoice(
    *,
    sender_invoice_no: str,
    amount_mnt: int,
    description: str,
    receiver_code: str = "terminal",
) -> dict[str, Any]:
    """Create a simple QPay invoice. Returns normalized fields for our order row."""
    invoice_code = settings.qpay_invoice_code.strip()
    if not invoice_code:
        raise QPayError("QPay invoice_code тохируулаагүй")
    payload = {
        "invoice_code": invoice_code,
        "sender_invoice_no": sender_invoice_no,
        "invoice_receiver_code": receiver_code or "terminal",
        "invoice_description": (description or "MongolWrite")[:255],
        "amount": float(amount_mnt),
        "callback_url": callback_url(),
    }
    raw = _authorized_post("/invoice", payload)
    invoice_id = str(raw.get("invoice_id") or raw.get("id") or "").strip()
    if not invoice_id:
        raise QPayError("QPay invoice_id олдсонгүй")
    urls = raw.get("urls") if isinstance(raw.get("urls"), list) else []
    return {
        "invoice_id": invoice_id,
        "qr_text": str(raw.get("qr_text") or raw.get("qPay_QRcode") or "").strip() or None,
        "qr_image": str(raw.get("qr_image") or raw.get("qPay_QRimage") or "").strip() or None,
        "short_url": str(
            raw.get("qPay_shortUrl") or raw.get("qpay_short_url") or raw.get("short_url") or ""
        ).strip()
        or None,
        "urls": urls,
        "raw": raw,
    }


def check_invoice_paid(invoice_id: str) -> dict[str, Any]:
    """Verify payment against QPay. Never trust webhook body alone."""
    cleaned = (invoice_id or "").strip()
    if not cleaned:
        return {"paid": False, "count": 0, "paid_amount": 0, "payment_id": "", "rows": []}
    raw = _authorized_post(
        "/payment/check",
        {
            "object_type": "INVOICE",
            "object_id": cleaned,
            "offset": {"page_number": 1, "page_limit": 100},
        },
    )
    count = int(raw.get("count") or 0)
    rows = raw.get("rows") if isinstance(raw.get("rows"), list) else []
    paid_amount = float(raw.get("paid_amount") or 0)
    payment_id = ""
    if rows and isinstance(rows[0], dict):
        payment_id = str(
            rows[0].get("payment_id")
            or rows[0].get("id")
            or rows[0].get("qpay_payment_id")
            or ""
        ).strip()
    return {
        "paid": count > 0,
        "count": count,
        "paid_amount": paid_amount,
        "payment_id": payment_id,
        "rows": rows,
        "raw": raw,
    }
