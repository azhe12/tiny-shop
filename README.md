# tiny-shop

A tiny FastAPI service that exposes a minimal order + coupon API. Used as the
implementation target for Symphony demo runs.

## API

Start the local service with `uvicorn app:app --reload`. The examples below use
`http://localhost:8000` and the service's in-memory storage.

### POST /orders

Creates an order, stores it in memory with a generated `ord-...` id, and returns
it with `PENDING` status.

```bash
curl -s -X POST http://localhost:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{
    "customer_id": "u-001",
    "items": [{"sku": "A", "qty": 2, "price": 9.9}],
    "amount": 19.8
  }'
```

### GET /orders/{order_id}

Returns a stored order by id.

```bash
ORDER_ID=$(curl -s -X POST http://localhost:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"u-002","items":[{"sku":"B","qty":1,"price":100.0}],"amount":100.0}' \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')

curl -s "http://localhost:8000/orders/${ORDER_ID}"
```

### GET /orders

Returns all orders currently stored in memory.

```bash
curl -s http://localhost:8000/orders
```

### POST /orders/{order_id}/cancel

Sets an existing order's status to `CANCELLED` and returns the updated order.

```bash
ORDER_ID=$(curl -s -X POST http://localhost:8000/orders \
  -H 'Content-Type: application/json' \
  -d '{"customer_id":"u-004","items":[{"sku":"D","qty":1,"price":50.0}],"amount":50.0}' \
  | python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])')

curl -s -X POST "http://localhost:8000/orders/${ORDER_ID}/cancel"
```

### POST /coupons

Stores a coupon by code and returns it with `is_active` set to `true`.

```bash
curl -s -X POST http://localhost:8000/coupons \
  -H 'Content-Type: application/json' \
  -d '{
    "code": "SAVE10",
    "discount": 0.1
  }'
```

### GET /coupons/{code}

Returns a stored coupon by code, or `404` when the coupon does not exist.

```bash
curl -s -X POST http://localhost:8000/coupons \
  -H 'Content-Type: application/json' \
  -d '{"code":"WELCOME","discount":0.2}' >/dev/null

curl -s http://localhost:8000/coupons/WELCOME
```

## How to run tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```

## How to run the service locally

```bash
source .venv/bin/activate
uvicorn app:app --reload
```

Then open <http://localhost:8000/docs> for the auto-generated Swagger UI.
