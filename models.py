"""Pydantic models for tiny-shop."""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    PAID = "PAID"
    SHIPPED = "SHIPPED"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REFUNDED = "REFUNDED"


class OrderItem(BaseModel):
    sku: str
    qty: int = Field(gt=0)
    price: float = Field(gt=0)


class Order(BaseModel):
    id: str
    customer_id: str
    items: list[OrderItem] = Field(min_length=1)
    amount: float = Field(gt=0)
    status: OrderStatus = OrderStatus.PENDING
    coupon_code: str | None = None
    refund_remark: str | None = None
    created_at: datetime


class OrderCreate(BaseModel):
    customer_id: str
    items: list[OrderItem] = Field(min_length=1)
    amount: float = Field(gt=0)
    coupon_code: str | None = None


class OrderRefund(BaseModel):
    remark: str | None = Field(default=None, max_length=500)


class Coupon(BaseModel):
    code: str
    discount_percent: int = Field(ge=1, le=100)
    expires_at: datetime | None = None
    is_active: bool = True


class CouponCreate(BaseModel):
    code: str
    discount_percent: int = Field(ge=1, le=100)
    expires_at: datetime | None = None
