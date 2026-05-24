"""In-memory storage for tiny-shop orders and coupons."""
from __future__ import annotations

import uuid
from datetime import datetime
from itertools import islice

from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

_orders: dict[str, Order] = {}
_coupons: dict[str, Coupon] = {}


def create_order(payload: OrderCreate) -> Order:
    order_id = f"ord-{uuid.uuid4().hex[:12]}"
    order = Order(
        id=order_id,
        customer_id=payload.customer_id,
        items=payload.items,
        amount=payload.amount,
        coupon_code=payload.coupon_code,
        created_at=datetime.utcnow(),
    )
    _orders[order_id] = order
    return order


def get_order(order_id: str) -> Order | None:
    return _orders.get(order_id)


def list_orders(limit: int = 20, offset: int = 0) -> list[Order]:
    return list(islice(_orders.values(), offset, offset + limit))


def count_orders() -> int:
    return len(_orders)


def update_order_status(order_id: str, status: OrderStatus) -> Order:
    order = _orders[order_id]
    order.status = status
    _orders[order_id] = order
    return order


def create_coupon(payload: CouponCreate) -> Coupon:
    coupon = Coupon(
        code=payload.code,
        discount=payload.discount,
        expires_at=payload.expires_at,
    )
    _coupons[coupon.code] = coupon
    return coupon


def get_coupon(code: str) -> Coupon | None:
    return _coupons.get(code)
