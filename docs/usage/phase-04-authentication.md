# Phase 4 — Authentication

JWT login, refresh-token rotation, and logout, backed by a server-side `refresh_tokens` table
so tokens can be revoked instead of trusted blindly until expiry.

## What shipped
- `RefreshToken` model — [`app/models/refresh_token.py`](../../app/models/refresh_token.py)
- `hash_token` helper + unique `jti` claim on every JWT — [`app/core/security.py`](../../app/core/security.py)
- Auth schemas (`LoginRequest`, `RefreshRequest`, `LogoutRequest`, `TokenResponse`) —
  [`app/schemas/auth.py`](../../app/schemas/auth.py)
- Auth service (login, refresh rotation, logout) — [`app/services/auth_service.py`](../../app/services/auth_service.py)
- Auth router — [`app/api/routes/auth.py`](../../app/api/routes/auth.py)
- Migration: `create refresh_tokens table`

`get_current_user` ([`app/dependencies/auth.py`](../../app/dependencies/auth.py)) already protected
routes since Phase 3 — Phase 4 adds the endpoints that actually mint and revoke tokens.

## Endpoints

| Method | Path                     | Auth | Description                          |
|--------|--------------------------|------|---------------------------------------|
| POST   | `/api/v1/auth/login`     | —    | Verify credentials, issue token pair  |
| POST   | `/api/v1/auth/refresh`   | —    | Rotate a refresh token for a new pair |
| POST   | `/api/v1/auth/logout`    | —    | Revoke a refresh token                |

## Design notes

- **Access tokens** are short-lived (`access_token_expire_minutes`, default 30) JWTs, not
  persisted — `get_current_user` just verifies the signature and `type: access`.
- **Refresh tokens** are longer-lived (`refresh_token_expire_days`, default 7) JWTs whose
  **SHA-256 hash** is stored in `refresh_tokens`. The raw token is never persisted.
- **Rotation**: every successful `/auth/refresh` call revokes the presented refresh token and
  issues a brand-new access/refresh pair. A refresh token can only be used once — replaying an
  old one after it's been rotated (or explicitly logged out) returns `401`.
- Every JWT carries a random `jti` claim so two tokens minted for the same user in the same
  second still hash to distinct, unique values (`token_hash` is a unique column).
- `/auth/logout` is idempotent: revoking an already-revoked or unknown token still returns `204`.

## API flow

### 1. Login
```http
POST /api/v1/auth/login
Content-Type: application/json

{ "email": "ada@example.com", "password": "s3cret-pass" }
```
`200 OK`
```json
{
  "access_token": "<jwt>",
  "refresh_token": "<jwt>",
  "token_type": "bearer"
}
```
Wrong email/password → `401`:
```json
{ "error": { "type": "UnauthorizedError", "detail": "Invalid email or password" } }
```

### 2. Call a protected route
```http
GET /api/v1/users/me
Authorization: Bearer <access_token>
```

### 3. Refresh (rotate)
```http
POST /api/v1/auth/refresh
Content-Type: application/json

{ "refresh_token": "<refresh_token>" }
```
`200 OK` — new `access_token` + `refresh_token`. The old refresh token is now revoked; reusing
it returns `401`.

### 4. Logout
```http
POST /api/v1/auth/logout
Content-Type: application/json

{ "refresh_token": "<refresh_token>" }
```
`204 No Content`. The refresh token can no longer be used to obtain new tokens. Access tokens
already issued remain valid until they naturally expire (they are stateless).

## Error envelope
All handled errors share one shape:
```json
{ "error": { "type": "<ExceptionName>", "detail": "<message>" } }
```

## Verify (fresh DB)
```bash
alembic upgrade head
uvicorn app.main:app --reload
# register a user, then:
# POST /auth/login -> {access_token, refresh_token}
# GET /users/me with the access_token
# POST /auth/refresh with the refresh_token -> new pair; old refresh_token now 401s
# POST /auth/logout with a refresh_token -> 204; that token now 401s on /auth/refresh
```
