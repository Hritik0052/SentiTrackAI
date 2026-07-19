# Phase 3 — User Module

User registration and self-management, backed by the `users` table.

## What shipped
- `User` model — [`app/models/user.py`](../../app/models/user.py)
- Schemas (`UserCreate`, `UserRead`, `UserUpdate`) — [`app/schemas/user.py`](../../app/schemas/user.py)
- Password hashing + JWT helpers — [`app/core/security.py`](../../app/core/security.py)
- Custom exceptions + central error envelope — [`app/core/exceptions.py`](../../app/core/exceptions.py)
- User service (CRUD, unique-email guard) — [`app/services/user_service.py`](../../app/services/user_service.py)
- `get_current_user` dependency — [`app/dependencies/auth.py`](../../app/dependencies/auth.py)
- Users router — [`app/api/routes/users.py`](../../app/api/routes/users.py)
- First Alembic migration: `create users table`

## Endpoints

| Method | Path                     | Auth | Description            |
|--------|--------------------------|------|------------------------|
| POST   | `/api/v1/users/register` | —    | Create a new account   |
| GET    | `/api/v1/users/me`       | JWT  | Current user profile   |
| PUT    | `/api/v1/users/me`       | JWT  | Update current user    |
| DELETE | `/api/v1/users/me`       | JWT  | Delete current user    |

> Login (token issuance) arrives in **Phase 4**. Until then, `/me` accepts any valid
> access token (e.g. one minted via `app.core.security.create_access_token`).

## API flow

### 1. Register
```http
POST /api/v1/users/register
Content-Type: application/json

{ "name": "Ada Lovelace", "email": "ada@example.com", "password": "s3cret-pass" }
```
`201 Created`
```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com",
  "id": 1,
  "created_at": "2026-07-19T13:05:02",
  "updated_at": "2026-07-19T13:05:02"
}
```
Duplicate email → `409`:
```json
{ "error": { "type": "ConflictError", "detail": "Email already registered" } }
```

### 2. Get current user
```http
GET /api/v1/users/me
Authorization: Bearer <access_token>
```
Missing/invalid token → `401`.

### 3. Update current user
```http
PUT /api/v1/users/me
Authorization: Bearer <access_token>
Content-Type: application/json

{ "name": "Ada L" }
```

### 4. Delete current user
```http
DELETE /api/v1/users/me
Authorization: Bearer <access_token>
```
`204 No Content`.

## Error envelope
All handled errors share one shape:
```json
{ "error": { "type": "<ExceptionName>", "detail": "<message or field errors>" } }
```

## Verify (fresh DB)
```bash
alembic upgrade head
uvicorn app.main:app --reload
# then register + call /me with a bearer token
```
