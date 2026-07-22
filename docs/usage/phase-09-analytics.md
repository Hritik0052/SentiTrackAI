# Phase 9 — Analytics

Read-only aggregations over the caller's journal entries and their stored sentiments
(Phase 7). No new tables — every endpoint joins `journal_entries` to `sentiments` and
rolls the result up in Python, so the math is identical on SQLite and PostgreSQL.

## What shipped
- Analytics schemas (`DashboardAnalytics`, `MoodDistribution`, `PeriodStat`, …) —
  [`app/schemas/analytics.py`](../../app/schemas/analytics.py)
- Analytics service (aggregation, streaks, month/year bucketing) —
  [`app/services/analytics_service.py`](../../app/services/analytics_service.py)
- Analytics router — [`app/api/routes/analytics.py`](../../app/api/routes/analytics.py)

All endpoints require a valid access token and only ever see the caller's own data.
An account with no entries returns well-formed zeros/nulls (never an error).

## Endpoints

| Method | Path                                   | Auth | Description                                  |
|--------|----------------------------------------|------|----------------------------------------------|
| GET    | `/api/v1/analytics/dashboard`          | JWT  | Overview totals, averages, streaks           |
| GET    | `/api/v1/analytics/mood-distribution`  | JWT  | Sentiment / emotion / mood breakdown         |
| GET    | `/api/v1/analytics/monthly?year=YYYY`  | JWT  | Per-month stats for a year (default: current) |
| GET    | `/api/v1/analytics/yearly`             | JWT  | Per-year stats across all history            |

## Definitions
- **analyzed** — an entry that has a stored sentiment (Phase 7). Stats like
  `average_confidence` and `most_common_emotion` are computed over analyzed entries only;
  totals and streaks use *all* entries.
- **streak** — consecutive calendar days with at least one entry.
  `longest_streak` is the longest such run ever; `current_streak` is the run ending at the
  most recent entry, counted only if that entry was **today or yesterday** (otherwise `0`).
- Weeks are **Monday–Sunday**; `entries_this_month` uses the current calendar month.

## API flow

### 1. Dashboard
```http
GET /api/v1/analytics/dashboard
Authorization: Bearer <access_token>
```
`200 OK`
```json
{
  "total_entries": 10,
  "analyzed_entries": 9,
  "sentiment_counts": { "positive": 4, "neutral": 3, "negative": 2 },
  "average_confidence": 0.6444,
  "most_common_emotion": "calm",
  "most_common_mood": "okay",
  "current_streak": 3,
  "longest_streak": 4,
  "entries_this_week": 4,
  "entries_this_month": 8,
  "first_entry_at": "2025-12-31T09:00:00",
  "last_entry_at": "2026-07-22T20:00:00"
}
```

### 2. Mood distribution
```http
GET /api/v1/analytics/mood-distribution
Authorization: Bearer <access_token>
```
`200 OK` — `emotions` and `moods` are sorted by count, descending:
```json
{
  "total_analyzed": 9,
  "sentiment_counts": { "positive": 4, "neutral": 3, "negative": 2 },
  "emotions": [ { "label": "calm", "count": 3 }, { "label": "joy", "count": 2 } ],
  "moods": [ { "label": "okay", "count": 3 }, { "label": "happy", "count": 2 } ]
}
```

### 3. Monthly (per-year)
```http
GET /api/v1/analytics/monthly?year=2026
Authorization: Bearer <access_token>
```
`200 OK` — only months that have entries are returned, ascending:
```json
{
  "year": 2026,
  "months": [
    { "period": "2026-06", "entries": 1, "analyzed": 1,
      "sentiment_counts": { "positive": 1, "neutral": 0, "negative": 0 },
      "average_confidence": 0.85, "most_common_emotion": "gratitude" },
    { "period": "2026-07", "entries": 8, "analyzed": 7, "sentiment_counts": { "positive": 3, "neutral": 3, "negative": 2 },
      "average_confidence": 0.6071, "most_common_emotion": "calm" }
  ]
}
```
`year` defaults to the current year when omitted.

### 4. Yearly
```http
GET /api/v1/analytics/yearly
Authorization: Bearer <access_token>
```
`200 OK` — one `PeriodStat` per year (`period` = `YYYY`), ascending.

## Error envelope
```json
{ "error": { "type": "<ExceptionName>", "detail": "<message or field errors>" } }
```
- No/invalid token → `401 UnauthorizedError`
- `year` outside 1970–9999 → `422 ValidationError`

## Verify
```bash
alembic upgrade head
uvicorn app.main:app --reload
# register + login, create/analyze a few entries, then GET the four analytics endpoints.
# (Streaks and trends only get interesting once entries span multiple days/months.)
```
