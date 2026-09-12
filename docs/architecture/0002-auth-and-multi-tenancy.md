# ADR 0002: Authentication & Multi-Tenant Foundation

**Status:** Accepted — implemented
**Date:** 2026-09-08
**Supersedes (in part):** the auth/role/routing sketches in
`docs/architecture/0001-foundation.md`,
`docs/architecture/backend-architecture.md`,
`docs/architecture/frontend-architecture.md`, and
`docs/database/database-design.md`. Those docs describe the eventual
repository/ingestion/chat data model (Phase 3+); this ADR is the source of
truth for what actually shipped for auth and multi-tenancy in this phase.

## What was built

- Email/password auth: registration, login, logout, JWT access tokens,
  rotated refresh tokens, password reset, email verification — all real,
  no stubbed auth checks.
- GitHub OAuth login (a plain GitHub **OAuth App**, not a GitHub App —
  see "GitHub OAuth, not GitHub App" below).
- Multi-tenancy: `User`, `Organization`, `OrganizationMember` with a
  `Role` enum (`owner`, `admin`, `developer`, `viewer`), enforced in
  `app/services/organization_service.py` and the
  `require_organization_role` FastAPI dependency.
- `AuditLog` recording every security-relevant action (register, login,
  logout, password reset request/completion, email verification,
  organization/member create/role-change/remove).
- Full frontend: `/login`, `/register`, `/forgot-password`,
  `/reset-password`, `/verify-email`, `/dashboard`, `/settings`,
  `/settings/members` — all wired to the real API, no demo data.

## Decisions and why

### Password hashing: Argon2id, not bcrypt

`argon2-cffi` (`app/core/security/password.py`). Argon2id is OWASP's
current recommendation over bcrypt for new systems — memory-hard, tunable,
no 72-byte input truncation footgun. `MIN_PASSWORD_LENGTH = 8` is enforced
at the Pydantic schema layer (`app/schemas/auth.py`), not in the hashing
module itself.

### Session model: `sessions` + `refresh_tokens` as genuinely distinct concerns

A `Session` row is created once per login (email/password, GitHub OAuth,
or registration) and represents "one logged-in device/browser instance."
A `RefreshToken` row is a rotated, single-use credential _for_ a session.
This split is what makes real session management possible — revoking a
`Session` (logout) immediately invalidates every access token and refresh
token derived from it, without needing to hunt down and revoke each
`RefreshToken` row individually.

- **Access token**: a 15-minute JWT (`app/core/security/tokens.py`)
  carrying `sub` (user id) and `sid` (session id). Verified on every
  request against the `sessions` table (`app/api/deps.py`,
  `get_current_user_and_session`) — not purely stateless — so revoking a
  session takes effect immediately, not just at token expiry.
- **Refresh token**: a 30-day opaque random token (`secrets.token_urlsafe`),
  stored only as a SHA-256 hash (`refresh_tokens.token_hash`), rotated on
  every use. **Reuse of an already-rotated token revokes the entire
  parent session** — this is a real, tested behavior
  (`test_refresh_rotates_token_and_reuse_is_detected`), not a documented
  aspiration: it's the standard signal that a refresh token was stolen and
  is being replayed by an attacker after the legitimate client already
  rotated past it.
- Cookies: `rm_session` (path `/`) and `rm_refresh` (path scoped to
  `/api/v1/auth/refresh` only), both httpOnly, `SameSite=Lax`, `Secure` in
  production. CSRF is mitigated by requiring a custom
  `X-Requested-With: RepoMind` header on every mutating request
  (`require_csrf_header`) — a cross-site request can't add that header
  without a CORS preflight our origin policy rejects.

### Password reset / email verification: real tokens, no real email transport

Both flows generate a high-entropy opaque token, store only its hash (plus
an expiry) directly on the `users` row — not in separate tables. This
keeps the schema to exactly the six tables asked for
(`users, organizations, organization_members, sessions, refresh_tokens,
audit_logs`) while still being real, single-use, expiring tokens; a second
request overwrites the first (only one active token of each kind at a
time — a deliberate simplification, not a bug).

No transactional email provider is wired up yet — `app/integrations/email/`
defines an `EmailSender` ABC (mirroring `AIProvider`'s pattern) with one
implementation, `ConsoleEmailSender`, which logs the email instead of
sending it. This is not fake auth: the token generation, hashing, expiry,
and validation are fully real and tested
(`tests/integration/test_auth.py::test_password_reset_flow`,
`test_email_verification_flow`); only the transport is a stub, swappable
by implementing `EmailSender` and changing `app/integrations/email/factory.py`.
`Settings.require_email_verification` defaults to `False` for exactly this
reason — flipping it on today would lock every user out, since there's no
real inbox to receive the link.

### GitHub OAuth, not GitHub App

`docs/architecture/backend-architecture.md` (Phase 1) planned a single
GitHub **App** covering login, repository installation, and webhooks. This
phase implements only the login piece, and does it with a plain **GitHub
OAuth App** (`app/integrations/github/oauth.py`) instead — repository
access/installation tokens are a distinct, not-yet-built concern for a
later phase, and an OAuth App is the simpler mechanism when installation
tokens aren't needed yet. `Settings.github_client_id/secret` (already
present from Phase 0) are reused as-is. Revisit the GitHub App migration
when repository ingestion is actually built — nothing here blocks it: the
`User.github_user_id` column and find-or-create-by-that-id logic
(`auth_service.login_with_github`) work the same regardless of which
GitHub credential type authorized the request.

A new user created via GitHub has no `password_hash` (nullable on `User`)
and is linked strictly by `github_user_id` — never by matching email
address, to avoid the account-takeover risk of silently merging into an
existing password-based account just because GitHub reports the same
email.

### Role model: four roles, not three

Phase 1's database-design.md sketched `owner|admin|member`. This phase
implements the four roles actually requested: `OWNER > ADMIN > DEVELOPER

> VIEWER` (`app/domain/role.py`, `role_at_least`for ordering checks).`docs/database/database-design.md`'s `organization_role` enum values are
> now stale — treat this ADR as authoritative for the role set until that
> doc is revised.

Authorization rules (`app/services/organization_service.py`), each with a
passing integration test:

- Any member (`VIEWER`+) can view the organization and its member list.
- `ADMIN`+ can add/remove members and change roles — **except** an `ADMIN`
  cannot grant or modify the `OWNER` role; only an existing `OWNER` can.
- A member can always remove _themselves_ regardless of role (leaving an
  organization needs no special permission) — except the organization's
  last remaining `OWNER` can neither leave nor be demoted/removed
  (`LastOwnerError`), which would otherwise orphan the organization.

### Frontend routing: flat routes, not `/[workspaceSlug]/...`

Phase 1's shell used `/[workspaceSlug]/...` URLs. This phase's explicit
route list (`/dashboard`, `/settings`, `/settings/members`) has no slug
segment, so "which organization am I looking at" moved from the URL into
client state: `CurrentOrgProvider` (`lib/current-org.tsx`) holds the
active organization id, persisted to `localStorage`, defaulting to the
user's first membership. The sidebar org switcher changes this client
state directly rather than navigating to a different URL. This is a
genuine simplification worth revisiting if/when a feature needs the
organization to be linkable/bookmarkable via URL (e.g. a direct link to
one organization's dashboard) — not something this phase needed.

`middleware.ts` was renamed to `proxy.ts` — Next.js 16 deprecated the
`middleware` file convention (same mechanics, `export function proxy`
instead of `export function middleware`). It performs a UX-only redirect
based on cookie _presence_; the API independently and authoritatively
enforces real auth on every request regardless of what the proxy decides.

### Server/client data flow

`(dashboard)/layout.tsx` is a Server Component that calls
`serverApiFetch("/api/v1/auth/me")`, forwarding the incoming request's
cookies manually (a Server Component's own `fetch` never automatically
carries the browser's cookies to a different-origin API — see
`lib/server-api.ts`). On a 401 it redirects to `/login` server-side,
before any client JS runs. The fetched `{user, organizations}` seeds a
React Query cache (`useMeQuery(initialData)`) that the rest of the
dashboard reads and mutates reactively (e.g. creating an organization
invalidates and refetches this same query, updating the switcher without
a full page reload).

## Testing

39 backend tests (`backend/tests/`): unit tests for password hashing, JWT
tokens, and role ordering; integration tests (real Postgres, real HTTP
requests via `httpx.AsyncClient` against the actual FastAPI app) covering
registration, login, logout, refresh rotation and theft-detection,
password reset, email verification, organization creation, and the full
authorization matrix (role requirements, last-owner protection,
self-removal, non-member 404s). Test isolation uses a `NullPool` engine
against a separate `repomind_test` database with `TRUNCATE ... CASCADE`
between tests — the initially-attempted SAVEPOINT-per-test rollback
pattern raced with asyncpg's single-operation-per-connection constraint
under FastAPI's dependency resolution and was abandoned in favor of this
simpler approach.

Frontend has no automated tests yet (no test runner configured in Phase
0/1) — verified manually via Playwright-driven browser sessions against
the real backend (registration → dashboard → settings → members → logout
→ redirect-when-logged-out; wrong-password error; full password-reset
round trip; add-member validation error), not just `next build`/`tsc`.
Adding a frontend test runner (Vitest + Testing Library, or Playwright as
a committed test suite rather than an ad hoc verification script) is
worth doing in a future phase.
