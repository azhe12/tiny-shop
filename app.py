"""tiny-shop FastAPI service.

A minimal order + coupon API used as the implementation target for Symphony
demo runs. Deliberately ships with known issues that the agent is expected to
fix via Linear tickets.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Header, HTTPException

import storage
from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

app = FastAPI(title="tiny-shop", version="0.1.0")


def _validate_coupon(coupon_code: str | None) -> None:
    if coupon_code is None:
        return

    coupon = storage.get_coupon(coupon_code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="coupon not found")
    if not coupon.is_active:
        raise HTTPException(status_code=400, detail="coupon inactive")
    if (
        coupon.expires_at is not None
        and coupon.expires_at <= _now_for(coupon.expires_at)
    ):
        raise HTTPException(status_code=400, detail="coupon expired")


def _now_for(expires_at: datetime) -> datetime:
    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        return datetime.now(timezone.utc).replace(tzinfo=None)
    return datetime.now(timezone.utc).astimezone(expires_at.tzinfo)


@app.post("/orders", response_model=Order)
def create_order(
    payload: OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Order:
    _validate_coupon(payload.coupon_code)
    return storage.create_order(payload, idempotency_key=idempotency_key)


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str) -> Order:
    order = storage.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order.model_copy()


@app.get("/orders", response_model=list[Order])
def list_orders() -> list[Order]:
    return storage.list_orders()


@app.post("/orders/{order_id}/cancel", response_model=Order)
def cancel_order(order_id: str) -> Order:
    return storage.update_order_status(order_id, OrderStatus.CANCELLED)


@app.post("/coupons", response_model=Coupon)
def create_coupon(payload: CouponCreate) -> Coupon:
    return storage.create_coupon(payload)


@app.get("/coupons/{code}", response_model=Coupon)
def get_coupon(code: str) -> Coupon:
    coupon = storage.get_coupon(code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="coupon not found")
    return coupon
