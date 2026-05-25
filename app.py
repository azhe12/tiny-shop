"""tiny-shop FastAPI service.

A minimal order + coupon API used as the implementation target for Symphony
demo runs. Deliberately ships with known issues that the agent is expected to
fix via Linear tickets.
"""
from __future__ import annotations

from functools import wraps
from typing import Callable, TypeVar, cast

from fastapi import FastAPI, Header, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import storage
from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

ORDER_RATE_LIMIT = "100/minute"
_ORDER_RATE_LIMIT_CUSTOMER_ATTR = "order_rate_limit_customer_id"

_CreateOrderCallable = TypeVar("_CreateOrderCallable", bound=Callable[..., Order])

app = FastAPI(title="tiny-shop", version="0.1.0")
order_limiter = Limiter(key_func=lambda request: "unknown")
app.state.limiter = order_limiter
app.state.order_rate_limit = ORDER_RATE_LIMIT
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


def get_order_rate_limit() -> str:
    return app.state.order_rate_limit


def get_order_customer_id(request: Request) -> str:
    customer_id = getattr(request.state, _ORDER_RATE_LIMIT_CUSTOMER_ATTR, None)
    return f"customer:{customer_id}" if customer_id else "customer:unknown"


def bind_order_rate_limit_customer(func: _CreateOrderCallable) -> _CreateOrderCallable:
    @wraps(func)
    def wrapper(*args: object, **kwargs: object) -> Order:
        request = kwargs.get("request")
        payload = kwargs.get("payload")

        if request is None:
            request = next((arg for arg in args if isinstance(arg, Request)), None)
        if payload is None:
            payload = next((arg for arg in args if isinstance(arg, OrderCreate)), None)

        if isinstance(request, Request) and isinstance(payload, OrderCreate):
            setattr(request.state, _ORDER_RATE_LIMIT_CUSTOMER_ATTR, payload.customer_id)

        return func(*args, **kwargs)

    return cast(_CreateOrderCallable, wrapper)


@app.post("/orders", response_model=Order)
@bind_order_rate_limit_customer
@order_limiter.limit(get_order_rate_limit, key_func=get_order_customer_id)
def create_order(
    request: Request,
    payload: OrderCreate,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> Order:
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
