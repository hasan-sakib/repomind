# API Design

> **Note:** this document describes the Phase 1 target API for the
> eventual AI ingestion/chat product (repositories tied directly to
> embeddings and chat sessions). The GitHub-integration routes actually
> implemented in Phase 3 (`/organizations/{id}/github/*`,
> `/organizations/{id}/repositories`, `/repositories/{id}/*`,
> `/webhooks/github`) are metadata-sync-oriented, not AI-oriented, and
> differ from what's sketched below — see
> `docs/architecture/0003-github-integration.md` for the real, shipped
> API surface. Auth routes (`/auth/*`, `/organizations/*` member
> management, `/users/*`) below match Phase 2's real implementation — see
> `docs/architecture/0002-auth-and-multi-tenancy.md`. Phase 4 shipped the
> real indexing-trigger/status API — `POST` and `GET
> /repositories/{id}/indexing-jobs`, `GET
> /repositories/{id}/indexing-jobs/{jobId}` — see
> `docs/architecture/0004-codebase-indexing.md`; the ingestion-job
> endpoints sketched below (and the chat/retrieval endpoints, which read
> `CodeChunk` rows for citations) remain unbuilt design.

**Status:** Design (Phase 1) — targets implementation in Phase 2
**Scope:** Full REST surface under `/api/v1`, error shape, pagination, rate
limiting
**Companion docs:** `docs/architecture/backend-architecture.md` (service
layering, auth model, GitHub integration internals — read that first for how
these endpoints are implemented, not just what they do)

This replaces the placeholder in `docs/api/README.md` for the Phase 1 slice
(repo ingestion + chat). All routes are versioned under `settings.api_v1_prefix`
(`/api/v1`, already configured in `app/core/config.py`). `GET /api/v1/health`
already exists (Phase 0) and is unchanged.

Unless noted otherwise, every route requires a valid `rm_session` cookie
(`get_current_user` dependency) and every route with a `{workspace_id}` path
parameter additionally requires workspace membership
(`get_workspace_member` dependency). See `backend-architecture.md` §2 for what
those dependencies check. The two exceptions are the GitHub OAuth
entry/callback routes (unauthenticated by design — they establish the
session) and the webhook endpoint (authenticated by HMAC signature instead of
a cookie).

## 1. Auth

| Method | Path                    | Auth                     | Description                                                                                                                       |
| ------ | ----------------------- | ------------------------ | --------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/auth/github/login`    | none                     | 302 to GitHub App's authorize URL                                                                                                 |
| GET    | `/auth/github/callback` | none                     | Exchanges `code`, upserts `User`, provisions personal workspace on first login, sets `rm_session` + `rm_refresh`, 302 to frontend |
| POST   | `/auth/refresh`         | `rm_refresh` cookie only | Rotates refresh token, reissues both cookies                                                                                      |
| POST   | `/auth/logout`          | `rm_session`             | Clears both cookies, revokes current refresh token row                                                                            |
| GET    | `/auth/me`              | `rm_session`             | Current user profile + list of workspace memberships (id, name, slug, role)                                                       |

`GET /auth/me` is the route the frontend calls on app load to determine
whether a session is live and which workspaces/roles the user has — it never
needs to decode the JWT client-side. `POST /auth/refresh` reads only
`rm_refresh` (scoped to this path, per `backend-architecture.md` §2.2) — it
does not require a (possibly already-expired) `rm_session` to be present,
since its entire purpose is to reissue one.

Full sequence diagrams for login and rotation are in
`backend-architecture.md` §2.1 and §2.3.

## 2. GitHub App

| Method | Path                                              | Auth             | Description                                                                                            |
| ------ | ------------------------------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------ |
| GET    | `/github/install`                                 | `rm_session`     | 302 to `github.com/apps/<slug>/installations/new`                                                      |
| GET    | `/github/callback`                                | `rm_session`     | Receives `installation_id` + `setup_action`, records `GitHubInstallation`, 302 to frontend repo picker |
| GET    | `/workspaces/{workspace_id}/github/installations` | workspace member | List installations recorded for this workspace                                                         |
| GET    | `/workspaces/{workspace_id}/github/repos`         | workspace member | List installation-accessible repos not yet connected (i.e. no `Repository` row yet)                    |

`GET /workspaces/{workspace_id}/github/repos` calls
`app/integrations/github/repo_client.py` under the hood
(`backend-architecture.md` §3.4) using a freshly-minted or Redis-cached
installation token; it is the read side that feeds the "connect a repository"
action in §3.

## 3. Workspaces

| Method | Path               | Auth             | Description                                     |
| ------ | ------------------ | ---------------- | ----------------------------------------------- |
| GET    | `/workspaces`      | `rm_session`     | List workspaces the current user is a member of |
| GET    | `/workspaces/{id}` | workspace member | Workspace detail                                |

Workspace creation is not a standalone endpoint in Phase 1 — the only
workspace-creation path is the automatic personal workspace provisioned on
first login (`backend-architecture.md` §2.1). Multi-workspace / team
invitations are out of scope for this phase.

## 4. Repositories

| Method | Path                                      | Auth                                       | Description                                                                                                                                                            |
| ------ | ----------------------------------------- | ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| GET    | `/workspaces/{workspace_id}/repositories` | workspace member                           | List connected repositories, cursor-paginated                                                                                                                          |
| POST   | `/workspaces/{workspace_id}/repositories` | workspace member (admin/owner)             | Connect a repository by `github_repo_id`; creates the row and triggers the initial `IngestionJob`                                                                      |
| GET    | `/repositories/{id}`                      | workspace member (of the repo's workspace) | Repository detail                                                                                                                                                      |
| DELETE | `/repositories/{id}`                      | workspace member (admin/owner)             | Disconnect (removes `Repository` and cascades `CodeChunk`/`IngestionJob` rows; does not uninstall the GitHub App)                                                      |
| GET    | `/repositories/{id}/ingestion-status`     | workspace member                           | Current ingestion state: `status`, `last_indexed_commit_sha`, `last_indexed_at`, and (if a job is in flight) the active `IngestionJob`'s `status`/`started_at`/`stats` |

`POST /workspaces/{workspace_id}/repositories` request body:
`{ "github_repo_id": 123456 }`. The service looks up the repo's metadata via
`repo_client.py` (full name, default branch, private flag) rather than
trusting client-supplied values for anything beyond the id — this prevents a
client from connecting a repo the installation doesn't actually grant access
to. Returns `409 Conflict` (`code: REPOSITORY_ALREADY_CONNECTED`) if a
`Repository` row already exists for that `(workspace_id, github_repo_id)`
pair.

**Why polling, not push, for ingestion status:** ingestion is a background
job that takes on the order of minutes (cloning, chunking, embedding — see
the AI/retrieval architecture doc), not seconds. A client polling
`GET /repositories/{id}/ingestion-status` every few seconds gets acceptable
latency on a status transition with no persistent connection, no
reconnect/backoff logic, and no server-side fan-out concerns. This is a
deliberately different tradeoff from chat (§5): chat is a single request
that needs to render token-by-token as the model produces them, where
polling would mean either blocking the whole response or reconstructing a
prefix on every poll — SSE is the right tool there because the client is
waiting on one in-flight generation, not on a multi-minute background job it
can walk away from.

## 5. Chat

| Method | Path                               | Auth                                     | Description                                                 |
| ------ | ---------------------------------- | ---------------------------------------- | ----------------------------------------------------------- |
| POST   | `/repositories/{id}/chat/sessions` | workspace member                         | Create a `ChatSession`                                      |
| GET    | `/repositories/{id}/chat/sessions` | workspace member                         | List sessions for this repo, cursor-paginated, newest first |
| GET    | `/chat/sessions/{id}/messages`     | workspace member (of the session's repo) | List messages in a session, cursor-paginated, oldest first  |
| POST   | `/chat/sessions/{id}/messages`     | workspace member                         | Post a user message; response is `text/event-stream`        |

### 5.1 Streaming response shape

`POST /chat/sessions/{id}/messages` takes `{ "content": "..." }`, persists it
as a `ChatMessage` (`role="user"`), then opens an SSE stream
(`Content-Type: text/event-stream`) with these event types:

```
event: delta
data: {"text": "The ingestion pipeline "}

event: delta
data: {"text": "chunks each file by "}

... (one event per token/text-delta from AIProvider.stream)

event: done
data: {"message_id": "9f2b...", "citations": [{"file_path": "app/services/ingestion_service.py", "start_line": 12, "end_line": 40}], "content": "<full assembled text>"}
```

The `done` event carries the persisted assistant `ChatMessage`'s id, the full
assembled content (so the client doesn't need to concatenate deltas itself
if it dropped one), and the `citations` array — sourced from which
`CodeChunk` rows fed the retrieval context for this turn, per
`backend-architecture.md` §4, not parsed out of the model's own text. If the
underlying `AIProvider.stream` call fails mid-stream, the handler emits a
final `event: error` with a machine-readable code
(`data: {"code": "PROVIDER_ERROR", "message": "..."}`) instead of silently
closing the connection, and still persists whatever partial content was
generated so the session's history stays consistent with what the user saw.

`chat_service.py` owns this contract end to end: persisting the user
message, invoking retrieval, calling `AIProvider.stream`, persisting the
assistant message, and yielding the event sequence back to the route. The
route itself only wraps the service's async generator in a
`StreamingResponse`.

## 6. Webhooks

| Method | Path               | Auth                                              | Description           |
| ------ | ------------------ | ------------------------------------------------- | --------------------- |
| POST   | `/webhooks/github` | HMAC signature (`X-Hub-Signature-256`), no cookie | GitHub event delivery |

This is the one route in the entire API surface that does not go through
`get_current_user`. It is registered outside the cookie-authenticated route
tree and documented here as a deliberate, explicit exception — not an
oversight. Signature verification and event handling are detailed in
`backend-architecture.md` §3.3. The endpoint always returns `200` once the
signature is verified and the payload is parsed, regardless of whether it
resulted in an enqueued job, a debounce, or a non-default-branch no-op —
GitHub retries deliveries on non-2xx responses, and none of those three
outcomes is an error.

## 7. Health

| Method | Path      | Auth | Description                            |
| ------ | --------- | ---- | -------------------------------------- |
| GET    | `/health` | none | Liveness check, unchanged from Phase 0 |

## 8. Error shape

Every 4xx/5xx response body:

```json
{
  "error": {
    "code": "REPOSITORY_ALREADY_CONNECTED",
    "message": "This repository is already connected to the workspace.",
    "details": {}
  }
}
```

`details` is an object, empty (`{}`) when there's nothing structured to add.
For Pydantic validation failures (`422`), `details` carries the per-field
errors, keyed by field path:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed.",
    "details": {
      "github_repo_id": ["field required"]
    }
  }
}
```

This is produced by a single FastAPI exception handler registered in
`app/main.py` for `RequestValidationError`, plus a second handler for a small
`AppError` exception hierarchy (defined once, raised from services, caught at
the app level — not `try/except`ed in every route) that carries `code`,
`http_status`, `message`, and optional `details`. Routes never construct the
error envelope themselves.

### 8.1 Status codes actually used

| Status | When                                                                                                                                                                                                              |
| ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 400    | Malformed request that isn't a schema validation failure (e.g. a query param combination that doesn't make sense together)                                                                                        |
| 401    | Missing/invalid/expired `rm_session` (or `rm_refresh` on the refresh route); invalid webhook signature                                                                                                            |
| 403    | Authenticated, but not a member of the target workspace, or membership role too low for the action                                                                                                                |
| 404    | Resource doesn't exist, or exists but the caller has no visibility into it (workspace-scoped resources 404 rather than 403 when the workspace itself isn't visible, to avoid confirming existence to non-members) |
| 409    | State conflict — e.g. `REPOSITORY_ALREADY_CONNECTED`, or a refresh token replay that's already been revoked                                                                                                       |
| 422    | Pydantic request validation failure                                                                                                                                                                               |
| 429    | Rate limit exceeded (see §10)                                                                                                                                                                                     |
| 500    | Unhandled server error — logged with a correlation id, generic message returned, no internals leaked                                                                                                              |

### 8.2 `code` values

| Code                           | Status                                     | Meaning                                                                                                                 |
| ------------------------------ | ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| `VALIDATION_ERROR`             | 422                                        | Request body/query failed schema validation                                                                             |
| `NOT_AUTHENTICATED`            | 401                                        | No valid session                                                                                                        |
| `SESSION_EXPIRED`              | 401                                        | JWT present but expired (frontend uses this to trigger a refresh-and-retry instead of a hard logout)                    |
| `INVALID_REFRESH_TOKEN`        | 401                                        | `rm_refresh` not found, expired, or already revoked                                                                     |
| `REFRESH_TOKEN_REUSED`         | 401                                        | Revoked token replayed — family revoked, client must re-authenticate                                                    |
| `FORBIDDEN`                    | 403                                        | Authenticated but lacks permission (role or membership)                                                                 |
| `NOT_FOUND`                    | 404                                        | Generic resource-not-found                                                                                              |
| `REPOSITORY_ALREADY_CONNECTED` | 409                                        | Repo already has a `Repository` row in this workspace                                                                   |
| `INGESTION_IN_PROGRESS`        | 409                                        | Action (e.g. disconnect) blocked while an `IngestionJob` is running, if the service chooses to block rather than cancel |
| `INVALID_WEBHOOK_SIGNATURE`    | 401                                        | HMAC verification failed on `/webhooks/github`                                                                          |
| `RATE_LIMITED`                 | 429                                        | Per-user or per-endpoint limit exceeded                                                                                 |
| `PROVIDER_ERROR`               | — (SSE `event: error`, not an HTTP status) | `AIProvider` call failed mid-stream                                                                                     |
| `INTERNAL_ERROR`               | 500                                        | Unhandled exception                                                                                                     |

This table is the authoritative list of `code` values for Phase 2; new codes
get added here when new endpoints are implemented rather than invented ad hoc
in route handlers.

## 9. Pagination

List endpoints (`repositories`, `chat/sessions`, `chat/sessions/{id}/messages`)
use cursor-based pagination, not offset/limit. Request:
`GET /repositories/{id}/chat/sessions/{sid}/messages?cursor=<opaque>&limit=50`
(`limit` capped server-side, default 50, max 200). Response:

```json
{
  "items": [ ... ],
  "next_cursor": "eyJpZCI6ICI5ZjJi...",
  "has_more": true
}
```

The cursor encodes the last-seen row's `(created_at, id)` tuple
(base64-encoded, opaque to the client — the client must not construct or
parse it). Cursor pagination is chosen over offset/limit specifically because
`ChatMessage` history is append-only within a session: an offset-based page
2 can skip or duplicate rows if a new message lands between two of a client's
requests, which is exactly the access pattern of an open chat view polling
or paging through history while a conversation continues. `Repository` and
`ChatSession` listings are lower-churn but use the same scheme for
consistency rather than maintaining two pagination styles.

## 10. Rate limiting

Two endpoints justify rate limiting in Phase 2:
`POST /chat/sessions/{id}/messages` (each call is a paid AI provider call)
and `POST /webhooks/github` (exposed to the public internet, GitHub-signed
but still worth bounding). The intended approach is a per-user token bucket
enforced at the API layer (a dependency checked before the route body runs,
backed by Redis — the same Redis already used for installation token
caching, `backend-architecture.md` §3.1), returning `429` with
`code: RATE_LIMITED` and a `Retry-After` header when exhausted. Limits
themselves (bucket size, refill rate) are a product/cost decision deferred to
Phase 2 implementation, not fixed here; this section documents the mechanism,
not the numbers.
