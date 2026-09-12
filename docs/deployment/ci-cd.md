# CI/CD

**Status:** Current — this is the authoritative deployment plan (Phase 15),
superseding the Fly.io-centric sketch in `deployment.md` §4–9 (that
document's CORS/cookie same-site reasoning in §3, its migration-safety
rules in §7, and its observability notes in §10 are provider-agnostic and
still apply as written; see the note at the top of that file).

## What's automated today

Three GitHub Actions workflows, each scoped to only the part of the
monorepo it actually needs to run for (a backend-only PR doesn't wait on a
`pnpm install` + Next.js build, and vice versa):

### `.github/workflows/frontend-ci.yml`

Triggers on any push to `main` or PR touching `frontend/**` (or the root
pnpm lockfile/workspace files, since `frontend` participates in the root
pnpm workspace). One job:

1. Install dependencies (`pnpm install --frozen-lockfile`)
2. Lint (`pnpm lint`)
3. Typecheck (`pnpm exec tsc --noEmit`)
4. Test (`pnpm test` — the Vitest suite from
   `docs/development/testing-strategy.md`)
5. Production build (`pnpm build`)

**Caching:** `actions/setup-node`'s built-in `cache: pnpm`, keyed on
`pnpm-lock.yaml` — a clean install still runs every time (correctness),
but skips re-downloading unchanged packages (speed).

### `.github/workflows/backend-ci.yml`

Triggers on any push to `main` or PR touching `backend/**`. One job, with
real Postgres and Redis service containers (the backend's test suite
needs both — see `docs/development/testing-strategy.md`):

1. Install dependencies (`uv sync`)
2. Lint (`uv run ruff check .`)
3. Typecheck (`uv run mypy app`)
4. Test (`uv run pytest -q`)

**Caching:** `astral-sh/setup-uv`'s `enable-cache: true`, keyed on
`backend/uv.lock`.

### `.github/workflows/security.yml`

Triggers on push/PR like the two above, but **not** path-scoped — a
dependency can grow a new CVE on a PR that touches neither app's source,
and severities change over time independent of any code change at all.
Also runs on a **weekly schedule** (Mondays 06:00 UTC) and via
`workflow_dispatch` for exactly that reason. Four independent jobs:

| Job | Tool | Blocks the check? |
|---|---|---|
| `dependency-audit-frontend` | `pnpm audit --audit-level=high` | Yes — fails on high/critical advisories |
| `dependency-audit-backend` | `pip-audit` (via `uv run --with pip-audit`, against the actually-installed venv) | Yes — fails on any known advisory |
| `secret-scan` | `gitleaks` (official Docker image, run directly — not the marketplace action, to avoid depending on that action's own licensing terms), scanning full git history, not just the current commit | Yes |
| `vulnerability-scan` | `aquasecurity/trivy-action` filesystem scan (both lockfiles, for a second advisory-database opinion, plus Dockerfile/IaC misconfiguration checks) | **No** — findings are uploaded as SARIF to the repo's **Security** tab instead of failing the build. A newly-disclosed upstream CVE with no fix yet shouldn't block every unrelated PR; it should be visible and triaged instead. |

`.gitleaks.toml` (repo root) allowlists the two fixed, clearly-fake test/CI
secrets (`tests/conftest.py`'s dummy `JWT_SECRET`, `backend-ci.yml`'s own
copy) by exact value — not by disabling the underlying detection rule —
so the check stays meaningfully blocking for an actual secret anywhere
else. Adding a new intentionally-fake test fixture that looks like a
secret means adding its exact value there, with a comment saying why.

## Environments

| | Development | Staging | Production |
|---|---|---|---|
| Who runs it | Each developer, locally | Shared, pre-release | Real users |
| Frontend | `pnpm dev` (localhost:3000) | Vercel Preview deployment (one per PR, or a persistent `staging` branch deployment) | Vercel Production deployment (the `main` branch) |
| Backend | `uvicorn --reload` (localhost:8000) or the full `docker compose up` stack — see `docs/development/getting-started.md` | A separate Render/Railway service, deployed from a `staging` branch | A separate Render/Railway service, deployed from `main` |
| Database | Local Postgres (Docker Compose, `pgvector/pgvector:pg16`) | A separate Supabase project | A separate Supabase project |
| Redis | Local Redis (Docker Compose) | A separate Upstash database | A separate Upstash database |
| `ENVIRONMENT` | `development` | `production`\* | `production` |
| Secrets source | `backend/.env` / `frontend/.env` (gitignored, never committed) | Render/Railway's + Vercel's own environment-secret stores, scoped to the staging service/deployment | Render/Railway's + Vercel's own environment-secret stores, scoped to the production service/deployment |

\* **Why staging uses `ENVIRONMENT=production`, not a third `staging`
literal:** `app/core/config.py`'s `environment` field is
`Literal["development", "test", "production"]`, and the only things it
gates are security-relevant (cookies get `Secure` only when
`environment == "production"`; `/docs` Swagger UI is hidden only in
`production`). Staging should behave *identically* to production on both
counts — it's reachable over the public internet under a real domain, so
it needs secure cookies and no exposed API docs just as much as
production does. Giving it its own `staging` value would mean either
adding a third branch to both of those checks (for zero behavioral
difference) or accidentally leaving staging with `Secure`-less cookies.
Staging is kept isolated from production by using **entirely separate
infrastructure** (its own Supabase project, its own Upstash database, its
own Render/Railway service, its own Vercel deployment) instead — the
`ENVIRONMENT` value doesn't need to carry that distinction.

## Deployment strategy

| Layer | Platform | Why |
|---|---|---|
| Frontend | **Vercel** | Purpose-built for Next.js (the framework's own maintainer); zero-config preview deployments per PR come for free, which is exactly the "staging" story above. |
| Backend (API + worker) | **Render or Railway** | Both run a plain Docker container (this repo already has `backend/Dockerfile`, built for exactly this — see `docs/development/getting-started.md`'s Docker section) with git-push-to-deploy, a managed TLS cert, and a dashboard-based secrets store — no Kubernetes/IaC to hand-roll for an MVP-stage deployment. Pick one; this doc doesn't need to choose between them further; the API/worker are two *services* built from the same image regardless of which platform runs them (mirroring the two Fly.io "process groups" concept from the superseded `deployment.md` §4, and the two `docker-compose.yml` services `api`/`worker` already defined). |
| Database | **Supabase PostgreSQL** | Managed Postgres with the `pgvector` extension available (`CodeChunk.embedding` similarity search depends on it — see `docs/architecture/0004-codebase-indexing.md`), a generous free tier for an MVP-stage deployment, and a dashboard for one-off inspection without needing to open a psql tunnel by hand. |
| Redis | **Upstash** | Serverless Redis, billed per-request rather than per-instance-hour — a good fit for this app's actual Redis usage (the arq job queue and the real-time pub/sub event bus, both bursty, not constantly busy). Reachable over TLS from anywhere, so no VPC peering to set up between three different platforms. |

**Deliberately no `deploy.yml` workflow.** All three of Vercel, Render, and
Railway deploy directly from a git push via their own GitHub integration —
adding a GitHub Actions step to also call their CLI/API would just be a
slower, more brittle second way to do the same thing. The **release flow**
is:

1. Open a PR. `frontend-ci.yml`/`backend-ci.yml` (whichever the changed
   paths trigger) and `security.yml` all run. Vercel also deploys a
   preview automatically.
2. Merge to `main` once CI is green and the PR is approved (see branch
   protection below).
3. Vercel deploys the new production frontend; Render/Railway deploys the
   new production backend — both triggered by their own webhook on the
   `main` push, independent of each other and of GitHub Actions.
4. The backend's container entrypoint runs `alembic upgrade head` before
   `uvicorn` starts (see `docker-compose.yml`'s `api` service `command:`,
   which the production container should mirror) — migrations apply
   automatically on every deploy, the same way they already do locally.

If a deploy needs to be gated on something CI can't express (e.g. a
data migration that must run before the new code, not automatically on
container start), promote that specific step to a manual, documented
runbook rather than retrofitting a `deploy.yml` — that's a decision to
make when it's actually needed, not speculatively now.

## Environment variables

Full field-by-field reference: `backend/.env.example` (every
`app/core/config.py` field, fully documented — this is the "complete
`.env.example`" this phase asked for) and `frontend/.env.example` (just
`NEXT_PUBLIC_API_URL` — genuinely the only frontend env var that exists,
confirmed by a repo-wide grep in `docs/architecture/security.md`'s audit).
Never commit a populated `.env` file — both are gitignored.

Where each one actually lives, per environment:

| Variable | Local dev | CI | Staging / Production |
|---|---|---|---|
| Everything in `backend/.env.example` with a real value required (`JWT_SECRET`, `GITHUB_APP_PRIVATE_KEY`, `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, `GITHUB_WEBHOOK_SECRET`, `GITHUB_CLIENT_SECRET`, ...) | `backend/.env` (gitignored) | A fixed, clearly-fake value inline in `backend-ci.yml`'s `env:` block (e.g. `JWT_SECRET: ci-test-secret-...`) — safe only because it signs tokens against an ephemeral, throwaway test database that's destroyed at the end of the job | Render/Railway's own environment-variable/secrets UI, scoped to that one service. **Never** a GitHub Actions secret — GitHub Actions doesn't deploy this app, so it has no reason to hold its production secrets at all. |
| `DATABASE_URL` | Local Docker Postgres | The `postgres` service container (`localhost:5432`) | The Supabase project's connection string (Render/Railway's own secrets UI) |
| `REDIS_URL` | Local Docker Redis | The `redis` service container (`localhost:6379`) | The Upstash database's connection string (same) |
| `NEXT_PUBLIC_API_URL` | `frontend/.env` (`http://localhost:8000`) | `vars.NEXT_PUBLIC_API_URL` (a GitHub Actions **variable**, not a secret — this value ends up in the shipped client bundle regardless, so there's nothing to protect) with a placeholder fallback, since `frontend-ci.yml`'s build only needs to prove the build succeeds | Vercel's own Environment Variables UI, scoped separately per Preview/Production (Vercel's built-in distinction — see `deployment.md` §3/§8 for the same variable's role in the CORS/cookie same-site constraint, which still applies unchanged under this stack) |

**Any secret that isn't referenced through `secrets.*` or a platform's own
secrets UI in the paragraphs above does not belong in this repository at
all** — that's the one rule every workflow file and this doc are held to.

## Branch protection recommendations

Not something a workflow file can set (it's a repository setting, not a
CI step) — recommended for `main` under **Settings → Branches → Branch
protection rules**:

- **Require a pull request before merging** — no direct pushes to `main`.
- **Require approvals** — at least 1.
- **Require status checks to pass before merging**, specifically:
  - `Frontend CI / Lint, typecheck, test, build`
  - `Backend CI / Lint, typecheck, test`
  - Optionally, once the dependency-audit jobs are consistently clean:
    `Security / Dependency audit (frontend)` and
    `Security / Dependency audit (backend)`. `Security / Secret detection
    (gitleaks)` is a strong candidate to require immediately — a true
    positive there should never be mergeable. `Security / Vulnerability
    scan (Trivy)` is intentionally non-blocking (see the table above) and
    should stay that way even as a "required" check would defeat that
    design — don't add it here.
- **Require branches to be up to date before merging** — prevents merging
  a PR whose CI ran against a stale base.
- **Require conversation resolution before merging.**
- **Do not allow force pushes** and **do not allow deletions** of `main`.
- Consider **Require signed commits** once the team is set up for it — not
  a blocker for an MVP-stage repo, but cheap to turn on early rather than
  retrofit later.

## Known gaps / follow-up

- No staging/production infrastructure is actually provisioned yet (same
  status as the superseded `deployment.md`) — this document is the plan
  to provision against, not a record of what's live.
- No `FLY_API_TOKEN`-style deploy secret exists in GitHub Actions, and
  shouldn't — see "Deliberately no `deploy.yml`" above.
- `pip-audit`/`pnpm audit`/Trivy can all report a vulnerability with no
  available fix yet (a transitive dependency waiting on its own upstream
  patch). When that happens: document the specific advisory ID and why
  it's accepted (blast radius, exploitability given this app's actual
  usage) rather than silencing the tool wholesale — an unexplained
  ignore-list entry is worse than a red check.
