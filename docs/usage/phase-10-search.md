# Phase 10 — Search

One owner-scoped `GET /search` endpoint that filters journal entries by keyword, date
range, and sentiment attributes (mood / emotion / sentiment value), combining any subset
of filters. Results are paginated, sortable, and carry the entry's nested sentiment when
it has been analyzed.

## What shipped
- Search schemas (`SearchResultItem` with nested `SentimentRead`, `SearchResponse`) —
  [`app/schemas/search.py`](../../app/schemas/search.py)
- Search service (filter composition, sentiment join, pagination/sort, eager-loaded
  sentiment) — [`app/services/search_service.py`](../../app/services/search_service.py)
- Search router — [`app/api/routes/search.py`](../../app/api/routes/search.py)

Requires a valid access token and only ever searches the caller's own entries.

## Filters
All filters are optional and **AND-combined**; omit them all to page through everything.

| Param       | Type   | Behavior                                                        |
|-------------|--------|-----------------------------------------------------------------|
| `q`         | string | Case-insensitive substring over **title OR content**            |
| `date_from` | date   | `created_at` on/after this date (inclusive)                     |
| `date_to`   | date   | `created_at` on/before this date (inclusive)                    |
| `mood`      | string | Exact mood match, case-insensitive                              |
| `emotion`   | string | Exact emotion match, case-insensitive                          |
| `sentiment` | enum   | `positive` \| `neutral` \| `negative`                          |
| `sort_by`   | enum   | `created_at` (default) \| `updated_at` \| `title`              |
| `order`     | enum   | `asc` \| `desc` (default)                                      |
| `page`      | int    | 1-based (default 1)                                            |
| `page_size` | int    | default 20, max 100                                           |

Any of `mood` / `emotion` / `sentiment` joins the `sentiments` table, so those filters
**implicitly exclude entries that haven't been analyzed**. Keyword/date-only searches
keep all matching entries and return `sentiment: null` for un-analyzed ones.

## Example

```http
GET /api/v1/search?q=day&sentiment=positive&date_from=2026-07-01&sort_by=created_at&order=desc
Authorization: Bearer <access_token>
```
`200 OK`
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
        "id": 1, "journal_id": 1,
        "sentiment": "positive", "mood": "happy", "emotion": "joy", "confidence": 0.7,
        "created_at": "2026-07-22T09:00:00", "updated_at": "2026-07-22T09:00:00"
      }
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```
`raw_response` is never included in the nested sentiment. Entries without analysis
serialize as `"sentiment": null`.

## Error envelope
```json
{ "error": { "type": "<ExceptionName>", "detail": "<message or field errors>" } }
```
- No/invalid token → `401 UnauthorizedError`
- `date_from` later than `date_to` → `400 BadRequestError`
- Invalid `sentiment` / `sort_by` / `order` / bad date format → `422 ValidationError`

## Verify
```bash
alembic upgrade head
uvicorn app.main:app --reload
# register + login, create/analyze entries, then try:
#   GET /api/v1/search?q=happy
#   GET /api/v1/search?mood=calm&date_from=2026-06-01&date_to=2026-06-30
#   GET /api/v1/search?sentiment=negative&sort_by=created_at&order=asc
```
