"""In-memory storage for tiny-shop orders and coupons."""
from __future__ import annotations

import uuid
from datetime import datetime

from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

_orders: dict[str, Order] = {}
_coupons: dict[str, Coupon] = {}
_order_idempotency_keys: dict[str, str] = {}


def create_order(payload: OrderCreate, idempotency_key: str | None = None) -> Order:
    if idempotency_key is not None:
        existing_order_id = _order_idempotency_keys.get(idempotency_key)
        if existing_order_id is not None:
            return _orders[existing_order_id]

    order_id = f"ord-{uuid.uuid4().hex[:12]}"
    order = Order(
        id=order_id,
        customer_id=payload.customer_id,
        items=payload.items,
        amount=round(payload.amount, 2),
        coupon_code=payload.coupon_code,
        created_at=datetime.utcnow(),
    )
    _orders[order_id] = order
    if idempotency_key is not None:
        _order_idempotency_keys[idempotency_key] = order_id
    return order


def get_order(order_id: str) -> Order | None:
    return _orders.get(order_id)


def list_orders() -> list[Order]:
    return list(_orders.values())


def update_order_status(order_id: str, status: OrderStatus) -> Order:
    order = _orders[order_id]
    order.status = status
    order.amount = round(order.amount, 2)
    _orders[order_id] = order
    return order


def create_coupon(payload: CouponCreate) -> Coupon:
    coupon = Coupon(
        code=payload.code,
        discount_percent=payload.discount_percent,
        expires_at=payload.expires_at,
    )
    _coupons[coupon.code] = coupon
    return coupon


def get_coupon(code: str) -> Coupon | None:
    return _coupons.get(code)
