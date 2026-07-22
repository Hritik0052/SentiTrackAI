# Phase 11 — AI Insights

Turns a user's whole journaling history into short, natural-language observations.
`POST /insights/generate` builds a compact context from the Phase 9 analytics dashboard
plus the user's most recent entries, asks the AI for 3–5 insight sentences, and stores
each as an `insights` row. `GET /insights` pages through them, newest first.

## What shipped
- `Insight` model + `User.insights` relationship —
  [`app/models/insight.py`](../../app/models/insight.py)
- `generate_insights()` on the AI service (JSON array of sentences) —
  [`app/services/ai_service.py`](../../app/services/ai_service.py)
- Schemas (`InsightRead`, `InsightListResponse`) —
  [`app/schemas/insight.py`](../../app/schemas/insight.py)
- Insight service (context assembly, generate + store, paginated list) —
  [`app/services/insight_service.py`](../../app/services/insight_service.py)
- Insights router — [`app/api/routes/insights.py`](../../app/api/routes/insights.py)
- Migration: `create insights table`

All endpoints require a valid access token and are scoped to the caller.

## Data model
`insights` is an append-only log — one row per generated statement.

| Column       | Type     | Notes                                   |
|--------------|----------|-----------------------------------------|
| `id`         | int PK   |                                         |
| `user_id`    | int      | FK → `users.id`, cascade delete         |
| `content`    | text     | one natural-language insight sentence   |
| `created_at` / `updated_at` | datetime | generation time |

Each call to `generate` **appends a new batch** (it does not replace prior insights),
so history accumulates over time and the list endpoint paginates it.

## How the context is built
`generate` sends the AI a plain-text summary rather than raw rows: aggregate stats from
the analytics dashboard (totals, sentiment counts, average confidence, most-common
emotion/mood, current/longest streaks, entries this week/month) followed by the 10 most
recent entries (date + a 200-char preview). This keeps prompts small and grounded.

## Endpoints

| Method | Path                          | Auth | Description                              |
|--------|-------------------------------|------|------------------------------------------|
| POST   | `/api/v1/insights/generate`   | JWT  | Generate + store a fresh batch of insights |
| GET    | `/api/v1/insights`            | JWT  | List insights (newest first, paginated)   |

## API flow

### 1. Generate
```http
POST /api/v1/insights/generate
Authorization: Bearer <access_token>
```
`201 Created` — the newly created batch:
```json
[
  { "id": 12, "content": "You journal most consistently on weekends.", "created_at": "2026-07-22T14:25:01" },
  { "id": 13, "content": "Your mood trends more positive after exercise.", "created_at": "2026-07-22T14:25:01" },
  { "id": 14, "content": "Your journaling streak has been strong this month.", "created_at": "2026-07-22T14:25:01" }
]
```
No entries yet → `400`:
```json
{ "error": { "type": "BadRequestError", "detail": "No journal entries to generate insights from" } }
```

### 2. List
```http
GET /api/v1/insights?page=1&page_size=20
Authorization: Bearer <access_token>
```
`200 OK`
```json
{
  "items": [ { "id": 14, "content": "...", "created_at": "..." } ],
  "total": 6,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```
- `page` (default 1), `page_size` (default 20, max 100)
- Ordered by `created_at` descending (ties broken by `id` descending)

## Error envelope
```json
{ "error": { "type": "<ExceptionName>", "detail": "<message or field errors>" } }
```
- No/invalid token → `401 UnauthorizedError`
- No entries to analyze → `400 BadRequestError`
- AI provider unavailable / malformed / empty → `502 AIServiceError`

## Verify (fresh DB)
```bash
alembic upgrade head
uvicorn app.main:app --reload
# register + login, create a few entries (analyze some for richer context), then:
#   POST /api/v1/insights/generate   -> stores a batch (needs OPENROUTER_API_KEY)
#   GET  /api/v1/insights            -> lists them, newest first
```
