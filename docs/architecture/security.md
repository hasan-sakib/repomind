# Security

**Status:** Living document — reflects a full application security audit
(Phase 13) plus the fixes it produced. Update this file whenever a security-
relevant decision is made, not just when another audit happens.

This documents what was audited, what was found, what was fixed, and what
was reviewed and found sound. Every finding below cites the exact file(s)
involved so a future change can be checked against the same reasoning.

## Scope

The full application: FastAPI backend (`backend/app`), Next.js frontend
(`frontend`), and the infrastructure they depend on (Postgres, Redis,
GitHub OAuth/App integration). Checked against: authentication,
authorization, JWT handling, refresh tokens, CSRF, CORS, SQL injection,
XSS, SSRF, GitHub OAuth, GitHub webhook signatures, API rate limiting,
input validation, file processing, repository access, organization
isolation, secrets, environment variables, logging, and error responses.

## High-severity findings — fixed

### 1. A short or empty `JWT_SECRET` was accepted silently

`app/core/config.py` defaulted `jwt_secret` to the literal
`"dev-secret-change-me"` if the environment variable was unset — and, more
concretely, this repository's own `backend/.env` had `JWT_SECRET=` (present
but empty) before this audit, meaning session JWTs were being signed with
an **empty string** as the HMAC key. HS256 with a known or empty key is
trivially reproducible by anyone; this amounts to being able to forge a
valid session for any user ID.

**Fix:** `Settings` now has a `model_validator` (`_require_strong_jwt_secret`)
that raises at startup — in every environment, not just production — if
`jwt_secret` is under 32 characters. `backend/.env` was regenerated with a
real `openssl rand -hex 32` value. `backend/.env.example` documents the
requirement. Tests (`tests/conftest.py`) already set a 44-character test
secret, so this didn't require any test changes; `tests/unit/test_config.py`
directly tests the validator (short/empty rejected, 32+ accepted).

### 2. An empty `GITHUB_WEBHOOK_SECRET` degraded to "no verification"

`verify_signature` (`app/integrations/github/webhooks.py`) HMAC'd the
payload with `settings.github_webhook_secret` regardless of whether it was
configured. An empty secret is public knowledge (it's not a secret at
all), so anyone could compute a "valid" signature for an arbitrary forged
webhook payload — full webhook spoofing, not just a slightly weaker check.

**Fix:** `verify_signature` now returns `False` immediately if
`github_webhook_secret` is empty, before ever computing an HMAC — fails
closed instead of "verifying" against a key everyone already knows.
`backend/.env`'s webhook secret was also set to a real random value.
`tests/unit/test_webhook_signature.py::test_empty_configured_secret_rejects_everything`
covers this.

### 3. A malicious connected repository could read arbitrary files off the indexing worker

`app/indexing/discovery.py`'s `discover_files` walked a cloned repository
with `repo_root.rglob("*")` and `candidate.is_file()` — both of which
transparently follow symlinks. A repository containing a symlink (e.g.
`evil -> /etc/passwd`, or pointing anywhere else the worker process's
filesystem permits) would have the **target's** content read
(`app/indexing/pipeline.py`'s `file.absolute_path.read_bytes()`) and stored
in the database as if it were the repository's own source, retrievable
afterward through chat/architecture/onboarding for anyone with access to
that repository. Connecting a repository only requires an admin role in
*some* organization (`require_organization_role(Role.ADMIN)` on the connect
route) — and any authenticated user can create their own organization and
become its owner — so this was reachable by any registered user connecting
a repository they fully control.

**Fix:** `discover_files` now skips any `candidate.is_symlink()` entry
before the `is_file()` check. (Verified empirically that `Path.rglob` on
Python 3.12 doesn't descend into symlinked *directories* either, so this
one check closes both the symlinked-file and symlinked-directory cases —
see `tests/unit/test_indexing_discovery.py`'s two new symlink tests.)

### 4. No rate limiting anywhere

Confirmed via a full-codebase search: no rate-limiting middleware,
per-route limiter, or manual 429 existed on any route — including
`/auth/login`, `/auth/register`, `/auth/refresh`, and the password-reset/
email-verification endpoints. Credential stuffing, registration abuse, and
password-reset-email bombing were all unmitigated.

**Fix:** `app/core/rate_limit.py` — a Redis-backed (reusing the same
`redis.asyncio` client pattern already used by `app/events/bus.py`), fixed-
window, per-IP limiter, applied as a FastAPI dependency to:

| Route | Limit (configurable via `Settings`) |
|---|---|
| `POST /auth/register` | `rate_limit_register_per_minute` (default 5/min) |
| `POST /auth/login` | `rate_limit_login_per_minute` (default 10/min) |
| `POST /auth/refresh` | `rate_limit_refresh_per_minute` (default 30/min) |
| `POST /auth/password-reset/request` | `rate_limit_password_reset_per_minute` (default 5/min) |
| `POST /auth/password-reset/confirm` | `rate_limit_password_reset_per_minute` |
| `POST /auth/email/verify/request` | `rate_limit_email_verify_per_minute` (default 5/min) |

Keyed on `request.client.host` (see the module's docstring for the caveat:
this app isn't deployed behind a trusted proxy today — if one is added,
this must switch to reading the proxy's forwarded-for header, or every
request will share one bucket). Fails **open** on a Redis error (a brief
Redis outage shouldn't take down login entirely) and fails **closed** once
the limit is hit (`RateLimitExceededError`, HTTP 429,
`{"error": {"code": "rate_limit_exceeded"}}`).

Rate-limit counters live in Redis, not Postgres, so they aren't reset by
the existing per-test `TRUNCATE`. `tests/conftest.py` adds an autouse
`_reset_rate_limits` fixture (mirroring the DB truncation) so tests stay
independent. `tests/unit/test_rate_limit.py` unit-tests the counter logic
directly; `test_login_is_rate_limited_per_ip`
(`tests/integration/test_auth.py`) exercises the real 429 over HTTP.

## Medium-severity findings — fixed

### 5. `POST /auth/refresh` and `POST .../conversations` were missing CSRF protection

Every other state-changing, cookie-authenticated route in the app uses
`require_csrf_header` (`app/api/deps.py`) — a double-submit-style check
requiring `X-Requested-With: RepoMind`, which a cross-site request can't
attach without triggering a CORS preflight this API's origin policy
rejects. Two mutating routes were inconsistent with this: `POST
/auth/refresh` (rotates the refresh token, creates new `Session`/
`RefreshToken` rows) and `POST /repositories/{id}/conversations`
(`create_conversation`, creates a `Conversation` row). `SameSite=Lax`
cookies already substantially mitigate this for POST specifically (modern
browsers don't attach `Lax` cookies to cross-site non-navigation requests),
so the practical exposure was small — but there's no reason for two routes
to depend on that alone when every sibling route in the same file doesn't.

**Fix:** Added `Depends(require_csrf_header)` to both. Verified the
frontend didn't need any change first: `frontend/lib/api-client.ts`'s
`apiFetch` already attaches `X-Requested-With: RepoMind` to every
POST/PUT/PATCH/DELETE unconditionally, and `frontend/lib/sse.ts`'s
streaming POST sets it explicitly too — so both routes were already being
called with the header, and no frontend call to `/auth/refresh` exists yet
at all (nothing to break). New tests:
`test_refresh_without_csrf_header_is_rejected`,
`test_create_conversation_requires_csrf_header`.

### 6. Password-reset and email-verification tokens were logged in cleartext

`ConsoleEmailSender` (`app/integrations/email/console_sender.py`) — the
**only** `EmailSender` implementation that exists, wired unconditionally in
`app/integrations/email/factory.py` — logs the full email body via
`logger.info(...)`, including the raw, unhashed password-reset/email-
verification link (`app/services/auth_service.py`). That's an intentional,
useful stand-in for local development (there's no real transactional email
provider integrated yet), but nothing prevented it from being the sender
used in production too, in which case every password-reset token in the
system would land in production stdout logs.

**Fix:** `get_email_sender()` now raises `RuntimeError` if
`settings.environment == "production"` rather than falling back to
`ConsoleEmailSender` — failing loudly at first use instead of silently
leaking tokens into whatever log aggregation a production deployment has.
Non-production behavior (the whole point of this sender) is unchanged.

### 7. Argument-injection hardening for the shallow-clone subprocess

`app/integrations/git/fetcher.py` invokes `git` via
`asyncio.create_subprocess_exec` (never `shell=True`, so shell
metacharacter injection was never applicable), but `commit_sha` and
`full_name` were passed through unvalidated. `commit_sha` in particular
flows from a GitHub webhook's `after` field
(`app/services/webhook_service.py`) straight into `git fetch origin
<commit_sha>` as a bare argv token — a value starting with `-` could be
interpreted as a `git` flag rather than a positional argument. Practical
exploitability is very low (GitHub's own webhook payloads, already HMAC-
verified, always carry real 40-hex-char SHAs), but this is cheap to close
outright.

**Fix:** `clone_repository` now validates `full_name` against
`^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$` and `commit_sha` against
`^[0-9a-f]{7,40}$` before either reaches a subprocess argv, raising
`GitFetchError` immediately (before any network call) otherwise. See
`tests/unit/test_git_fetcher.py`.

### 8. `ConnectRepositoryRequest.full_name` had no length bound

`app/schemas/github.py` accepted an arbitrary-length string for a field
that's written into `Repository.full_name`, a `String(300)` column.

**Fix:** `Field(min_length=1, max_length=300)`, matching the column.

## Reviewed and found sound (no change made)

- **Multi-tenant isolation (org A / org B).** Every organization-scoped
  route uses `require_organization_role` (`app/api/deps.py`), which loads
  the caller's own `OrganizationMember` row filtered by *both* the URL's
  `organization_id` and the authenticated user's own ID — never "is
  authenticated" alone. Every repository-scoped route uses
  `require_repository_access`, backed by the per-user `RepositoryMembership`
  table (not just "is a member of the parent org"). Nested resources
  (conversations, messages, indexing jobs, PR analyses) are always fetched
  either through a query already filtered by the caller's own
  `repository_id`, or fetched by ID and then explicitly compared against
  the caller's already-verified parent resource before use — never
  returned by a bare, unscoped ID lookup. Both branches consistently raise
  the same "not found" error whether a resource doesn't exist or belongs to
  someone else, so there's no enumeration signal either way. API keys are
  scoped identically: `require_repository_access`'s bearer-token branch
  checks `repository.organization_id != api_key.organization_id` before
  granting anything.
- **SQL injection.** No raw SQL string construction anywhere in the
  codebase (`sqlalchemy.text(`, `.format()` near SQL, f-string SQL, and raw
  DBAPI cursor use were all searched for and found nowhere). Every query is
  a SQLAlchemy `select()`/`delete()` construct with bound parameters, the
  one or two `.ilike(f"%{q}%")` sites included — the f-string there builds
  a bound *parameter value*, not SQL text.
- **XSS via AI-generated/markdown content.** The only `react-markdown`
  usage (`frontend/components/chat/markdown.tsx`) has no `rehype-raw` in
  its plugin list, so literal HTML in markdown is rendered as text, not
  parsed. `dangerouslySetInnerHTML` is not used anywhere in the frontend.
- **SSRF.** Every outbound HTTP call in the backend targets a hardcoded
  host (`github.com`/`api.github.com` for the three GitHub integration
  modules; operator-configured Anthropic/Voyage/Ollama endpoints
  elsewhere) — no code path builds a request's host from user-supplied
  input, so there's no "fetch an arbitrary URL" primitive to restrict.
- **GitHub OAuth.** `state` is `secrets.token_urlsafe(24)`, stored in an
  `httponly`, path-scoped, 600-second cookie, and compared with
  `secrets.compare_digest` — a standard, correctly-implemented
  double-submit CSRF-for-OAuth pattern. The GitHub App install callback
  (`app/api/v1/routes/github.py`) uses the same pattern for its own `state`
  and additionally requires `Role.ADMIN` on the route that *sets* the
  cookie (`start_install`) — the callback itself trusts the
  cookie-embedded `organization_id` without a separate auth dependency,
  which is fine given the cookie is httponly and its `state` component is
  compared with `secrets.compare_digest`, but is worth a reviewer's eye if
  this flow is ever changed.
- **GitHub webhook signatures.** `verify_signature` runs against the raw
  request body, before `json.loads`, before any database access — confirmed
  by reading the route handler's exact statement order. Comparison is
  `hmac.compare_digest`, not `==`. Redelivery is deduplicated by
  `X-GitHub-Delivery`, enforced by a DB unique constraint (not just an
  application-level check), race-safe via `IntegrityError` handling.
- **CORS.** `allow_origins` is the configured origin list (not `"*"`)
  combined with `allow_credentials=True` — a valid, non-permissive
  combination, not the classic `allow_origins=["*"]` +
  `allow_credentials=True` misconfiguration.
- **Refresh token theft detection.** Rotates on every use; presenting an
  already-rotated token revokes the entire session, not just that token.
  (The one inherent gap — a stolen-but-not-yet-rotated token succeeding
  once before the legitimate client's next refresh — is the accepted
  tradeoff of this rotation-with-reuse-detection pattern, not a bug in this
  implementation.)
- **Password/token hashing.** Passwords: Argon2 (`argon2-cffi`). Refresh
  tokens, password-reset tokens, email-verification tokens: 256-bit
  (`secrets.token_urlsafe(32)`) opaque values, only their SHA-256 stored
  server-side — appropriate, since these "passwords" are themselves
  high-entropy random tokens, not human-chosen secrets needing a slow hash.
- **Secrets never appear in the frontend bundle.** Only
  `NEXT_PUBLIC_API_URL` (a base URL, not sensitive) is exposed via
  `NEXT_PUBLIC_*`; grepped the entire frontend for every other secret
  variable name and found none. Auth is cookie-based (`credentials:
  "include"`), never a bearer token held in JS/localStorage — the one
  `localStorage` use in the whole frontend stores a UI preference (the
  current org ID), nothing sensitive.
- **Secrets never appear in git history.** Checked `git log --all` for any
  `*.env` file ever being added (none), and for `sk-ant-`/`ghp_`/
  `github_pat_`/PEM private-key blocks anywhere across all refs (none).
  Only the two `.env.example` files are tracked, both with blank secret
  values.
- **Error responses.** The one registered exception handler
  (`app/main.py`) only converts the app's own `AppError` hierarchy into a
  `{"error": {"code", "message"}}` envelope. A genuinely unhandled
  exception falls through to Starlette's default (undebugged, since the
  app is never constructed with `debug=True`) plain-text 500 — no
  traceback, exception message, or file path reaches the client.

## Known gaps / follow-up

- Rate limiting is keyed on `request.client.host` with no trusted-proxy
  awareness — fine for today's direct-to-uvicorn deployment, but must be
  revisited (read a forwarded-for header instead) if a reverse proxy/load
  balancer is added in front of the API, or every request will appear to
  come from the proxy's IP and share one bucket.
- Background-job failure text (`error=str(exc)` on `IndexingJob`,
  `PullRequestAnalysis`, `OnboardingGuide`, `AnalyticsSnapshot`,
  `AiRun`) is surfaced to the same-tenant user who owns that job. This is
  intentional (useful debugging for "why did my indexing run fail"),
  scoped correctly (same repository-access check as everything else on
  that resource), and not a cross-tenant leak — but it does mean an
  internal exception's message text (not a traceback) can reach a client.
  Acceptable today; revisit if a future exception type could embed
  something more sensitive than a DB/HTTP client error string.
- No real transactional email provider is wired up
  (`app/integrations/email/`) — `ConsoleEmailSender` is explicitly a
  development-only stand-in, and now refuses to run in production instead
  of silently leaking tokens (see finding 6). Implementing a real
  `EmailSender` remains open work, independent of this audit.
- No automated dependency/CVE scanning (`pip-audit`, `npm audit`, Dependabot)
  is wired into CI yet — this audit reviewed the application's own code,
  not its third-party dependency tree.
