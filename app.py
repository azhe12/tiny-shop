"""tiny-shop FastAPI service.

A minimal order + coupon API used as the implementation target for Symphony
demo runs. Deliberately ships with known issues that the agent is expected to
fix via Linear tickets.
"""
from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Callable

from fastapi import FastAPI, HTTPException, Request

import storage
from models import Coupon, CouponCreate, Order, OrderCreate, OrderStatus

app = FastAPI(title="tiny-shop", version="0.1.0")


class SlidingWindowRateLimiter:
    def __init__(
        self,
        max_requests: int,
        window_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clock = clock
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, key: str) -> bool:
        now = self._clock()
        cutoff = now - self.window_seconds
        with self._lock:
            timestamps = self._requests[key]
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= self.max_requests:
                return False

            timestamps.append(now)
            return True

    def configure(self, max_requests: int, window_seconds: float) -> None:
        with self._lock:
            self.max_requests = max_requests
            self.window_seconds = window_seconds
            self._requests.clear()

    def reset(self) -> None:
        with self._lock:
            self._requests.clear()


order_rate_limiter = SlidingWindowRateLimiter(
    max_requests=int(os.getenv("ORDER_RATE_LIMIT_MAX_REQUESTS", "60")),
    window_seconds=float(os.getenv("ORDER_RATE_LIMIT_WINDOW_SECONDS", "60")),
)


@app.post("/orders", response_model=Order)
def create_order(payload: OrderCreate, request: Request) -> Order:
    client_host = request.client.host if request.client else "unknown"
    if not order_rate_limiter.allow(client_host):
        raise HTTPException(status_code=429, detail="too many order requests")
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
