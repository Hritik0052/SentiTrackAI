# Phase 5 — Journal Module

Owner-scoped journal entry CRUD with pagination, sorting, and keyword search — the
raw material every later phase (sentiment, summaries, analytics, search, insights)
analyzes.

## What shipped
- `JournalEntry` model + `User.journals` relationship — [`app/models/journal_entry.py`](../../app/models/journal_entry.py)
- Schemas (`JournalCreate`, `JournalUpdate`, `JournalRead`, `JournalListResponse`) —
  [`app/schemas/journal.py`](../../app/schemas/journal.py)
- Journal service (owner-scoped CRUD, pagination, sort, search) —
  [`app/services/journal_service.py`](../../app/services/journal_service.py)
- Journals router — [`app/api/routes/journals.py`](../../app/api/routes/journals.py)
- Migration: `create journal_entries table`

Every endpoint requires a valid access token (`get_current_user`) and only ever
operates on the caller's own entries — requesting another user's entry returns the
same `404` as a nonexistent one, never a `403` (no ownership is leaked).

## Endpoints

| Method | Path                        | Auth | Description                              |
|--------|-----------------------------|------|-------------------------------------------|
| POST   | `/api/v1/journals`          | JWT  | Create a journal entry                    |
| GET    | `/api/v1/journals`          | JWT  | List entries (paginated/sortable/searchable) |
| GET    | `/api/v1/journals/{id}`     | JWT  | Get one entry                             |
| PUT    | `/api/v1/journals/{id}`     | JWT  | Update an entry                           |
| DELETE | `/api/v1/journals/{id}`     | JWT  | Delete an entry                           |

## API flow

### 1. Create
```http
POST /api/v1/journals
Authorization: Bearer <access_token>
Content-Type: application/json

{ "title": "Morning walk", "content": "Felt great and energized today." }
```
`201 Created`
```json
{
  "title": "Morning walk",
  "content": "Felt great and energized today.",
  "id": 4,
  "created_at": "2026-07-21T09:59:50",
  "updated_at": "2026-07-21T09:59:50"
}
```
`title` is optional — omit it for an untitled entry. `content` is required (1–10,000 chars).

### 2. List (pagination, sorting, search)
```http
GET /api/v1/journals?page=1&page_size=20&sort_by=created_at&order=desc&q=anxious
Authorization: Bearer <access_token>
```
`200 OK`
```json
{
  "items": [ { "id": 5, "title": "Stressful meeting", "content": "...", "created_at": "...", "updated_at": "..." } ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```
- `page` (default 1), `page_size` (default 20, max 100)
- `sort_by`: `created_at` (default) | `updated_at` | `title`
- `order`: `asc` | `desc` (default)
- `q`: optional keyword, matched against `title` OR `content` (case-insensitive substring)

### 3. Get one
```http
GET /api/v1/journals/5
Authorization: Bearer <access_token>
```
Not owned / doesn't exist → `404`:
```json
{ "error": { "type": "NotFoundError", "detail": "Journal entry not found" } }
```

### 4. Update
```http
PUT /api/v1/journals/4
Authorization: Bearer <access_token>
Content-Type: application/json

{ "title": "Morning walk (updated)" }
```
Only supplied fields are changed (partial update).

### 5. Delete
```http
DELETE /api/v1/journals/4
Authorization: Bearer <access_token>
```
`204 No Content`.

## Error envelope
All handled errors share one shape:
```json
{ "error": { "type": "<ExceptionName>", "detail": "<message or field errors>" } }
```
No/invalid token → `401 UnauthorizedError`. Empty/oversized `content` or oversized `title` →
`422 ValidationError` with per-field details.

## Verify (fresh DB)
```bash
alembic upgrade head
uvicorn app.main:app --reload
# register + login, then create/list/get/update/delete under /api/v1/journals
# with the access token from /auth/login
```
