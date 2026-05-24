"""tiny-shop FastAPI service.

A minimal order + coupon API used as the implementation target for Symphony
demo runs. Deliberately ships with known issues that the agent is expected to
fix via Linear tickets.
"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

import storage
from models import Coupon, CouponCreate, Order, OrderCreate, OrderList, OrderStatus

app = FastAPI(title="tiny-shop", version="0.1.0")


@app.post("/orders", response_model=Order)
def create_order(payload: OrderCreate) -> Order:
    return storage.create_order(payload)


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str) -> Order:
    order = storage.get_order(order_id)
    return order.model_copy()


@app.get("/orders", response_model=OrderList)
def list_orders(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> OrderList:
    return OrderList(
        items=storage.list_orders(limit=limit, offset=offset),
        total=storage.count_orders(),
        limit=limit,
        offset=offset,
    )


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
