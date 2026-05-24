"""tiny-shop FastAPI service.

A minimal order + coupon API used as the implementation target for Symphony
demo runs. Deliberately ships with known issues that the agent is expected to
fix via Linear tickets.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

import storage
from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

app = FastAPI(title="tiny-shop", version="0.1.0")


@app.post("/orders", response_model=Order)
def create_order(payload: OrderCreate) -> Order:
    if payload.coupon_code is not None:
        coupon = storage.get_coupon(payload.coupon_code)
        if coupon is None:
            raise HTTPException(status_code=404, detail="coupon not found")
        if not coupon.is_active:
            raise HTTPException(status_code=400, detail="coupon inactive")
        if coupon.expires_at is not None:
            if (
                coupon.expires_at.tzinfo is None
                or coupon.expires_at.utcoffset() is None
            ):
                now = datetime.now(timezone.utc).replace(tzinfo=None)
            else:
                now = datetime.now(tz=coupon.expires_at.tzinfo)
            if coupon.expires_at <= now:
                raise HTTPException(status_code=400, detail="coupon expired")
    return storage.create_order(payload)


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str) -> Order:
    order = storage.get_order(order_id)
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
