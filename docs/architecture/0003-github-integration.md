# ADR 0003: GitHub Integration

**Status:** Accepted — implemented
**Date:** 2026-09-08
**Supersedes (in part):** the GitHub App sketch in
`docs/architecture/backend-architecture.md`, the AI-ingestion-oriented
`Repository`/`CodeChunk` schema in `docs/database/database-design.md`, and
the API surface in `docs/api/api-design.md`. Those docs describe the
eventual AI code-indexing pipeline (Phase 4+); this ADR is the source of
truth for the GitHub metadata integration actually built in this phase —
repository connection, sync, and webhooks, with no AI/embedding involved
yet.

## What was built

- A GitHub **App** (distinct from the OAuth App added in Phase 2 for
  login — see ADR 0002) providing installation-based repository access
  and webhooks: `app/integrations/github/app_client.py` (App JWT minting,
  installation token exchange, installation account lookup) and
  `app/integrations/github/rest_client.py` (the specific REST calls
  needed: list installation repos, get repo, list branches/commits/
  pulls/issues).
- Repository connection flow: install the App → list installation-
  accessible repos not yet connected → connect one → initial sync runs
  in the background.
- A bounded metadata sync pipeline (`app/services/sync_service.py`):
  repository metadata, branches, recent commits, pull requests, and
  issues, all upserted idempotently.
- Secure, idempotent webhook processing (`app/services/webhook_service.py`,
  `app/api/v1/routes/webhooks.py`) for `push`, `pull_request`, `issues`,
  `installation`, and `installation_repositories`.
- Eight new tables: `github_installations`, `repositories`, `branches`,
  `commits`, `pull_requests`, `issues`, `repository_memberships`,
  `webhook_events`.
- Frontend: connect flow, repository list (now `/dashboard`'s primary
  content), a compact repository overview page, and repository settings
  (disconnect).

## Decisions and why

### GitHub App, separate from the Phase 2 OAuth App

Phase 2 added a plain GitHub OAuth App for login only
(`app/integrations/github/oauth.py`). This phase adds a GitHub **App**
(`GITHUB_APP_ID` + `GITHUB_APP_PRIVATE_KEY` + `GITHUB_APP_SLUG`, separate
from `GITHUB_CLIENT_ID`/`GITHUB_CLIENT_SECRET`) purely for repository
access and webhooks — it never touches user login. This matches the split
ADR 0002 anticipated: login and repository access are different trust
boundaries (a user can sign in without ever granting repo access, and repo
access is scoped to an _installation_, not a user session), so keeping
them as two separate GitHub integrations avoids conflating "who is this
person" with "what can RepoMind read on GitHub's behalf."

Installation access tokens are minted **on demand, every time**
(`app_client.get_installation_access_token`) — no caching. The original
Phase 1 sketch planned a Redis-backed cache (~55 min TTL) to cut down on
mint calls. Redis isn't part of the stack yet (arq/Redis for background
jobs was deferred too — see below), and adding it just for token caching
isn't justified by this phase's call volume: each sync or webhook handler
mints at most one token and makes a handful of REST calls with it. Revisit
if GitHub's rate limits (5,000 req/hr per installation) become a real
constraint.

### Bounded sync, not full history

Every sync call fetches a recent window, not full history:
`MAX_COMMITS = MAX_PULL_REQUESTS = MAX_ISSUES = 50` (per_page on GitHub's
paginated list endpoints — see `app/integrations/github/rest_client.py`).
A repository overview is a dashboard, not an archive; nothing in the UI
needs (or paginates through) a full commit history. Re-syncs are
incremental in effect even though each call re-fetches the same bounded
window: commits are upserted by `sha` (skip if already present), branches
and PRs/issues are upserted by their natural key
(`(repository_id, name)` / `(repository_id, number)`), so re-running sync
never duplicates rows and only writes what actually changed.

### Sync execution: FastAPI `BackgroundTasks`, not arq/Redis

ADR 0001 planned `arq` + Redis for background jobs (AI ingestion). This
phase's sync work — clone-free REST calls, a few seconds per repository —
doesn't need a durable job queue, and standing up Redis + a worker process
for it would be infrastructure ahead of an actual need. `BackgroundTasks`
(`app/services/sync_service.py::run_sync_in_background`, scheduled from
`app/api/v1/routes/repositories.py` and `app/api/v1/routes/webhooks.py`)
runs the sync after the HTTP response is sent, in the same process.

**Real limitation, not swept under the rug:** a `BackgroundTasks` job is
lost if the API process restarts mid-sync — there's no persistence or
retry. `Repository.status` would be stuck at `syncing` until a manual
"Sync now" click recovers it. This is acceptable at this phase's scale
(a sync takes seconds; a mid-sync restart is rare and self-healing via a
retry click) but is the concrete reason to move to `arq`+Redis once AI
ingestion (which _does_ need a durable, potentially long-running job
queue) is built — at that point sync should move onto the same queue
rather than staying a special case.

`run_sync_in_background` opens its **own** database session
(`app.db.session.async_session_factory`) rather than reusing the
request's — a request-scoped session is closed once the response is
sent, before a background task actually runs. This was caught by a real
test failure, not designed defensively upfront — see Testing below.

### Idempotent webhooks: signature first, delivery-id dedup second

`app/integrations/github/webhooks.py::verify_signature` checks the
`X-Hub-Signature-256` HMAC against the raw request body **before**
anything else touches the payload — `app/api/v1/routes/webhooks.py`
computes this before even checking which event type it is. An
unverified or missing signature is rejected with 401
(`WebhookVerificationError`), never parsed.

Idempotency is GitHub's own `X-GitHub-Delivery` header, stored as a
unique constraint on `webhook_events.github_delivery_id`
(`app/domain/webhook_event.py`). Processing order:

1. Look up the delivery id — if a `webhook_events` row already exists,
   return immediately (already processed or in flight); no re-dispatch.
2. Insert a `webhook_events` row (`status="received"`) and commit
   immediately. If this insert hits the unique constraint (a genuinely
   concurrent duplicate delivery), catch the `IntegrityError` and treat
   it as a duplicate too — the row-existence check above has an
   unavoidable check-then-insert race window, and the DB constraint is
   what actually closes it.
3. Dispatch to the event-specific handler, then mark the row
   `processed`. A handler exception is caught, logged, and recorded as
   `status="failed"` on the row (queryable for debugging) — the webhook
   endpoint still returns 204, since GitHub's retry behavior on
   non-2xx responses isn't something a single failed handler run should
   trigger blindly.

### Event handlers: what payload data is trusted, and what isn't

Every handler resolves _our_ `Repository` row via
`(installation.organization_id, payload["repository"]["id"])` — never by
trusting a `full_name` or org slug in the payload — because the
`GitHubInstallation` → `organization_id` link is the only thing our own
database, not the webhook payload, is the source of truth for.

- **`push`**: only a push to the repository's recorded `default_branch`
  triggers a resync. A push to a feature branch is ignored — otherwise
  every branch push on an active repo would trigger a full resync,
  which is wasted work for a dashboard that only shows default-branch
  activity.
- **`pull_request`** / **`issues`**: upsert the single PR/issue from the
  payload directly (no need to re-fetch from the REST API — the webhook
  payload already has the full object).
- **`installation` (`action: "deleted"`)**: the only installation action
  handled. `"created"` is deliberately a no-op here — that case is
  handled by our own install-callback flow (`app/api/v1/routes/github.py`),
  which has the organization context (via the CSRF-style state cookie)
  that a bare webhook payload doesn't carry. `"deleted"` means the user
  uninstalled the App from GitHub's side; we find and delete the matching
  `GitHubInstallation`, cascading to every `Repository` under it.
- **`installation_repositories` (`action: "removed"`)**: deletes the
  specific `Repository` rows GitHub revoked access to. `"added"` is a
  no-op — a newly-accessible repo just becomes selectable next time the
  user opens the repository connect page; connecting stays a deliberate
  action, not something a webhook does on the user's behalf.

### `RepositoryMembership`: auto-maintained, not manually managed

Every organization member gets a `RepositoryMembership` row for every
repository in their organization, kept in sync at two points: connecting
a repository grants access to all current members
(`repository_service.connect_repository`), and adding a new organization
member grants them access to all existing repositories
(`organization_service.add_member`, extended in this phase). There is no
UI in this phase to restrict a specific repository to a subset of
members — the table exists as real, enforced infrastructure
(`require_repository_access` in `app/api/deps.py` checks it on every
repository-scoped route) for that future capability, not a stub. Today it
behaves exactly like "any org member can see any org repository," which
is the correct default until per-repository visibility is an actual
product requirement.

### Frontend: `/dashboard` becomes the repository list

Phase 2's `/dashboard` was a placeholder ("repository connection lands in
the next phase"). This phase makes it the real connected-repositories
list — the natural home view now that repositories exist — rather than
introducing a separate `/repositories` route for the list. **Breadcrumb
note:** the `repositories` URL _segment_ (e.g. in
`/repositories/{id}`) has no page of its own — it's not a route, just a
grouping prefix — so the breadcrumb trail's "Repositories" crumb is
special-cased to link to `/dashboard` rather than forming the
literal (non-existent) `/repositories` URL. This was a real bug caught
during manual verification (see Testing), not a hypothetical one.

Repository overview (`/repositories/[repositoryId]`) follows the
project's "no giant dashboard cards" rule explicitly: repo metadata is a
single dense strip (language dot, stars, forks, default branch, last
sync — all inline, not separate stat cards), and commits/PRs/issues are
three compact bordered list panels, not padded shadcn `Card`s. See
`docs/architecture/design-system.md` for the broader convention this
follows.

## Testing

22 new backend tests (bringing the suite to 61): unit tests for webhook
signature verification, GitHub App JWT minting/verification (against a
throwaway per-test-run RSA keypair — never a real key), and GitHub API
response parsing (including the "issues endpoint also returns PRs" edge
case). Integration tests mock GitHub's REST API via `pytest-httpx`
(already a dependency from Phase 2) rather than hitting real GitHub —
covering the full connect → sync happy path, authorization (non-admin
can't connect, non-member gets 404), webhook signature rejection,
duplicate-delivery idempotency, push-to-default-vs-feature-branch
resync behavior, and installation-deleted cascade.

Two real bugs were caught by these tests and by manual browser
verification, not found through code review alone:

1. **Cross-event-loop database engine reuse.** pytest-asyncio's default
   per-test event loop broke `app/db/session.py`'s module-level engine
   (used by `run_sync_in_background`, which can't reuse the request's
   session) with `asyncpg.exceptions` about connections attached to the
   wrong loop. Fixed by making the whole test session share one event
   loop (`asyncio_default_fixture_loop_scope = "session"` /
   `asyncio_default_test_loop_scope = "session"` in `pyproject.toml`),
   matching production's single-loop-per-process model rather than
   pytest-asyncio's default.
2. **`GitHubInstallation.repositories` cascade delete.** Deleting an
   installation raised a `NotNullViolationError` on
   `repositories.installation_id` — SQLAlchemy's default ORM-level
   cascade tried to `UPDATE` each child's foreign key to `NULL` before
   the parent delete, which is impossible on a `NOT NULL` column. Fixed
   with `passive_deletes=True` on the relationship, so the database's own
   `ON DELETE CASCADE` handles it directly instead.

Frontend has no automated tests (same gap noted in ADR 0002) — verified
via Playwright against the running app: empty states (no installation, no
repositories), and, since this environment has no real GitHub App
credentials to exercise a live OAuth/installation round trip, a
directly-seeded repository (branches/commits/PRs/issues inserted straight
into the dev database) to verify the overview page's rendering,
responsive behavior (desktop/tablet/mobile), and dark mode.
