"""QPay merchant API v2 client (auth, refresh, invoice, payment check).

Aligned with https://developer.qpay.mn/docs/merchant?version=2.0.0
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

from app.core.config import settings

_log = logging.getLogger(__name__)
_lock = threading.Lock()
_token: str | None = None
_refresh_token: str | None = None
_token_expires_at = 0.0


class QPayError(RuntimeError):
    """Raised when QPay API returns an error response."""


def callback_url(*, order_id: str = "") -> str:
    """Base webhook URL, optionally stamped with our order_id for reliable matching."""
    configured = settings.qpay_callback_url.strip()
    base = configured or "https://mongolwrite.com/api/v1/billing/qpay/callback"
    oid = (order_id or "").strip()
    if not oid:
        return base
    parts = urlparse(base)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query["order_id"] = oid
    return urlunparse(parts._replace(query=urlencode(query)))


def base_url() -> str:
    raw = (settings.qpay_base_url or "https://merchant.qpay.mn/v2").strip().rstrip("/")
    if raw.endswith("/v2"):
        return raw
    return f"{raw}/v2"


def _clear_token() -> None:
    global _token, _refresh_token, _token_expires_at
    _token = None
    _refresh_token = None
    _token_expires_at = 0.0


def _apply_token_payload(data: dict[str, Any], *, now: float) -> str:
    global _token, _refresh_token, _token_expires_at
    token = str(data.get("access_token") or "").strip()
    if not token:
        raise QPayError("QPay access_token олдсонгүй")
    refresh = str(data.get("refresh_token") or "").strip()
    if refresh:
        _refresh_token = refresh
    # QPay V2 returns expires_in as unix timestamp (absolute) or relative seconds.
    expires_in = int(data.get("expires_in") or 3500)
    if expires_in > 1_000_000_000:
        _token_expires_at = float(expires_in)
    else:
        _token_expires_at = now + max(60, expires_in)
    _token = token
    return token


def _fetch_token_basic() -> str:
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
    if not isinstance(data, dict):
        raise QPayError("QPay нэвтрэлтийн хариу буруу")
    return _apply_token_payload(data, now=time.time())


def _refresh_access_token() -> str | None:
    """POST /v2/auth/refresh with Bearer refresh_token. Returns None if refresh fails."""
    global _refresh_token
    refresh = (_refresh_token or "").strip()
    if not refresh:
        return None
    url = f"{base_url()}/auth/refresh"
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {refresh}"},
            timeout=20.0,
        )
    except httpx.HTTPError:
        _log.exception("QPay token refresh network error")
        return None
    if response.status_code >= 400:
        _log.warning("QPay token refresh failed (%s)", response.status_code)
        return None
    try:
        data = response.json()
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return _apply_token_payload(data, now=time.time())
    except QPayError:
        return None


def get_access_token(*, force: bool = False) -> str:
    """Return a cached access token; refresh when near expiry (docs: avoid re-auth spam)."""
    global _token, _refresh_token, _token_expires_at
    with _lock:
        now = time.time()
        if not force and _token and now < _token_expires_at - 30:
            return _token
        if force:
            _token = None
            _token_expires_at = 0.0
        # Prefer refresh_token over Basic /auth/token (Merchant V2 docs).
        if _refresh_token:
            refreshed = _refresh_access_token()
            if refreshed:
                return refreshed
            _refresh_token = None
        return _fetch_token_basic()


def _authorized_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    token = get_access_token()
    url = f"{base_url()}{path}"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    except httpx.HTTPError as exc:
        raise QPayError(f"QPay хүсэлт амжилтгүй: {exc}") from exc
    if response.status_code == 401:
        # Prefer refresh; fall back to Basic auth once.
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
    order_id: str = "",
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
        "callback_url": callback_url(order_id=order_id),
    }
    raw = _authorized_post("/invoice", payload)
    invoice_id = str(raw.get("invoice_id") or raw.get("id") or "").strip()
    if not invoice_id:
        raise QPayError("QPay invoice_id олдсонгүй")
    urls = raw.get("urls") if isinstance(raw.get("urls"), list) else []
    short = (
        raw.get("qPay_shortUrl")
        or raw.get("qpay_shortUrl")
        or raw.get("qpay_shortlink")
        or raw.get("qPay_shortlink")
        or raw.get("qpay_short_url")
        or raw.get("short_url")
        or ""
    )
    return {
        "invoice_id": invoice_id,
        "qr_text": str(raw.get("qr_text") or raw.get("qPay_QRcode") or "").strip() or None,
        "qr_image": str(raw.get("qr_image") or raw.get("qPay_QRimage") or "").strip() or None,
        "short_url": str(short).strip() or None,
        "urls": urls,
        "raw": raw,
    }


def check_invoice_paid(invoice_id: str) -> dict[str, Any]:
    """Verify payment via POST /v2/payment/check — only after callback or user action."""
    cleaned = (invoice_id or "").strip()
    if not cleaned:
        return {"paid": False, "count": 0, "paid_amount": 0, "payment_id": "", "rows": []}
    raw = _authorized_post(
        "/payment/check",
        {
            "object_type": "INVOICE",
            "object_id": cleaned,
            # Live API requires page_number / page_limit (not page / limit).
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
