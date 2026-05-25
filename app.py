"""tiny-shop FastAPI service.

A minimal order + coupon API used as the implementation target for Symphony
demo runs. Deliberately ships with known issues that the agent is expected to
fix via Linear tickets.
"""
from __future__ import annotations

from enum import Enum

from fastapi import FastAPI, Header, HTTPException

import storage
from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

app = FastAPI(title="tiny-shop", version="0.1.0")


class RouteTag(str, Enum):
    ORDERS = "Orders"
    COUPONS = "Coupons"


@app.post(
    "/orders",
    response_model=Order,
    tags=[RouteTag.ORDERS],
    summary="Create a new order",
)
def create_order(
    payload: OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Order:
    return storage.create_order(payload, idempotency_key=idempotency_key)


@app.get(
    "/orders/{order_id}",
    response_model=Order,
    tags=[RouteTag.ORDERS],
    summary="Get an order by ID",
)
def get_order(order_id: str) -> Order:
    order = storage.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="order not found")
    return order.model_copy()


@app.get(
    "/orders",
    response_model=list[Order],
    tags=[RouteTag.ORDERS],
    summary="List orders",
)
def list_orders() -> list[Order]:
    return storage.list_orders()


@app.post(
    "/orders/{order_id}/cancel",
    response_model=Order,
    tags=[RouteTag.ORDERS],
    summary="Cancel an order",
)
def cancel_order(order_id: str) -> Order:
    order = storage.get_order(order_id)
    if order is not None and order.status not in {OrderStatus.PENDING, OrderStatus.PAID}:
        raise HTTPException(
            status_code=400,
            detail=f"cannot cancel order in status {order.status.value}",
        )
    return storage.update_order_status(order_id, OrderStatus.CANCELLED)


@app.post(
    "/coupons",
    response_model=Coupon,
    tags=[RouteTag.COUPONS],
    summary="Create a coupon",
)
def create_coupon(payload: CouponCreate) -> Coupon:
    return storage.create_coupon(payload)


@app.get(
    "/coupons/{code}",
    response_model=Coupon,
    tags=[RouteTag.COUPONS],
    summary="Get a coupon by code",
)
def get_coupon(code: str) -> Coupon:
    coupon = storage.get_coupon(code)
    if coupon is None:
        raise HTTPException(status_code=404, detail="coupon not found")
    return coupon
