# SentiTrack AI

> An AI-powered personal journaling backend that turns daily entries into
> sentiment insights, weekly summaries, and mood analytics with FastAPI and
> OpenRouter LLMs.

SentiTrack AI is a REST backend for private journaling. Users can create journal
entries, analyze them for mood and sentiment, generate weekly summaries, review
analytics, search their history, and store AI-generated insights. The project is
being built incrementally by phase.

---

## Features

Completed through Phase 11:

- **JWT authentication** - register, login, refresh, logout with hashed passwords
- **Journal CRUD** - create, read, update, delete entries with pagination, sorting, and search
- **AI sentiment analysis** - mood, sentiment, emotion, and confidence via OpenRouter
- **Weekly summaries** - one AI digest plus suggestions per week
- **Analytics** - mood distribution, streaks, averages, monthly trends, and yearly trends
- **Advanced search** - keyword, date range, mood, emotion, and sentiment filters
- **AI insights** - natural-language observations generated from journal history

Planned in later phases:

- **Background processing** - analysis runs off the request path (Phase 12)
- **Caching** - Redis cache for dashboard/summary where useful (Phase 13)
- **Testing** - pytest suite with FastAPI TestClient (Phase 15)
- **API documentation** - consolidated `API.md` (Phase 16)
- **Dockerized runtime** - app plus PostgreSQL via docker-compose (Phase 17)
- **Deployment and production hardening** - deployment notes, rate limiting, security headers, and CI/CD (Phases 18-20)

---

## Tech Stack

| Layer            | Technology                                      |
|------------------|-------------------------------------------------|
| Language         | Python 3.11+                                    |
| Web framework    | FastAPI + Uvicorn                               |
| ORM / migrations | SQLAlchemy 2.0 + Alembic                        |
| Database         | PostgreSQL (prod) / SQLite (zero-config dev)    |
| Auth             | PyJWT + bcrypt                                  |
| Validation       | Pydantic v2 / pydantic-settings                 |
| AI provider      | OpenRouter                                      |
| HTTP client      | httpx                                           |
| Testing          | pytest + FastAPI TestClient (planned Phase 15)  |
| Packaging        | Docker + docker-compose (planned Phase 17)      |

---

## Project Structure

```text
app/
  main.py            # App factory, middleware, router wiring
  core/              # config, logging, security, exceptions
  database/          # engine, session, declarative Base
  models/            # SQLAlchemy ORM models
  schemas/           # Pydantic request/response models
  dependencies/      # get_db, get_current_user, pagination
  services/          # business logic
  api/routes/        # thin HTTP routers per resource
alembic/             # database migrations
docs/usage/          # phase-wise API-flow guides
tests/               # planned pytest suite
```

---

## Getting Started

### 1. Prerequisites

- Python 3.11+
- Optional: PostgreSQL 14+; SQLite is used by default for local development

### 2. Install

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
```

Edit `.env` and set at least `JWT_SECRET_KEY` and your `OPENROUTER_API_KEY`.
Keep the default `DATABASE_URL` for SQLite, or point it at PostgreSQL.

If you override `DEBUG`, use a boolean-like value such as `true`, `false`, `1`, or `0`.
Values like `release` are invalid for the current Pydantic settings field.
`HOST` and `PORT` control the settings-driven server runner used by `python -m app.main`.

### 4. Migrate And Run

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

Or run through `.env` host/port settings:

```bash
python -m app.main
```

- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health: http://127.0.0.1:8000/health

---

## Render Deployment

Render web services must listen on the host `0.0.0.0` and the port provided by
the `PORT` environment variable. This project supports that through `HOST` and
`PORT` settings loaded from the environment. Do not use `--reload` on Render.

Manual Render settings:

```text
Language: Python 3
Build Command: pip install -r requirements.txt
Pre-Deploy Command: alembic upgrade head
Start Command: python -m app.main
Health Check Path: /health
```

Required Render environment variables:

```text
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=10000
JWT_SECRET_KEY=<long-random-secret>
OPENROUTER_API_KEY=<your-openrouter-key>
DATABASE_URL=<render-postgres-internal-database-url>
```

This repository also includes [`render.yaml`](render.yaml) with the same service
configuration for Render Blueprint deployments.

---

## API Overview

Feature endpoints live under `/api/v1`. Full request/response examples for each
module are in [`docs/usage/`](docs/usage/).

| Module        | Base path              | Guide                                             |
|---------------|------------------------|---------------------------------------------------|
| Health / meta | `/`, `/health`         | [phase 1](docs/usage/phase-01-project-init.md)    |
| Database      | N/A                    | [phase 2](docs/usage/phase-02-database.md)        |
| Users         | `/api/v1/users`        | [phase 3](docs/usage/phase-03-users.md)           |
| Auth          | `/api/v1/auth`         | [phase 4](docs/usage/phase-04-authentication.md)  |
| Journals      | `/api/v1/journals`     | [phase 5](docs/usage/phase-05-journal.md)         |
| Sentiment     | `/api/v1/journals/...` | [phase 7](docs/usage/phase-07-sentiment.md)       |
| Summary       | `/api/v1/summary`      | [phase 8](docs/usage/phase-08-weekly-summary.md)  |
| Analytics     | `/api/v1/analytics`    | [phase 9](docs/usage/phase-09-analytics.md)       |
| Search        | `/api/v1/search`       | [phase 10](docs/usage/phase-10-search.md)         |
| Insights      | `/api/v1/insights`     | [phase 11](docs/usage/phase-11-insights.md)       |

A consolidated `API.md` reference is planned for Phase 16.

---

## Roadmap And Status

Detailed acceptance criteria live in [`DEVELOPMENT_PLAN.md`](DEVELOPMENT_PLAN.md),
[`CHECKLIST.md`](CHECKLIST.md), and [`requirement.md`](requirement.md).

- Done: **Phase 1** - Project initialization
- Done: **Phase 2** - Database layer
- Done: **Phase 3** - User module
- Done: **Phase 4** - Authentication
- Done: **Phase 5** - Journal CRUD
- Done: **Phase 6** - AI integration
- Done: **Phase 7** - Sentiment analysis
- Done: **Phase 8** - Weekly summaries
- Done: **Phase 9** - Analytics
- Done: **Phase 10** - Search
- Done: **Phase 11** - AI insights
- Pending: **Phase 12-20** - Background tasks, caching, testing, docs, Docker, deployment, and production hardening

---

## Database Schema

Current planned schema:

`users`, `journal_entries`, `sentiments`, `weekly_summaries`, `insights`, `refresh_tokens`

---

## Notes

- Uses OpenRouter models configured through environment variables.
- Secrets live in `.env`, which is git-ignored. Never commit real API keys.
