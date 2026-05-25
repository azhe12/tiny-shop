"""Happy-path smoke tests for tiny-shop.

Intentionally does NOT cover the known bugs (no idempotency, no amount
validation, no state-machine checks, no pagination, no coupon validation).
Those gaps exist so Linear tickets can drive the agent to add them.
"""
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import storage
from app import app
from models import OrderStatus

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


def test_create_order_rejects_negative_amount():
    resp = client.post(
        "/orders",
        json={
            "customer_id": "u-negative",
            "items": [{"sku": "A", "qty": 1, "price": 9.9}],
            "amount": -1,
        },
    )
    assert 400 <= resp.status_code < 500


def test_create_order_rejects_zero_item_price():
    resp = client.post(
        "/orders",
        json={
            "customer_id": "u-zero-price",
            "items": [{"sku": "A", "qty": 1, "price": 0}],
            "amount": 9.9,
        },
    )
    assert 400 <= resp.status_code < 500


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


def test_cancel_paid_order_succeeds():
    created = client.post(
        "/orders",
        json={
            "customer_id": "u-005",
            "items": [{"sku": "E", "qty": 1, "price": 75.0}],
            "amount": 75.0,
        },
    ).json()
    storage.update_order_status(created["id"], OrderStatus.PAID)

    resp = client.post(f"/orders/{created['id']}/cancel")

    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


def test_cancel_shipped_order_returns_400():
    created = client.post(
        "/orders",
        json={
            "customer_id": "u-006",
            "items": [{"sku": "F", "qty": 1, "price": 35.0}],
            "amount": 35.0,
        },
    ).json()
    storage.update_order_status(created["id"], OrderStatus.SHIPPED)

    resp = client.post(f"/orders/{created['id']}/cancel")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "cannot cancel order in status SHIPPED"


def test_cancel_cancelled_order_returns_400():
    created = client.post(
        "/orders",
        json={
            "customer_id": "u-006",
            "items": [{"sku": "F", "qty": 1, "price": 25.0}],
            "amount": 25.0,
        },
    ).json()
    first_cancel = client.post(f"/orders/{created['id']}/cancel")
    assert first_cancel.status_code == 200

    resp = client.post(f"/orders/{created['id']}/cancel")

    assert resp.status_code == 400
    assert resp.json()["detail"] == "cannot cancel order in status CANCELLED"


def test_refund_paid_order_records_user_remark():
    created = client.post(
        "/orders",
        json={
            "customer_id": "u-refund",
            "items": [{"sku": "R", "qty": 1, "price": 49.0}],
            "amount": 49.0,
        },
    ).json()
    storage.update_order_status(created["id"], OrderStatus.PAID)
    remark = "Customer requested refund after duplicate purchase."

    resp = client.post(f"/orders/{created['id']}/refund", json={"remark": remark})

    assert resp.status_code == 200
    assert resp.json()["status"] == "REFUNDED"
    assert resp.json()["refund_remark"] == remark

    fetched = client.get(f"/orders/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["refund_remark"] == remark


def test_refund_pending_order_returns_400():
    created = client.post(
        "/orders",
        json={
            "customer_id": "u-refund-pending",
            "items": [{"sku": "R", "qty": 1, "price": 49.0}],
            "amount": 49.0,
        },
    ).json()

    resp = client.post(
        f"/orders/{created['id']}/refund",
        json={"remark": "Please refund before payment."},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "cannot refund order in status PENDING"
    assert client.get(f"/orders/{created['id']}").json()["refund_remark"] is None


def test_refund_missing_order_returns_404():
    resp = client.post(
        "/orders/does-not-exist/refund",
        json={"remark": "Customer submitted a refund request."},
    )

    assert resp.status_code == 404
    assert resp.json() == {"detail": "order not found"}


def test_create_coupon_happy_path():
    resp = client.post(
        "/coupons",
        json={
            "code": "SAVE10",
            "discount_percent": 10,
            "expires_at": (datetime.utcnow() + timedelta(days=30)).isoformat(),
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == "SAVE10"
    assert body["discount_percent"] == 10
    assert body["is_active"] is True


def test_create_coupon_rejects_past_expires_at():
    resp = client.post(
        "/coupons",
        json={
            "code": "EXPIRED",
            "discount_percent": 10,
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
        },
    )

    assert resp.status_code == 400
    assert resp.json() == {"detail": "coupon expires_at must be in the future"}


def test_create_coupon_accepts_future_expires_at():
    resp = client.post(
        "/coupons",
        json={
            "code": "SOON",
            "discount_percent": 10,
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat(),
        },
    )

    assert resp.status_code == 200
    assert resp.json()["code"] == "SOON"


def test_create_coupon_rejects_discount_percent_below_minimum():
    resp = client.post("/coupons", json={"code": "SAVE0", "discount_percent": 0})

    assert 400 <= resp.status_code < 500


def test_create_coupon_rejects_discount_percent_above_maximum():
    resp = client.post("/coupons", json={"code": "SAVE150", "discount_percent": 150})

    assert 400 <= resp.status_code < 500


def test_create_coupon_accepts_discount_percent_boundaries():
    for discount_percent in (1, 100):
        resp = client.post(
            "/coupons",
            json={
                "code": f"SAVE{discount_percent}",
                "discount_percent": discount_percent,
            },
        )

        assert resp.status_code == 200
        assert resp.json()["discount_percent"] == discount_percent


def test_get_coupon_returns_created_one():
    client.post("/coupons", json={"code": "WELCOME", "discount_percent": 20})
    resp = client.get("/coupons/WELCOME")
    assert resp.status_code == 200
    assert resp.json()["discount_percent"] == 20


def test_get_coupon_404_when_missing():
    resp = client.get("/coupons/DOES-NOT-EXIST")
    assert resp.status_code == 404
    assert resp.json() == {"detail": "coupon not found"}
