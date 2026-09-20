from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.billing import (
    billing_public_status,
    create_checkout,
    find_order_by_invoice_no,
    get_order,
    list_orders_for_user,
    mark_order_paid,
    public_order,
    qpay_configured,
)
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
    return {"order": public_order(order), "checkout_ready": qpay_configured()}


@router.post("/qpay/callback")
def qpay_callback(body: QpayCallbackRequest) -> dict[str, Any]:
    """QPay webhook stub — matches order and activates plan when paid.

    Wire real signature verification when QPay credentials arrive.
    """
    order = None
    if body.order_id.strip():
        order = get_order(body.order_id.strip())
    if order is None and body.sender_invoice_no.strip():
        order = find_order_by_invoice_no(body.sender_invoice_no.strip())
    if order is None:
        raise HTTPException(status_code=404, detail="Захиалга олдсонгүй")

    payment_id = body.qpay_payment_id or body.payment_id or body.invoice_id
    updated = mark_order_paid(str(order["id"]), qpay_payment_id=payment_id)
    return {"ok": True, "order": public_order(updated or order)}
