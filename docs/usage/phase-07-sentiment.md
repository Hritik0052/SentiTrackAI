# Phase 7 — Sentiment Analysis

Turns a saved journal entry into structured emotion data. `POST /journals/{id}/analyze`
sends the entry's content to the AI provider (Phase 6 `AIService`) and persists the
result in a `sentiments` row; `GET /journals/{id}/sentiment` reads it back. Analysis is
1:1 with an entry — this is the raw material Phase 9 analytics and Phase 8 summaries build on.

## What shipped
- `Sentiment` model + `JournalEntry.sentiment` (1:1) relationship —
  [`app/models/sentiment.py`](../../app/models/sentiment.py)
- `SentimentRead` schema (omits `raw_response`) —
  [`app/schemas/sentiment.py`](../../app/schemas/sentiment.py)
- Sentiment service (owner-scoped analyze + get, upsert on re-analyze) —
  [`app/services/sentiment_service.py`](../../app/services/sentiment_service.py)
- Two endpoints on the journals router —
  [`app/api/routes/journals.py`](../../app/api/routes/journals.py)
- Migration: `create sentiments table`

Both endpoints require a valid access token and operate only on the caller's own
entries. Requesting analysis on another user's entry returns the same `404` as a
nonexistent one — ownership is never leaked.

## Data model
`sentiments` has a **unique** FK to `journal_entries` (`ondelete=CASCADE`), so each entry
has at most one sentiment and deleting an entry removes its analysis.

| Column        | Type          | Notes                                       |
|---------------|---------------|---------------------------------------------|
| `id`          | int PK        |                                             |
| `journal_id`  | int, unique   | FK → `journal_entries.id`, cascade delete   |
| `sentiment`   | str(20)       | `positive` \| `neutral` \| `negative`       |
| `mood`        | str(50)       | short mood descriptor, e.g. `content`       |
| `emotion`     | str(50)       | primary emotion, e.g. `gratitude`           |
| `confidence`  | float         | 0.0–1.0                                     |
| `raw_response`| text          | full LLM output; stored, never returned     |
| `created_at` / `updated_at` | datetime | `updated_at` bumps on re-analysis |

## Endpoints

| Method | Path                                  | Auth | Description                              |
|--------|---------------------------------------|------|------------------------------------------|
| POST   | `/api/v1/journals/{id}/analyze`       | JWT  | Analyze the entry and store its sentiment |
| GET    | `/api/v1/journals/{id}/sentiment`     | JWT  | Read the stored sentiment                 |

## API flow

### 1. Analyze
```http
POST /api/v1/journals/5/analyze
Authorization: Bearer <access_token>
```
`200 OK`
```json
{
  "id": 1,
  "journal_id": 5,
  "sentiment": "positive",
  "mood": "content",
  "emotion": "gratitude",
  "confidence": 0.87,
  "created_at": "2026-07-22T07:02:32",
  "updated_at": "2026-07-22T07:02:32"
}
```
Re-running `analyze` on the same entry **overwrites** the previous result (upsert) and
bumps `updated_at` — no duplicate rows. Use it after editing an entry to refresh its analysis.

### 2. Get sentiment
```http
GET /api/v1/journals/5/sentiment
Authorization: Bearer <access_token>
```
Not analyzed yet → `404`:
```json
{ "error": { "type": "NotFoundError", "detail": "This journal entry has not been analyzed yet" } }
```
Not owned / doesn't exist → `404 NotFoundError` ("Journal entry not found").

## Error envelope
All handled errors share one shape:
```json
{ "error": { "type": "<ExceptionName>", "detail": "<message or field errors>" } }
```
- No/invalid token → `401 UnauthorizedError`
- Entry not found or not owned → `404 NotFoundError`
- AI provider unavailable or malformed response → `502 AIServiceError`
  (both primary and fallback models failed, or the LLM returned an unparseable/invalid shape)

## Verify (fresh DB)
```bash
alembic upgrade head
uvicorn app.main:app --reload
# register + login, create a journal, then:
#   POST /api/v1/journals/{id}/analyze      -> stores sentiment
#   GET  /api/v1/journals/{id}/sentiment    -> reads it back
# (a valid OPENROUTER_API_KEY is required for a real analyze call)
```
