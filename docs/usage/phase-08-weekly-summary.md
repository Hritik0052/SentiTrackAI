# Phase 8 — Weekly Summary

Rolls a week of journal entries into a single AI digest plus actionable suggestions.
`POST /summary/weekly` gathers the caller's entries for a Monday–Sunday week, sends them
through the Phase 6 `AIService` weekly-digest prompt, and stores one `weekly_summaries`
row per (user, week). `GET` endpoints read them back.

## What shipped
- `WeeklySummary` model + `User.weekly_summaries` relationship —
  [`app/models/weekly_summary.py`](../../app/models/weekly_summary.py)
- `generate_weekly_summary()` on the AI service (returns `{summary, suggestions}`) —
  [`app/services/ai_service.py`](../../app/services/ai_service.py)
- Schemas (`WeeklySummaryGenerate`, `WeeklySummaryRead`) —
  [`app/schemas/summary.py`](../../app/schemas/summary.py)
- Summary service (week bounds, entry gathering, upsert) —
  [`app/services/summary_service.py`](../../app/services/summary_service.py)
- Summary router — [`app/api/routes/summary.py`](../../app/api/routes/summary.py)
- Migration: `create weekly_summaries table`

All endpoints require a valid access token and are scoped to the caller. Requesting
another user's summary returns the same `404` as a nonexistent one.

## Data model
`weekly_summaries` has a **unique (`user_id`, `week_start`)** constraint, so each user has
at most one summary per week; regenerating the same week upserts that row.

| Column        | Type      | Notes                                            |
|---------------|-----------|--------------------------------------------------|
| `id`          | int PK    |                                                  |
| `user_id`     | int       | FK → `users.id`, cascade delete                  |
| `week_start`  | date      | Monday of the week                               |
| `week_end`    | date      | Sunday of the week                               |
| `summary`     | text      | 2–4 sentence AI reflection                       |
| `suggestions` | JSON      | list of short suggestion strings                 |
| `entry_count` | int       | how many entries were summarized                 |
| `created_at` / `updated_at` | datetime | `updated_at` bumps on regeneration |

The week is always **Monday–Sunday**. `week_of` may be *any* date within the target week
(the service snaps it to that week's Monday). Entries are matched by `created_at` falling
within the week's datetime range.

## Endpoints

| Method | Path                             | Auth | Description                              |
|--------|----------------------------------|------|------------------------------------------|
| POST   | `/api/v1/summary/weekly`         | JWT  | Generate/regenerate a week's summary      |
| GET    | `/api/v1/summary/weekly`         | JWT  | List summaries (newest week first)        |
| GET    | `/api/v1/summary/weekly/{id}`    | JWT  | Get one summary                           |

## API flow

### 1. Generate (current week)
```http
POST /api/v1/summary/weekly
Authorization: Bearer <access_token>
```
Or target a specific week by passing any date inside it:
```http
POST /api/v1/summary/weekly
Content-Type: application/json

{ "week_of": "2026-07-20" }
```
`201 Created`
```json
{
  "id": 1,
  "week_start": "2026-07-20",
  "week_end": "2026-07-26",
  "summary": "A generally positive week with steady progress.",
  "suggestions": ["Keep journaling daily", "Take a rest day"],
  "entry_count": 2,
  "created_at": "2026-07-22T13:55:10",
  "updated_at": "2026-07-22T13:55:10"
}
```
Regenerating the same week **overwrites** the existing row (same `id`, bumped `updated_at`)
rather than creating a duplicate — run it again after adding entries to refresh the digest.

A week with no entries → `400`:
```json
{ "error": { "type": "BadRequestError", "detail": "No journal entries in this week to summarize" } }
```

### 2. List
```http
GET /api/v1/summary/weekly
Authorization: Bearer <access_token>
```
`200 OK` — an array of summaries, most recent `week_start` first.

### 3. Get one
```http
GET /api/v1/summary/weekly/1
Authorization: Bearer <access_token>
```
Not owned / doesn't exist → `404 NotFoundError` ("Weekly summary not found").

## Error envelope
```json
{ "error": { "type": "<ExceptionName>", "detail": "<message or field errors>" } }
```
- No/invalid token → `401 UnauthorizedError`
- Empty week → `400 BadRequestError`
- Summary not found / not owned → `404 NotFoundError`
- AI provider unavailable or malformed → `502 AIServiceError`

## Verify (fresh DB)
```bash
alembic upgrade head
uvicorn app.main:app --reload
# register + login, create a few journal entries this week, then:
#   POST /api/v1/summary/weekly            -> generates the digest (needs OPENROUTER_API_KEY)
#   GET  /api/v1/summary/weekly            -> lists summaries
#   GET  /api/v1/summary/weekly/{id}       -> one summary
```
