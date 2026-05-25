"""In-memory storage for tiny-shop orders and coupons."""
from __future__ import annotations

import uuid
from datetime import datetime

from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

_orders: dict[str, Order] = {}
_coupons: dict[str, Coupon] = {}
_order_idempotency_keys: dict[str, str] = {}


def _is_coupon_redeemable(coupon: Coupon) -> bool:
    if not coupon.is_active:
        return False
    if coupon.expires_at is None:
        return True
    return coupon.expires_at > datetime.utcnow()


def _discount_percent(coupon: Coupon) -> float:
    if coupon.discount <= 1:
        return coupon.discount * 100
    return coupon.discount


def _discounted_amount(amount: float, coupon: Coupon) -> float:
    return round(amount * (100 - _discount_percent(coupon)) / 100, 2)


def create_order(payload: OrderCreate, idempotency_key: str | None = None) -> Order:
    if idempotency_key is not None:
        existing_order_id = _order_idempotency_keys.get(idempotency_key)
        if existing_order_id is not None:
            return _orders[existing_order_id]

    amount = payload.amount
    if payload.coupon_code is not None:
        coupon = _coupons.get(payload.coupon_code)
        if coupon is not None and _is_coupon_redeemable(coupon):
            amount = _discounted_amount(amount, coupon)

    order_id = f"ord-{uuid.uuid4().hex[:12]}"
    order = Order(
        id=order_id,
        customer_id=payload.customer_id,
        items=payload.items,
        amount=amount,
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
    _orders[order_id] = order
    return order


def create_coupon(payload: CouponCreate) -> Coupon:
    coupon = Coupon(
        code=payload.code,
        discount=payload.normalized_discount(),
        expires_at=payload.expires_at,
    )
    _coupons[coupon.code] = coupon
    return coupon


def get_coupon(code: str) -> Coupon | None:
    return _coupons.get(code)
