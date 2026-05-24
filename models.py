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


class OrderItem(BaseModel):
    sku: str
    qty: int = Field(gt=0)
    price: float


class Order(BaseModel):
    id: str
    customer_id: str
    items: list[OrderItem] = Field(min_length=1)
    amount: float
    status: OrderStatus = OrderStatus.PENDING
    coupon_code: str | None = None
    created_at: datetime


class OrderList(BaseModel):
    items: list[Order]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)


class OrderCreate(BaseModel):
    customer_id: str
    items: list[OrderItem] = Field(min_length=1)
    amount: float
    coupon_code: str | None = None


class Coupon(BaseModel):
    code: str
    discount: float
    expires_at: datetime | None = None
    is_active: bool = True


class CouponCreate(BaseModel):
    code: str
    discount: float
    expires_at: datetime | None = None
