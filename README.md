# 🧠 SentiTrack AI

> An AI-powered personal journaling backend that turns your daily entries into
> **sentiment insights, weekly summaries, and mood analytics** — built with FastAPI
> and free OpenRouter LLMs.

SentiTrack AI is a production-minded REST backend where users keep a private journal.
Every entry can be analyzed by a large language model to detect **mood, sentiment,
emotions, and confidence**, which then feed into **weekly AI summaries**, **trend
analytics**, and **personalized insights** ("you feel happier on weekends", "stress
increased 20% this month"). It's designed to be clean, modular, and interview-ready.

---

## ✨ Features

- 🔐 **JWT authentication** — register, login, refresh, logout with hashed passwords
- 📓 **Journal CRUD** — create/read/update/delete entries with pagination, sorting & search
- 🤖 **AI sentiment analysis** — mood, sentiment, emotions & confidence via OpenRouter
- 🗓️ **Weekly summaries** — one AI digest + suggestions per week
- 📊 **Analytics** — mood distribution, streaks, averages, monthly/yearly trends
- 🔎 **Advanced search** — keyword, date range, mood & emotion filters
- 💡 **AI insights** — natural-language observations generated from your history
- ⚙️ **Background processing** — analysis runs off the request path
- 🐳 **Dockerized** — app + PostgreSQL via docker-compose

---

## 🧰 Tech Stack

| Layer            | Technology                                   |
|------------------|----------------------------------------------|
| Language         | Python 3.11+                                 |
| Web framework    | FastAPI + Uvicorn                            |
| ORM / migrations | SQLAlchemy 2.0 + Alembic                     |
| Database         | PostgreSQL (prod) · SQLite (zero-config dev) |
| Auth             | PyJWT + bcrypt                               |
| Validation       | Pydantic v2 / pydantic-settings              |
| AI provider      | OpenRouter (free models)                     |
| HTTP client      | httpx                                        |
| Testing          | pytest + FastAPI TestClient                  |
| Packaging        | Docker + docker-compose                      |

---

## 🗂️ Project Structure

```
app/
├── main.py            # App factory, middleware, router wiring
├── core/              # config, logging, security, exceptions
├── database/          # engine, session, declarative Base
├── models/            # SQLAlchemy ORM models
├── schemas/           # Pydantic request/response models
├── dependencies/      # get_db, get_current_user, pagination
├── services/          # business logic (user, auth, journal, ai, ...)
├── api/routes/        # thin HTTP routers per resource
└── middleware/        # request logging etc.
alembic/               # database migrations
docs/usage/            # phase-wise API-flow guides
tests/                 # pytest suite
```

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.11+
- (Optional) PostgreSQL 14+ — SQLite is used by default for local dev

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
Keep the default `DATABASE_URL` (SQLite) for a zero-config run, or point it at PostgreSQL.

### 4. Migrate & run
```bash
alembic upgrade head
uvicorn app.main:app --reload
```

- Swagger UI → http://127.0.0.1:8000/docs
- ReDoc → http://127.0.0.1:8000/redoc
- Health → http://127.0.0.1:8000/health

---

## 📚 API Overview

Feature endpoints live under `/api/v1`. Full request/response examples for each module
are in [`docs/usage/`](docs/usage/).

| Module         | Base path              | Guide                                                        |
|----------------|------------------------|--------------------------------------------------------------|
| Health / meta  | `/`, `/health`         | [phase 1](docs/usage/phase-01-project-init.md)               |
| Database       | —                      | [phase 2](docs/usage/phase-02-database.md)                   |
| Users          | `/api/v1/users`        | [phase 3](docs/usage/phase-03-users.md)                      |
| Auth           | `/api/v1/auth`         | [phase 4](docs/usage/phase-04-authentication.md)             |
| Journals       | `/api/v1/journals`     | [phase 5](docs/usage/phase-05-journal.md)                    |
| Sentiment      | `/api/v1/journals/...` | _coming in Phase 7_                                          |
| Summary        | `/api/v1/summary`      | _coming in Phase 8_                                          |
| Analytics      | `/api/v1/analytics`    | _coming in Phase 9_                                          |
| Search         | `/api/v1/search`       | _coming in Phase 10_                                         |
| Insights       | `/api/v1/insights`     | _coming in Phase 11_                                         |

A consolidated `API.md` reference lands in Phase 16.

---

## 🧭 Roadmap & Status

Built incrementally, one module per phase. Detailed acceptance criteria live in the
local planning docs (`DEVELOPMENT_PLAN.md`, `CHECKLIST.md`).

- ✅ **Phase 1** — Project initialization (health, config, logging)
- ✅ **Phase 2** — Database layer (SQLAlchemy + Alembic)
- ✅ **Phase 3** — User module (register + profile management)
- ✅ **Phase 4** — Authentication (login / refresh / logout)
- ✅ **Phase 5** — Journal CRUD (pagination / sort / search)
- ⏳ **Phase 6** — AI integration (OpenRouter) ← _next_
- ☐ **Phase 7** — Sentiment analysis
- ☐ **Phase 8** — Weekly summaries
- ☐ **Phase 9** — Analytics
- ☐ **Phase 10** — Search
- ☐ **Phase 11** — AI insights
- ☐ **Phase 12–20** — Background tasks, caching, testing, docs, Docker, deployment, production hardening

---

## 🗄️ Database Schema (target)

`users` · `journal_entries` · `sentiments` · `weekly_summaries` · `insights` · `refresh_tokens`

---

## 🤝 Notes

- Uses **free** OpenRouter models only (e.g. `google/gemma-3-27b-it:free`).
- Secrets live in `.env` (git-ignored) — never commit real keys.
