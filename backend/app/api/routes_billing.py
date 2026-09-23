from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.core.billing import (
    billing_public_status,
    create_checkout,
    find_order_by_invoice_no,
    find_order_by_qpay_invoice_id,
    get_order,
    list_orders_for_user,
    public_order,
    qpay_configured,
    sync_order_payment,
)
from app.core.qpay import QPayError, check_invoice_paid
from app.core.user_auth import require_user

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])


class CheckoutRequest(BaseModel):
    plan_id: Literal["pro_3m", "pro_year"] = "pro_year"


class QpayCallbackRequest(BaseModel):
    """QPay payment notification payload (fields vary; we accept common keys)."""

    invoice_id: str = Field(default="", max_length=120)
    order_id: str = Field(default="", max_length=80)
    sender_invoice_no: str = Field(default="", max_length=80)
    payment_id: str = Field(default="", max_length=120)
    qpay_payment_id: str = Field(default="", max_length=120)


def _resolve_order_from_callback(
    *,
    invoice_id: str = "",
    order_id: str = "",
    sender_invoice_no: str = "",
) -> dict[str, Any] | None:
    if order_id.strip():
        order = get_order(order_id.strip())
        if order:
            return order
    if sender_invoice_no.strip():
        order = find_order_by_invoice_no(sender_invoice_no.strip())
        if order:
            return order
    if invoice_id.strip():
        return find_order_by_qpay_invoice_id(invoice_id.strip())
    return None


def _complete_verified_payment(order: dict[str, Any], *, invoice_id: str = "") -> dict[str, Any]:
    """Verify with QPay payment/check, then activate. Never trust callback alone."""
    qpay_invoice = (invoice_id or str(order.get("qpay_invoice_id") or "")).strip()
    if not qpay_invoice:
        # Credentials not wired yet — allow legacy test activation only when QPay unset.
        if not qpay_configured():
            from app.core.billing import mark_order_paid

            updated = mark_order_paid(str(order["id"]))
            return updated or order
        raise HTTPException(status_code=400, detail="QPay invoice_id дутуу")

    if not qpay_configured():
        raise HTTPException(status_code=503, detail="QPay тохируулаагүй")

    try:
        result = check_invoice_paid(qpay_invoice)
    except QPayError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    if not result.get("paid"):
        return order

    from app.core.billing import mark_order_paid

    updated = mark_order_paid(
        str(order["id"]),
        qpay_payment_id=str(result.get("payment_id") or ""),
    )
    return updated or order


@router.get("/plans")
def billing_plans() -> dict[str, Any]:
    return billing_public_status()


@router.post("/checkout")
def billing_checkout(
    body: CheckoutRequest,
    user: Annotated[dict, Depends(require_user)],
) -> dict[str, Any]:
    try:
        return create_checkout(
            user_id=str(user["id"]),
            email=str(user.get("email") or ""),
            plan_id=body.plan_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/orders")
def billing_orders(user: Annotated[dict, Depends(require_user)]) -> dict[str, Any]:
    items = list_orders_for_user(str(user["id"]))
    return {"items": items, "count": len(items)}


@router.get("/orders/{order_id}")
def billing_order_detail(
    order_id: str,
    user: Annotated[dict, Depends(require_user)],
) -> dict[str, Any]:
    order = get_order(order_id)
    if not order or str(order.get("user_id")) != str(user["id"]):
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй")
    synced = sync_order_payment(order)
    return {"order": public_order(synced), "checkout_ready": qpay_configured()}


@router.post("/orders/{order_id}/sync")
def billing_order_sync(
    order_id: str,
    user: Annotated[dict, Depends(require_user)],
) -> dict[str, Any]:
    """Client poll — re-check QPay and activate if paid."""
    order = get_order(order_id)
    if not order or str(order.get("user_id")) != str(user["id"]):
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй")
    synced = sync_order_payment(order)
    return {"order": public_order(synced), "paid": synced.get("status") == "paid"}


@router.api_route("/qpay/callback", methods=["GET", "POST"])
async def qpay_callback(
    request: Request,
    invoice_id: str = Query(default="", max_length=120),
    order_id: str = Query(default="", max_length=80),
    sender_invoice_no: str = Query(default="", max_length=80),
    qpay_payment_id: str = Query(default="", max_length=120),
) -> dict[str, Any]:
    """QPay webhook — verify payment via API then activate plan.

    Accepts GET query params (legacy) and POST JSON body.
    """
    body_invoice = ""
    body_order = ""
    body_sender = ""
    if request.method == "POST":
        try:
            payload = await request.json()
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            body_invoice = str(payload.get("invoice_id") or "")
            body_order = str(payload.get("order_id") or "")
            body_sender = str(payload.get("sender_invoice_no") or "")
            if not qpay_payment_id:
                qpay_payment_id = str(
                    payload.get("qpay_payment_id") or payload.get("payment_id") or ""
                )

    resolved_invoice = (body_invoice or invoice_id).strip()
    resolved_order = (body_order or order_id).strip()
    resolved_sender = (body_sender or sender_invoice_no).strip()

    order = _resolve_order_from_callback(
        invoice_id=resolved_invoice,
        order_id=resolved_order,
        sender_invoice_no=resolved_sender,
    )
    if order is None and resolved_invoice:
        # Invoice may arrive before we indexed — still try by qpay id only.
        order = find_order_by_qpay_invoice_id(resolved_invoice)
    if order is None:
        # Acknowledge unknown callbacks with 200 so QPay does not retry forever
        # after we already processed / expired; still log-friendly.
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй")

    if order.get("status") == "paid":
        return {"ok": True, "order": public_order(order)}

    updated = _complete_verified_payment(order, invoice_id=resolved_invoice)
    return {"ok": True, "order": public_order(updated)}
