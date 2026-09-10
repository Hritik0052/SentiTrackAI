# SentiTrack AI

> An AI-powered personal journaling backend that turns daily entries into
> sentiment insights, weekly summaries, mood analytics, Excel exports, and
> gamification (streaks, XP, badges, challenges) with FastAPI and OpenRouter LLMs.

SentiTrack AI is a REST backend for private journaling. Users can create journal
entries, analyze them for mood and sentiment, generate weekly summaries, review
analytics and multi-line mood trends, export data to Excel, earn XP and badges,
and store AI-generated insights.

---

## Features

- **JWT authentication** — register, login, refresh, logout with hashed passwords
- **Journal CRUD** — create, read, update, delete entries with pagination, sorting, and search
- **AI sentiment analysis** — mood, sentiment, emotion, and confidence via OpenRouter
- **Weekly summaries** — one AI digest plus suggestions per week
- **Analytics** — mood distribution, streaks, averages, monthly/yearly trends
- **Mood trends** — daily multi-line series for sentiment and top emotions (`week` / `month` / custom range)
- **Excel export** — journals, weekly summaries, and monthly summary workbooks (openpyxl)
- **Gamification** — soft streaks with freeze tokens, XP/levels, PNG-key badges, weekly challenges
- **Advanced search** — keyword, date range, mood, emotion, and sentiment filters
- **AI insights** — natural-language observations generated from journal history

---

## Tech Stack

| Layer            | Technology                                      |
|------------------|-------------------------------------------------|
| Language         | Python 3.11+                                    |
| Web framework    | FastAPI + Uvicorn                               |
| ORM / migrations | SQLAlchemy 2.0 + Alembic                        |
| Database         | PostgreSQL / Neon (prod) · SQLite (local default) |
| Auth             | PyJWT + bcrypt                                  |
| Validation       | Pydantic v2 / pydantic-settings                 |
| AI provider      | OpenRouter                                      |
| Excel            | openpyxl                                        |
| HTTP client      | httpx                                           |
| Testing          | pytest + FastAPI TestClient                     |
| Hosting          | Render (`render.yaml`)                          |

---

## Project Structure

```text
app/
  main.py            # App factory, middleware, router wiring
  core/              # config, logging, security, exceptions
  database/          # engine, session, declarative Base
  models/            # SQLAlchemy ORM models (incl. gamification)
  schemas/           # Pydantic request/response models
  dependencies/      # get_db, get_current_user, pagination
  services/          # business logic + gamification hooks
  gamification/      # badge & challenge catalogs
  api/routes/        # thin HTTP routers per resource
alembic/             # database migrations
docs/usage/          # phase-wise API-flow guides
tests/               # pytest suite (incl. trends/export smoke tests)
```

---

## Getting Started

### 1. Prerequisites

- Python 3.11+
- Optional: PostgreSQL / Neon; SQLite is used by default for local development

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
Keep the default `DATABASE_URL` for SQLite, or point it at PostgreSQL/Neon:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST/DB?sslmode=require
```

If you override `DEBUG`, use a boolean-like value such as `true`, `false`, `1`, or `0`.
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

### 5. Tests (optional)

```bash
pytest tests/test_mood_trends_and_export.py -q
```

---

## Render Deployment

Render web services must listen on `0.0.0.0` and the `PORT` environment variable.
Do not use `--reload` on Render.

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
DATABASE_URL=<neon-or-postgres-url>
```

**Note (Render free / no shell):** you can run `alembic upgrade head` locally against
the same Neon `DATABASE_URL` before pushing; Render’s pre-deploy will then usually
be a no-op. This repo includes [`render.yaml`](render.yaml) for Blueprint deploys.

---

## API Overview

Feature endpoints live under `/api/v1`. Full request/response examples for older
modules are in [`docs/usage/`](docs/usage/). Use Swagger for the newest routes.

| Module         | Base path                    | Notes |
|----------------|------------------------------|-------|
| Health / meta  | `/`, `/health`               | Liveness |
| Users          | `/api/v1/users`              | Register / profile |
| Auth           | `/api/v1/auth`               | Login, refresh, logout |
| Journals       | `/api/v1/journals`           | CRUD + analyze (awards XP/badges) |
| Sentiment      | `/api/v1/journals/{id}/...`  | Analyze / read sentiment |
| Summary        | `/api/v1/summary`            | Weekly digests |
| Analytics      | `/api/v1/analytics`          | Dashboard, distribution, monthly/yearly |
| Mood trends    | `/api/v1/analytics/mood-trends` | Week/month multi-line series |
| Mood compare   | `/api/v1/analytics/mood-trends/compare` | Custom range (max 90 days) |
| Export         | `/api/v1/export`             | `.xlsx` journals / summaries / monthly |
| Search         | `/api/v1/search`             | Filters |
| Insights       | `/api/v1/insights`           | AI patterns |
| Gamification   | `/api/v1/gamification`       | `streaks`, `xp`, `badges`, `challenges` |
| Admin          | `/api/v1/admin`              | Plans, users, stats (`is_admin` required) |
| Billing        | `/api/v1/billing`            | Plans, Cashfree checkout + webhook |

### Admin / billing endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/users/me` | Includes `is_admin` + current `plan` |
| GET | `/api/v1/users/me/usage` | Quota used / limit / remaining |
| GET | `/api/v1/admin/stats` | Overview KPIs |
| GET/POST | `/api/v1/admin/plans` | List / create plans |
| GET/PATCH | `/api/v1/admin/plans/{id}` | Read / update plan |
| POST | `/api/v1/admin/plans/{id}/set-default` | Default plan for new users |
| GET | `/api/v1/admin/users` | Paginated users (+ search `q`) |
| GET/PATCH | `/api/v1/admin/users/{id}` | Detail / assign plan / toggle admin |

### Cashfree billing endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/billing/plans` | Active plans (incl. Pro price) |
| GET | `/api/v1/billing/me` | Plan + payment provider + Cashfree ready flag |
| POST | `/api/v1/billing/cashfree/create-order` | Start Pro checkout (auth) |
| POST | `/api/v1/billing/cashfree/webhook` | Cashfree webhook (signature verified; no JWT) |

Set secrets in Render / local `.env` only (`CASHFREE_*`). Configure Cashfree Dashboard webhook URL to the webhook path above.

Create an admin locally:

```powershell
python -m app.cli.create_admin --email YOU@example.com --password "YourStrongPass123" --name "Admin"
```

### Gamification endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/gamification/streaks` | Soft streak, freezes, milestones |
| GET | `/api/v1/gamification/xp` | Level, total XP, recent events |
| GET | `/api/v1/gamification/badges` | Catalog + unlock state (`image_key` → frontend PNGs) |
| GET | `/api/v1/gamification/challenges` | This week’s challenges + progress |

XP is awarded automatically when users create journals, analyze sentiment, generate
weekly summaries / insights, or complete challenges.

### Export endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/export/journals` | Optional `date_from` / `date_to` |
| GET | `/api/v1/export/weekly-summaries` | Optional date filters |
| GET | `/api/v1/export/monthly-summary` | Required `year` & `month` |

---

## Database Schema

Tables:

`users` (incl. `is_admin`), `refresh_tokens`, `journal_entries`, `sentiments`, `weekly_summaries`, `insights`,
`streak_profiles`, `xp_profiles`, `xp_events`, `user_badges`, `user_challenges`,
`subscription_plans`, `user_subscriptions`, `usage_events`

Badge and challenge **definitions** live in code (`app/gamification/`), not in the DB.
Only unlock / progress rows are persisted.

---

## Roadmap And Status

- Done: auth, journals, sentiment, summaries, analytics, search, insights
- Done: mood trends + Excel export
- Done: gamification (streaks 2.0, XP/levels, badges, weekly challenges)
- Done: admin flag, subscription plans, quotas, admin APIs (manual plan assignment)
- Done: Cashfree create-order + webhook Pro upgrade
- Later: background jobs, caching, Docker packaging

See also [`requirement.md`](requirement.md).

---

## Notes

- Uses OpenRouter models configured through environment variables.
- Secrets live in `.env`, which is git-ignored. Never commit real API keys.
