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

## How to run the service locally

```bash
source .venv/bin/activate
uvicorn app:app --reload
```

Then open <http://localhost:8000/docs> for the auto-generated Swagger UI.
