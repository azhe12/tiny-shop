# tiny-shop

A tiny FastAPI service that exposes a minimal order + coupon API. Used as the
implementation target for Symphony demo runs.

## How to run tests

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```

## Dependencies

| Library | Version | Purpose |
| --- | --- | --- |
| fastapi | 0.110.0 | Provides the web framework used to define the order and coupon API endpoints. |
| uvicorn | 0.27.0 | Runs the FastAPI application as an ASGI server during local development. |
| pytest | 8.0.0 | Runs the automated test suite for the service. |
| httpx | 0.27.0 | Supplies the HTTP client used by FastAPI's test client in the pytest suite. |

## How to run the service locally

```bash
source .venv/bin/activate
uvicorn app:app --reload
```

Then open <http://localhost:8000/docs> for the auto-generated Swagger UI.

## Refund an order

Paid, shipped, and delivered orders can be refunded with an optional user
remark:

```bash
curl -X POST http://localhost:8000/orders/ord-example/refund \
  -H "Content-Type: application/json" \
  -d '{"remark": "Customer requested refund after duplicate purchase."}'
```

The response includes `status: "REFUNDED"` and the stored `refund_remark`.
