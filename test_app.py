"""Happy-path smoke tests for tiny-shop.

Intentionally does NOT cover the known bugs (no idempotency, no amount
validation, no state-machine checks, no pagination, no coupon validation).
Those gaps exist so Linear tickets can drive the agent to add them.
"""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

import storage
from app import ORDER_RATE_LIMIT, app, order_limiter

client = TestClient(app)


def setup_function():
    order_limiter.reset()
    app.state.order_rate_limit = ORDER_RATE_LIMIT


def test_create_order_happy_path():
    resp = client.post(
        "/orders",
        json={
            "customer_id": "u-001",
            "items": [{"sku": "A", "qty": 2, "price": 9.9}],
            "amount": 19.8,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["customer_id"] == "u-001"
    assert body["amount"] == 19.8
    assert body["status"] == "PENDING"
    assert body["id"].startswith("ord-")


def test_create_order_with_idempotency_key_returns_existing_order_without_insert():
    payload = {
        "customer_id": "u-idempotent",
        "items": [{"sku": "A", "qty": 2, "price": 9.9}],
        "amount": 19.8,
    }
    headers = {"Idempotency-Key": "retry-create-order-u-idempotent"}
    before_count = len(storage._orders)

    first = client.post("/orders", json=payload, headers=headers)
    assert first.status_code == 200
    after_first_count = len(storage._orders)

    second = client.post("/orders", json=payload, headers=headers)
    assert second.status_code == 200

    assert after_first_count == before_count + 1
    assert second.json() == first.json()
    assert len(storage._orders) == after_first_count


def test_create_order_without_idempotency_key_still_creates_new_orders():
    payload = {
        "customer_id": "u-no-idempotency",
        "items": [{"sku": "A", "qty": 1, "price": 9.9}],
        "amount": 9.9,
    }
    before_count = len(storage._orders)

    first = client.post("/orders", json=payload)
    second = client.post("/orders", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] != second.json()["id"]
    assert len(storage._orders) == before_count + 2


def test_create_order_rate_limit_returns_429_for_same_customer():
    app.state.order_rate_limit = "2/minute"
    payload = {
        "customer_id": "u-rate-limited",
        "items": [{"sku": "A", "qty": 1, "price": 9.9}],
        "amount": 9.9,
    }

    first = client.post("/orders", json=payload)
    second = client.post("/orders", json=payload)
    third = client.post("/orders", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert "Rate limit exceeded" in third.json()["error"]


def test_create_order_rate_limit_is_scoped_by_customer_id():
    app.state.order_rate_limit = "1/minute"
    payload = {
        "customer_id": "u-rate-limit-a",
        "items": [{"sku": "A", "qty": 1, "price": 9.9}],
        "amount": 9.9,
    }
    other_customer_payload = payload | {"customer_id": "u-rate-limit-b"}

    assert client.post("/orders", json=payload).status_code == 200
    assert client.post("/orders", json=payload).status_code == 429
    assert client.post("/orders", json=other_customer_payload).status_code == 200


def test_get_order_returns_created_one():
    created = client.post(
        "/orders",
        json={
            "customer_id": "u-002",
            "items": [{"sku": "B", "qty": 1, "price": 100.0}],
            "amount": 100.0,
        },
    ).json()
    resp = client.get(f"/orders/{created['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


def test_get_order_404_when_missing():
    resp = client.get("/orders/does-not-exist")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "order not found"}


def test_list_orders_includes_created():
    client.post(
        "/orders",
        json={
            "customer_id": "u-003",
            "items": [{"sku": "C", "qty": 3, "price": 5.0}],
            "amount": 15.0,
        },
    )
    resp = client.get("/orders")
    assert resp.status_code == 200
    assert any(o["customer_id"] == "u-003" for o in resp.json())


def test_cancel_pending_order_succeeds():
    created = client.post(
        "/orders",
        json={
            "customer_id": "u-004",
            "items": [{"sku": "D", "qty": 1, "price": 50.0}],
            "amount": 50.0,
        },
    ).json()
    resp = client.post(f"/orders/{created['id']}/cancel")
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_create_coupon_happy_path():
    resp = client.post(
        "/coupons",
        json={
            "code": "SAVE10",
            "discount": 0.1,
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "SAVE10"
    assert body["is_active"] is True


def test_get_coupon_returns_created_one():
    client.post("/coupons", json={"code": "WELCOME", "discount": 0.2})
    resp = client.get("/coupons/WELCOME")
    assert resp.status_code == 200
    assert resp.json()["discount"] == 0.2


def test_get_coupon_404_when_missing():
    resp = client.get("/coupons/NOPE-DOES-NOT-EXIST")
    assert resp.status_code == 404
