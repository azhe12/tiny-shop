"""In-memory storage for tiny-shop orders and coupons."""
from __future__ import annotations

import uuid
from datetime import datetime

from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

_orders: dict[str, Order] = {}
_coupons: dict[str, Coupon] = {}
_order_idempotency_keys: dict[str, str] = {}


def _normalize_coupon_code(code: str) -> str:
    return code.strip().upper()


def create_order(payload: OrderCreate, idempotency_key: str | None = None) -> Order:
    if idempotency_key is not None:
        existing_order_id = _order_idempotency_keys.get(idempotency_key)
        if existing_order_id is not None:
            return _orders[existing_order_id]

    coupon_code = (
        _normalize_coupon_code(payload.coupon_code)
        if payload.coupon_code is not None
        else None
    )
    order_id = f"ord-{uuid.uuid4().hex[:12]}"
    order = Order(
        id=order_id,
        customer_id=payload.customer_id,
        items=payload.items,
        amount=payload.amount,
        coupon_code=coupon_code,
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
    _orders[order_id] = order
    return order


def create_coupon(payload: CouponCreate) -> Coupon:
    coupon = Coupon(
        code=_normalize_coupon_code(payload.code),
        discount_percent=payload.discount_percent,
        expires_at=payload.expires_at,
    )
    _coupons[coupon.code] = coupon
    return coupon


def get_coupon(code: str) -> Coupon | None:
    return _coupons.get(_normalize_coupon_code(code))
