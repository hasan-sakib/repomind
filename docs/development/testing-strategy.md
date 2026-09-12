# Testing Strategy

**Status:** Living document — reflects the test suite built out in Phase 14.
Update it whenever the testing approach changes, not just when a new
audit happens.

This documents what's tested, how, why, and where — for both `backend`
(294 tests before this phase, 329 after) and `frontend` (0 tests before
this phase, 90 after — there was no frontend test runner at all until
now). See `docs/architecture/security.md` for the security-focused audit
that produced several of the backend's authorization tests.

## Philosophy

- **Test behavior, not implementation.** Every test in this suite asserts
  on an outcome a real caller would observe (an HTTP response, a rendered
  DOM, a returned/persisted value) — never on private internals that would
  make the test break on a harmless refactor.
- **Real dependencies over mocks, wherever practical.** Backend tests run
  against a real Postgres database (`repomind_test`) and a real Redis
  instance, not in-memory fakes — a fake DB/query layer is exactly where a
  query-construction bug (the kind repository tests exist to catch) would
  go unnoticed. Only genuinely external systems (GitHub's API, an AI
  provider) are mocked, via `pytest-httpx`/fake provider classes already
  established in `tests/conftest.py`.
- **Fixtures and factories over copy-pasted setup.** Both suites now have a
  shared factory module (`backend/tests/factories.py`,
  `frontend/test/factories.ts`) so a test states only the fields it
  actually cares about, and a model gaining a required field means editing
  one file, not every test that builds one.
- **Every critical flow is covered from both ends** — a backend
  integration test proves the API contract; a frontend test proves the UI
  actually drives that contract correctly (right method, right body, right
  navigation/error handling on the response). See the mapping table below.

## Backend (`backend/tests/`)

Layout: `tests/unit/` (no I/O — pure functions, schema validation, config
validators) and `tests/integration/` (anything touching Postgres/Redis/the
real FastAPI app via `httpx.AsyncClient`).

### Unit tests

Pure logic with no database: password hashing (`test_password.py`), token
generation/expiry/signature verification (`test_tokens.py`,
`test_webhook_signature.py`), role-ranking (`test_roles.py`), config
validation (`test_config.py` — the `JWT_SECRET` strength validator from
the security audit), rate-limit counter logic (`test_rate_limit.py`), git
argument-injection guards (`test_git_fetcher.py`), diff parsing, chunking,
discovery, classification, and result-schema validation for the
indexing/onboarding/PR-analysis/analytics subsystems (`test_indexing_*`,
`test_onboarding_*`, `test_pr_analysis_*`, `test_analytics_*`,
`test_architecture_classifier.py`, `test_github_schemas.py`,
`test_retrieval_intent.py`).

### Repository tests (`tests/integration/test_repositories.py`)

**New in this phase.** Exercises `app/repositories/*.py` functions
directly against a real DB session — bypassing the service and route
layers entirely. This is a distinct category from API integration tests
on purpose: a route/service test only proves a query returns *something*
on its happy path; it can't prove the query's *filter* is right, because
the happy path never needed the edge case. These tests target exactly
that — e.g.:

- `user_repository.get_by_email` is case-sensitive (an exact-match
  assertion a service test would never think to make).
- `repository_membership_repository.get` scoped to repo A returns nothing
  for the same user against repo B — the literal invariant
  `require_repository_access` depends on.
- `pull_request_repository.get` scoped by `(repository_id, number)`, not
  `number` alone — two repositories can both have a PR #1.
- `conversation_repository.list_for_repository` orders by `updated_at`
  descending and excludes another repository's conversations.

Uses `tests/factories.py` (see below) for setup.

### Service tests

Business logic one layer above repositories: `test_chat_service.py`,
`test_pr_analysis_service.py` / `test_pr_analysis_context.py`,
`test_onboarding_service.py` / `test_onboarding_context.py`,
`test_analytics_service.py`, `test_entitlements.py`,
`test_architecture_graph_builder.py`, `test_retrieval_dependency_graph.py`.
These call into `app/services/*.py` directly (not through HTTP), so they
can assert on intermediate state (e.g. a cached analysis's exact risk
level) without an HTTP round-trip.

### API integration tests

Full-stack, via `httpx.AsyncClient` against the real `FastAPI` app
(`tests/conftest.py`'s `client` fixture) and a real (truncated-between-
tests) Postgres database: `test_auth.py`, `test_organizations.py` /
`test_organization_settings.py`, `test_repository_connect.py`,
`test_repository_permissions.py`, `test_pull_request_routes.py`,
`test_chat_routes.py`, `test_onboarding_routes.py`,
`test_analytics_routes.py`, `test_architecture_routes.py`,
`test_api_keys.py`, `test_webhooks.py`, `test_websocket_route.py`,
`test_health.py`.

### Authorization tests

Two layers:

1. **Scattered `test_non_member_gets_404_*` tests** across almost every
   route file above — the "obvious" attack (using someone else's
   `organization_id`/`repository_id` directly in the URL) is stopped by
   `require_organization_role`/`require_repository_access`
   (`app/api/deps.py`) before a handler ever runs, and every one of these
   tests confirms a 404 (not a 403 — see
   `docs/architecture/security.md`'s note on not leaking existence).
2. **`tests/integration/test_authorization_cross_tenant.py` — new in this
   phase.** The *subtler* attack: a user legitimately authenticated to
   their *own* repository, presenting their own (valid) `repository_id`
   in the URL, but referencing a **nested resource id** (a conversation, an
   indexing job) that belongs to a *different* organization's repository.
   `chat_service.get_conversation_or_raise` and
   `indexing_service.get_job_or_raise` fetch the resource by its own id
   first and only *then* compare its `repository_id` — correct, but
   nothing exercised that comparison directly before this file. It now
   does, for both conversations (get + feedback) and indexing jobs
   (get + list), each with two real organizations/repositories connected
   through the actual GitHub-App-install HTTP flow (mocked GitHub API
   responses, not a shortcut).

### Fixtures and factories

- `tests/conftest.py` — the `db_session` fixture (real Postgres,
  `TRUNCATE`d between tests, not a rolled-back transaction — see its
  docstring for why), `client`/`second_client`/`third_client` (independent
  authenticated `httpx.AsyncClient`s sharing one `db_session`, for
  multi-user scenarios), `FakeArqPool` (runs an enqueued job inline instead
  of touching real Redis-backed arq), `captured_emails` (intercepts
  `ConsoleEmailSender` so a test can read a password-reset/verification
  token out of the "sent" email instead of parsing logs), and (new this
  phase) an autouse `_reset_rate_limits` fixture — rate-limit counters live
  in Redis, which isn't reset by the DB truncation, so without this an
  earlier test's requests to `/auth/login` would count against a later,
  unrelated test's limit.
- `tests/factories.py` — **new in this phase.** `create_user`,
  `create_organization`, `create_organization_member`, `create_repository`
  (+ installation), `create_repository_membership`, `create_pull_request`,
  `create_conversation` — each flushes (never commits) so the caller gets a
  real id back immediately while still controlling its own transaction
  boundary. Several integration test files had independently hand-rolled
  their own version of `create_repository` before this existed
  (`test_architecture_graph_builder.py`'s `_create_repository`,
  `test_repository_connect.py`'s HTTP-flow equivalent for route-level
  tests) — those weren't migrated in this pass (no behavior changed, low
  value to touch working tests), but any *new* backend test needing this
  kind of setup should use `tests/factories.py`, not write another local
  copy.

### Running it

```bash
cd backend
uv run ruff check .        # lint
uv run mypy app             # types (app/ only — tests/ isn't part of this gate)
uv run pytest -q            # 329 tests, needs postgres+redis: docker compose up -d postgres redis
```

## Frontend (`frontend/`)

**New in this phase**: there was no test runner at all before this —
`docs/architecture/design-system.md`'s "known gaps" section noted the
frontend was previously verified only via ad hoc Playwright scripts, not
a committed suite. Added: Vitest + `@testing-library/react` +
`@testing-library/user-event` + jsdom, configured in
`vitest.config.mts`/`vitest.setup.ts`, run via `pnpm test` (from `frontend/`
or the repo root via Turborepo — `turbo.json` already had a `test` task
wired up from Phase 1, unused until now).

### Unit tests (colocated `*.test.ts` next to their source)

Pure functions in `lib/`: `format-time.test.ts` (relative-time formatting,
with `vi.useFakeTimers`/`setSystemTime` instead of relying on real wall-
clock time — the classic source of a flaky date test), `github-url.test.ts`
(`buildBlobUrl` — the exact function the "view source reference" flow
depends on to link a citation to the right file/line range),
`analytics-merge.test.ts`, `analytics-time.test.ts` (date-bucket filtering
relative to a snapshot's own latest date, not "today" — matches the
function's own documented intent), `validation/auth.test.ts` (the Zod
schemas backing every auth form), and
`realtime/apply-event.test.ts` (`applyRealtimeEvent` — patches the React
Query cache in place for every WebSocket event resource type; tested
against a real `QueryClient`, not a mock, since the whole point is proving
the *cache keys and shapes* it writes match what the pages that read them
expect).

### Component tests (colocated `*.test.tsx`)

Presentational/interactive components rendered with
`@testing-library/react`: `EmptyState`, `ErrorState` (including the retry
button's `onClick`), `FieldError`, `RepositoryStatusBadge`,
`SourcePanel` (renders a source's file/line/commit info and links it to
the exact right GitHub URL — the rendering half of "view source
reference"), and `DetailPanel` (the architecture explorer's click-to-
inspect side panel — see below for why this, and not the graph canvas
itself, is what's tested).

### Critical interaction tests

One test file per flow, mocking only the API-client functions (never
`fetch` directly) and `next/navigation`'s `useRouter`, then driving the
UI exactly as a user would (`userEvent.type`/`click`) and asserting on
the resulting API call *and* the resulting UI state:

| # | Flow | Test file |
|---|------|-----------|
| 1 | Register | `app/(auth)/register/page.test.tsx` |
| 2 | Login | `app/(auth)/login/page.test.tsx` |
| 3 | Create organization | `components/shell/create-org-dialog.test.tsx` |
| 4 | Invite member | `app/(dashboard)/settings/members/add-member-dialog.test.tsx` |
| 5 | Connect GitHub | `app/(dashboard)/repositories/connect/page.test.tsx` |
| 6 | Connect repository | `app/(dashboard)/repositories/connect/page.test.tsx` (same file — one page covers both) |
| 7 | Index repository | `app/(dashboard)/repositories/[repositoryId]/indexing/page.test.tsx` |
| 8 | Ask AI question | `components/chat/chat-shell.test.tsx` (streamed via a fake `AsyncGenerator`, exercising the real token-by-token accumulation logic) |
| 9 | View source reference | `components/chat/source-panel.test.tsx` |
| 10 | View architecture | `components/architecture/detail-panel.test.tsx` (the click-to-inspect panel — see note below on the graph canvas itself) |
| 11 | Analyze PR | `app/(dashboard)/repositories/[repositoryId]/pull-requests/[number]/page.test.tsx` |

Every one of these flows also has backend API-integration coverage (see
the backend section above and the flow-to-file references there); the
frontend tests prove the *client* side of the same contract, not a
duplicate of the backend's own assertions.

### Fixtures and factories

- `test/factories.ts` — `makeUser`, `makeOrganization`,
  `makeOrganizationMembership`, `makeMember`, `makeRepository`,
  `makePullRequest`, `makePullRequestAnalysis`, `makeIndexingJob`,
  `makeSourceReference`, `makeCommit`, `makeConversation` — mirrors
  `lib/types.ts`; kept in sync with it deliberately (a type change that
  breaks a factory is a signal to update the factory, not silence it).
- `test/render.tsx` — `renderWithProviders`, wrapping a component in a
  fresh `QueryClient` (retries disabled — a failing mocked request
  retrying in the background after a test already asserted on it is a
  classic source of test flakiness) and `CurrentOrgProvider`.
- `vitest.setup.ts` — polyfills `Element.prototype.scrollIntoView` (jsdom
  doesn't implement it; several real components call it, e.g. `SourcePanel`
  scrolling the active citation into view) and runs
  `@testing-library/react`'s `cleanup()` after every test.

### Avoiding brittleness — specific decisions made in this phase

- **`use(params)` route pages were split into a thin wrapper + an exported,
  directly-testable inner component.** Next's `params: Promise<...>` +
  React's `use()` is real in production (the framework's own streaming
  machinery resolves it), but a bare `render()` in a unit test has no such
  machinery — `use()` on a manually-constructed `Promise.resolve(...)`
  reliably suspends forever in this React/RTL version combination (verified
  with a minimal repro before concluding this, not assumed). Trying to
  paper over that with fake timers or manual `act()` flushing produces
  exactly the kind of test that passes today and mysteriously hangs after
  the next React/RTL bump. Instead,
  `RepositoryIndexingPage`/`PullRequestDetailPage` now each delegate to an
  exported `RepositoryIndexingView`/`PullRequestDetailView` taking plain
  props — the default export's only job is unwrapping `params`. Tests
  render the view directly; production behavior is unchanged (the default
  export is still what Next.js routes to).
- **A pre-existing flaky backend test was found and fixed, not left in
  the suite.** `test_decode_rejects_wrong_signature` flipped the *last*
  character of a JWT to prove tampering is rejected — but a 32-byte
  HMAC-SHA256 signature's base64url encoding ends in a character that can
  encode as few as 2 real bits, so that flip didn't always change the
  decoded signature bytes (confirmed by running it 20+ times: roughly 1
  in 5 runs passed the "tampered" token straight through as if it were
  valid, meaning the test was accidentally *not testing anything* on those
  runs). Fixed by tampering with the *first* character of the signature
  segment instead, which always encodes real bits — verified deterministic
  across 20 repeated runs after the fix.
- **The React Flow architecture canvas itself is not rendered in these
  tests.** `ArchitectureExplorer` wraps `@xyflow/react`, which measures
  real DOM layout (`ResizeObserver`, `getBoundingClientRect`) that jsdom
  doesn't meaningfully provide — a test that renders the canvas would
  either need heavy, brittle polyfilling or would be asserting on jsdom's
  fake measurements rather than real behavior. Since the actual point of
  interest — inspecting a node's symbols/dependencies/dependents/recent
  commits once clicked — lives in the plain, prop-driven `DetailPanel`
  component with no canvas dependency, that's what's tested instead. The
  canvas rendering itself was manually verified in Phase 12's design
  audit (real screenshots via Playwright against a running app) and
  remains a gap for a future committed Playwright/E2E suite, not silently
  assumed to work.
- **Streaming SSE is tested via a fake `AsyncGenerator`, not a mocked
  `fetch` stream.** `askQuestion`'s return type (`AsyncGenerator<
  ChatStreamEvent>`) is the actual seam between `lib/api/chat.ts` and
  `ChatShell` — replacing the generator directly exercises `ChatShell`'s
  real token-accumulation/sources/done handling without needing to
  fabricate a byte-level SSE response and fight the browser `fetch`
  streaming API inside jsdom.
- **Rate-limit and other Redis-backed state is reset between backend
  tests explicitly** (see the `_reset_rate_limits` fixture above) rather
  than accepting order-dependent pollution across the suite.

### Running it

```bash
cd frontend
pnpm test          # vitest run — 90 tests
pnpm test:watch    # vitest, watch mode
pnpm lint && pnpm exec tsc --noEmit && pnpm build   # unchanged from before this phase
```

## Known gaps / follow-up

- No committed Playwright (or other) end-to-end suite yet — Phase 12's
  design audit and this phase's manual verification both used ad hoc
  Playwright scripts against a running dev stack, not a checked-in,
  CI-runnable E2E suite. The frontend critical-interaction tests plus the
  backend's full-stack API integration tests (real Postgres, real route
  handlers, mocked GitHub API only) together cover every critical flow's
  actual logic; a true browser E2E suite would additionally catch
  CSS/layout/visual regressions and real-browser-only bugs, which neither
  of the above can.
- The React Flow architecture graph's own rendering (pan/zoom, node
  layout, edge drawing) has no automated test — see the note above.
- No coverage-percentage gate is enforced in CI for either suite; this
  phase focused on covering the explicitly-named critical flows and
  filling the concrete category gaps (repository tests, cross-tenant
  authorization tests, a frontend suite existing at all) rather than
  chasing a number.
