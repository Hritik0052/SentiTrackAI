# Phase 1 — Project Initialization

Boots a clean, scalable FastAPI app with settings, logging, and health endpoints.

## What shipped
- App factory in [`app/main.py`](../../app/main.py) with CORS + lifespan logging
- Settings from env/`.env` in [`app/core/config.py`](../../app/core/config.py)
- Console logging in [`app/core/logging.py`](../../app/core/logging.py)
- Routers wired via [`app/api/router.py`](../../app/api/router.py)
- `GET /` and `GET /health`

## Setup

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env        # then edit values
```

## Run

```bash
uvicorn app.main:app --reload
```

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc:      http://127.0.0.1:8000/redoc

## API flow

### 1. Service metadata
```http
GET /
```
```json
{
  "app": "SentiTrack AI",
  "version": "0.1.0",
  "status": "running",
  "docs": "/docs",
  "redoc": "/redoc",
  "health": "/health"
}
```

### 2. Health check
```http
GET /health
```
```json
{
  "status": "ok",
  "app": "SentiTrack AI",
  "version": "0.1.0",
  "environment": "development"
}
```

## Verify

```bash
curl http://127.0.0.1:8000/
curl http://127.0.0.1:8000/health
```

Both return `200 OK`.
