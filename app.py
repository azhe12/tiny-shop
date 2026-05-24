"""tiny-shop FastAPI service.

A minimal order + coupon API used as the implementation target for Symphony
demo runs. Deliberately ships with known issues that the agent is expected to
fix via Linear tickets.
"""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

import storage
from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

app = FastAPI(title="tiny-shop", version="0.1.0")


def _format_validation_location(location: tuple[str | int, ...]) -> str:
    return ".".join(str(part) for part in location if part != "body")


def _format_validation_message(error: dict[str, Any]) -> str:
    field = _format_validation_location(tuple(error.get("loc", ())))
    if error.get("type") == "greater_than":
        greater_than = error.get("ctx", {}).get("gt")
        if isinstance(greater_than, (int, float)):
            return f"{field} must be greater than {greater_than:g}"
        return f"{field} must be greater than the minimum"

    message = str(error.get("msg", "Invalid request"))
    return f"{field}: {message}" if field else message


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    messages = [_format_validation_message(error) for error in exc.errors()]
    return JSONResponse(
        status_code=400,
        content={"error": "; ".join(messages), "details": messages},
    )


@app.post("/orders", response_model=Order)
def create_order(payload: OrderCreate) -> Order:
    return storage.create_order(payload)


@app.get("/orders/{order_id}", response_model=Order)
def get_order(order_id: str) -> Order:
    order = storage.get_order(order_id)
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
