"""Happy-path smoke tests for tiny-shop.

Intentionally does NOT cover the known bugs (no idempotency, no amount
validation, no state-machine checks, no pagination, no coupon validation).
Those gaps exist so Linear tickets can drive the agent to add them.
"""
from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from app import app

client = TestClient(app)


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
    body = resp.json()
    assert body["limit"] == 20
    assert body["offset"] == 0
    assert body["total"] >= 1
    assert any(o["customer_id"] == "u-003" for o in body["items"])


def test_list_orders_paginates_with_limit_and_offset():
    start_total = client.get("/orders").json()["total"]
    created_customers = ["page-001", "page-002", "page-003"]
    for customer_id in created_customers:
        client.post(
            "/orders",
            json={
                "customer_id": customer_id,
                "items": [{"sku": "PAGE", "qty": 1, "price": 1.0}],
                "amount": 1.0,
            },
        )

    resp = client.get(f"/orders?limit=2&offset={start_total}")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == start_total + 3
    assert body["limit"] == 2
    assert body["offset"] == start_total
    assert [order["customer_id"] for order in body["items"]] == created_customers[:2]


def test_list_orders_rejects_invalid_limit():
    assert client.get("/orders?limit=0").status_code == 422
    assert client.get("/orders?limit=101").status_code == 422


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
