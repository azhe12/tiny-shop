"""Pydantic models for tiny-shop."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


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

    @model_validator(mode="before")
    @classmethod
    def accept_discount_percent(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if data.get("discount") is None and data.get("discount_percent") is not None:
            return {**data, "discount": data["discount_percent"] / 100}
        return data


class CouponCreate(BaseModel):
    code: str
    discount: float | None = None
    discount_percent: float | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def require_discount(self) -> "CouponCreate":
        if self.discount is None and self.discount_percent is None:
            raise ValueError("discount or discount_percent is required")
        return self

    def normalized_discount(self) -> float:
        if self.discount_percent is not None:
            return self.discount_percent / 100
        assert self.discount is not None
        return self.discount
