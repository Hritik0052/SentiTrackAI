# SentiTrack AI - Claude Project Guide

This file is the handoff guide for continuing SentiTrack AI and building the React
frontend. The backend is complete through Phase 11. Future work should respect the
existing FastAPI API contract documented below.

## Project Snapshot

SentiTrack AI is an AI-powered personal journaling product. Users can register,
log in, write journal entries, analyze entries for sentiment/emotion, generate
weekly summaries, view analytics, search history, and generate AI insights.

Backend stack:

- FastAPI + Uvicorn
- SQLAlchemy 2.0 + Alembic
- SQLite for local development, PostgreSQL for production
- JWT access tokens + refresh-token rotation
- OpenRouter-backed AI service
- Pydantic v2 schemas

Backend base URL during local development:

```text
http://127.0.0.1:8000
```

Feature APIs live under:

```text
/api/v1
```

All protected endpoints require:

```http
Authorization: Bearer <access_token>
```

All handled backend errors use this envelope:

```json
{
  "error": {
    "type": "ErrorType",
    "detail": "Message or validation details"
  }
}
```

## Frontend Build Direction

Build a modern, polished React frontend after the backend Phase 11 contract.

Recommended stack:

- React + Vite
- React Router
- Axios or Fetch wrapper
- Tailwind CSS or a clean CSS module setup
- Reusable layout components
- Token storage through a small auth service

Required public pages before dashboard/app pages:

1. **Landing page**
   - Modern, catchy first impression.
   - Explain journaling, AI mood tracking, weekly summaries, analytics, and insights.
   - Clear CTAs: `Get Started`, `Login`.
   - Should feel like a real product, not a placeholder.

2. **About Us**
   - Explain the purpose: private reflective journaling with AI-assisted self-awareness.
   - Highlight privacy-conscious design: user-scoped data and protected routes.

3. **Contact**
   - Simple contact form UI with name, email, message.
   - It can be frontend-only unless a backend contact API is added later.

Reusable UI:

- `Navbar` reused on Landing, About, Contact, Login/Register, and dashboard shell.
- `Footer` reused on Landing, About, Contact, and other public pages.
- Authenticated app shell can reuse the same brand but should include dashboard navigation.

Suggested app pages after public pages:

- Register
- Login
- Dashboard
- Journal List
- Journal Detail / Editor
- Analytics
- Weekly Summary
- Search
- Insights
- Profile

Frontend style:

- Clean, modern, emotionally warm.
- Use strong visual hierarchy, cards for individual repeated records, and clear empty states.
- Avoid showing raw AI payloads.
- Show loading/error states for AI operations because `/analyze`, `/summary/weekly`, and `/insights/generate` can take time.

## Phase 1 - Project Initialization

What exists:

- FastAPI app factory.
- CORS middleware.
- Lifespan logging.
- Root metadata endpoint.
- Health endpoint.

### `GET /`

Response `200`:

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

### `GET /health`

Response `200`:

```json
{
  "status": "ok",
  "app": "SentiTrack AI",
  "version": "0.1.0",
  "environment": "development"
}
```

Frontend use:

- Use `/health` for optional backend connectivity checks.

## Phase 2 - Database Layer

What exists:

- SQLAlchemy `Base`.
- `TimestampMixin`.
- Engine/session setup.
- `get_db` dependency.
- Alembic migrations.
- SQLite dev database and PostgreSQL-ready config.

No frontend API surface in this phase.

## Phase 3 - Users

### `POST /api/v1/users/register`

Request:

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "password": "s3cret-pass"
}
```

Response `201`:

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "id": 1,
  "created_at": "2026-07-19T13:05:02",
  "updated_at": "2026-07-19T13:05:02"
}
```

Duplicate email `409`:

```json
{
  "error": {
    "type": "ConflictError",
    "detail": "Email already registered"
  }
}
```

Frontend use:

- Registration page should call register, then redirect to login or automatically log in by calling `/auth/login`.

### `GET /api/v1/users/me`

Auth: required.

Response `200`:

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "id": 1,
  "created_at": "2026-07-19T13:05:02",
  "updated_at": "2026-07-19T13:05:02"
}
```

### `PUT /api/v1/users/me`

Auth: required.

Request, any subset:

```json
{
  "name": "Ada L",
  "email": "ada.l@example.com",
  "password": "new-pass-123"
}
```

Response `200`: updated user object.

### `DELETE /api/v1/users/me`

Auth: required.

Response `204`: no body.

## Phase 4 - Authentication

### `POST /api/v1/auth/login`

Request:

```json
{
  "email": "ada@example.com",
  "password": "s3cret-pass"
}
```

Response `200`:

```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```

Invalid credentials `401`:

```json
{
  "error": {
    "type": "UnauthorizedError",
    "detail": "Invalid email or password"
  }
}
```

Frontend use:

- Store `access_token` and `refresh_token`.
- Attach `Authorization: Bearer <access_token>` to protected calls.

### `POST /api/v1/auth/refresh`

Request:

```json
{
  "refresh_token": "<refresh_token>"
}
```

Response `200`:

```json
{
  "access_token": "<new-jwt>",
  "refresh_token": "<new-refresh-jwt>",
  "token_type": "bearer"
}
```

Notes:

- Refresh tokens rotate. Replace both stored tokens after each successful refresh.
- Reusing an old refresh token returns `401`.

### `POST /api/v1/auth/logout`

Request:

```json
{
  "refresh_token": "<refresh_token>"
}
```

Response `204`: no body.

Frontend use:

- Call logout, clear local tokens, redirect to landing or login.

## Phase 5 - Journal CRUD

All journal endpoints are user-scoped and require auth.

### `POST /api/v1/journals`

Request:

```json
{
  "title": "Morning walk",
  "content": "Felt great and energized today."
}
```

Response `201`:

```json
{
  "title": "Morning walk",
  "content": "Felt great and energized today.",
  "id": 4,
  "created_at": "2026-07-21T09:59:50",
  "updated_at": "2026-07-21T09:59:50"
}
```

Validation:

- `title` is optional, max 200 chars.
- `content` is required, 1-10000 chars.

### `GET /api/v1/journals`

Query params:

- `page`, default `1`
- `page_size`, default `20`, max `100`
- `sort_by`: `created_at`, `updated_at`, `title`
- `order`: `asc`, `desc`
- `q`: keyword search over title/content

Example:

```http
GET /api/v1/journals?page=1&page_size=20&sort_by=created_at&order=desc&q=anxious
```

Response `200`:

```json
{
  "items": [
    {
      "id": 5,
      "title": "Stressful meeting",
      "content": "I felt anxious before the meeting.",
      "created_at": "2026-07-22T09:00:00",
      "updated_at": "2026-07-22T09:00:00"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

### `GET /api/v1/journals/{journal_id}`

Response `200`: one journal object.

Not found/not owned `404`:

```json
{
  "error": {
    "type": "NotFoundError",
    "detail": "Journal entry not found"
  }
}
```

### `PUT /api/v1/journals/{journal_id}`

Request, any subset:

```json
{
  "title": "Morning walk updated",
  "content": "Updated content."
}
```

Response `200`: updated journal object.

### `DELETE /api/v1/journals/{journal_id}`

Response `204`: no body.

## Phase 6 - AI Integration

What exists:

- Backend-only `AIService`.
- OpenRouter `/chat/completions` client.
- Retry, timeout, fallback model.
- Safe JSON parsing for AI responses.

No direct frontend endpoint exists in Phase 6.

Frontend implication:

- AI-facing endpoints in later phases may be slower and can return `502 AIServiceError`.
- Build loading states and retry-friendly UI around analyze, summary generation, and insight generation.

## Phase 7 - Sentiment Analysis

### `POST /api/v1/journals/{journal_id}/analyze`

Auth: required.

Response `200`:

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

Notes:

- Re-running analysis overwrites the prior sentiment row.
- `raw_response` is stored but never returned to frontend.

Possible errors:

```json
{
  "error": {
    "type": "AIServiceError",
    "detail": "AI service is currently unavailable"
  }
}
```

### `GET /api/v1/journals/{journal_id}/sentiment`

Response `200`: same sentiment object.

Not analyzed `404`:

```json
{
  "error": {
    "type": "NotFoundError",
    "detail": "This journal entry has not been analyzed yet"
  }
}
```

Frontend use:

- Add an `Analyze` button on journal detail/editor pages.
- Show sentiment badge, mood, emotion, confidence percentage.
- Disable duplicate clicks while request is pending.

## Phase 8 - Weekly Summary

### `POST /api/v1/summary/weekly`

Auth: required.

Request is optional. Current week:

```json
{}
```

Specific week:

```json
{
  "week_of": "2026-07-20"
}
```

Response `201`:

```json
{
  "id": 1,
  "week_start": "2026-07-20",
  "week_end": "2026-07-26",
  "summary": "A generally positive week with steady progress.",
  "suggestions": [
    "Keep journaling daily",
    "Take a rest day"
  ],
  "entry_count": 2,
  "created_at": "2026-07-22T13:55:10",
  "updated_at": "2026-07-22T13:55:10"
}
```

No entries in week `400`:

```json
{
  "error": {
    "type": "BadRequestError",
    "detail": "No journal entries in this week to summarize"
  }
}
```

### `GET /api/v1/summary/weekly`

Response `200`:

```json
[
  {
    "id": 1,
    "week_start": "2026-07-20",
    "week_end": "2026-07-26",
    "summary": "A generally positive week with steady progress.",
    "suggestions": [
      "Keep journaling daily",
      "Take a rest day"
    ],
    "entry_count": 2,
    "created_at": "2026-07-22T13:55:10",
    "updated_at": "2026-07-22T13:55:10"
  }
]
```

### `GET /api/v1/summary/weekly/{summary_id}`

Response `200`: one weekly summary object.

Not found/not owned `404`:

```json
{
  "error": {
    "type": "NotFoundError",
    "detail": "Weekly summary not found"
  }
}
```

Frontend use:

- Weekly Summary page with generate/regenerate button.
- Display week range, entry count, summary text, and suggestion list.

## Phase 9 - Analytics

### `GET /api/v1/analytics/dashboard`

Response `200`:

```json
{
  "total_entries": 10,
  "analyzed_entries": 9,
  "sentiment_counts": {
    "positive": 4,
    "neutral": 3,
    "negative": 2
  },
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

### `GET /api/v1/analytics/mood-distribution`

Response `200`:

```json
{
  "total_analyzed": 9,
  "sentiment_counts": {
    "positive": 4,
    "neutral": 3,
    "negative": 2
  },
  "emotions": [
    {
      "label": "calm",
      "count": 3
    },
    {
      "label": "joy",
      "count": 2
    }
  ],
  "moods": [
    {
      "label": "okay",
      "count": 3
    },
    {
      "label": "happy",
      "count": 2
    }
  ]
}
```

### `GET /api/v1/analytics/monthly?year=2026`

Response `200`:

```json
{
  "year": 2026,
  "months": [
    {
      "period": "2026-06",
      "entries": 1,
      "analyzed": 1,
      "sentiment_counts": {
        "positive": 1,
        "neutral": 0,
        "negative": 0
      },
      "average_confidence": 0.85,
      "most_common_emotion": "gratitude"
    },
    {
      "period": "2026-07",
      "entries": 8,
      "analyzed": 7,
      "sentiment_counts": {
        "positive": 3,
        "neutral": 3,
        "negative": 2
      },
      "average_confidence": 0.6071,
      "most_common_emotion": "calm"
    }
  ]
}
```

### `GET /api/v1/analytics/yearly`

Response `200`:

```json
{
  "years": [
    {
      "period": "2026",
      "entries": 20,
      "analyzed": 18,
      "sentiment_counts": {
        "positive": 10,
        "neutral": 5,
        "negative": 3
      },
      "average_confidence": 0.71,
      "most_common_emotion": "calm"
    }
  ]
}
```

Frontend use:

- Dashboard cards: total entries, analyzed entries, current streak, longest streak, entries this week/month.
- Charts: sentiment distribution, emotion/mood bars, monthly trend.
- Empty states: show zeros and invite user to create/analyze entries.

## Phase 10 - Search

### `GET /api/v1/search`

Auth: required.

Query params:

- `q`: keyword over title/content
- `date_from`: inclusive date
- `date_to`: inclusive date
- `mood`: exact mood, case-insensitive
- `emotion`: exact emotion, case-insensitive
- `sentiment`: `positive`, `neutral`, `negative`
- `sort_by`: `created_at`, `updated_at`, `title`
- `order`: `asc`, `desc`
- `page`, `page_size`

Example:

```http
GET /api/v1/search?q=day&sentiment=positive&date_from=2026-07-01&sort_by=created_at&order=desc
```

Response `200`:

```json
{
  "items": [
    {
      "id": 1,
      "title": "Gym day",
      "content": "Felt strong and happy at the gym",
      "created_at": "2026-07-22T09:00:00",
      "updated_at": "2026-07-22T09:00:00",
      "sentiment": {
        "id": 1,
        "journal_id": 1,
        "sentiment": "positive",
        "mood": "happy",
        "emotion": "joy",
        "confidence": 0.7,
        "created_at": "2026-07-22T09:00:00",
        "updated_at": "2026-07-22T09:00:00"
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

Unanalyzed entries may return:

```json
{
  "sentiment": null
}
```

Invalid date range `400`:

```json
{
  "error": {
    "type": "BadRequestError",
    "detail": "date_from must be on or before date_to"
  }
}
```

Frontend use:

- Search page with text input, date range, sentiment dropdown, mood/emotion fields, sort controls, pagination.

## Phase 11 - AI Insights

### `POST /api/v1/insights/generate`

Auth: required.

Response `201`:

```json
[
  {
    "id": 12,
    "content": "You journal most consistently on weekends.",
    "created_at": "2026-07-22T14:25:01"
  },
  {
    "id": 13,
    "content": "Your mood trends more positive after exercise.",
    "created_at": "2026-07-22T14:25:01"
  },
  {
    "id": 14,
    "content": "Your journaling streak has been strong this month.",
    "created_at": "2026-07-22T14:25:01"
  }
]
```

No entries `400`:

```json
{
  "error": {
    "type": "BadRequestError",
    "detail": "No journal entries to generate insights from"
  }
}
```

### `GET /api/v1/insights`

Query params:

- `page`, default `1`
- `page_size`, default `20`, max `100`

Response `200`:

```json
{
  "items": [
    {
      "id": 14,
      "content": "Your journaling streak has been strong this month.",
      "created_at": "2026-07-22T14:25:01"
    }
  ],
  "total": 6,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

Frontend use:

- Insights page with a `Generate Insights` button.
- Show insight cards ordered newest first.
- Add loading states because generation calls the AI provider.

## Frontend Implementation Plan

### Frontend Phase 0 - Setup

- Create React app using Vite.
- Add routing.
- Add shared API client.
- Add auth token service.
- Add global layout styles.

### Frontend Phase 1 - Public Marketing Pages

Build these first:

- Landing page
- About Us page
- Contact page

Shared components:

- `Navbar`
- `Footer`
- `Button`
- `Section`
- `FeatureCard`

Navbar links:

- Home
- About
- Contact
- Login
- Get Started

Footer sections:

- Brand summary
- Product links
- Resource links
- Copyright

### Frontend Phase 2 - Auth

- Register page.
- Login page.
- Logout action.
- Protected route wrapper.
- Refresh-token handling.

### Frontend Phase 3 - Journal Experience

- Journal list with pagination/search.
- Create/edit journal form.
- Journal detail page.
- Analyze sentiment action and sentiment panel.

### Frontend Phase 4 - Dashboard And Analytics

- Dashboard using `/analytics/dashboard`.
- Mood distribution visualizations.
- Monthly/yearly analytics views.

### Frontend Phase 5 - AI Features

- Weekly summaries page.
- Search page.
- Insights page.

## Important Notes For Claude

- Do not implement frontend against imagined endpoints. Use only the endpoints above unless backend changes are made first.
- AI endpoints may be slow; always include loading and error states.
- Never display `raw_response`; backend intentionally omits it.
- Keep user data scoped to the logged-in user.
- README currently marks Phases 12-20 as planned, not complete.
- `DEBUG` must be boolean-like: `true`, `false`, `1`, or `0`.
- Secrets belong in `.env`; never commit real keys.
