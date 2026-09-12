# Getting Started

## Prerequisites

- Node.js >= 20, with Corepack enabled (`corepack enable`) for pnpm
- Python 3.12, managed via [uv](https://docs.astral.sh/uv/)
- Docker (for local Postgres)

## Setup

```bash
# Install JS dependencies (web app + tooling)
pnpm install

# Backend: install Python dependencies
cd backend && uv sync && cd ..

# Copy env files and fill in secrets
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env

# Start local Postgres
docker compose up -d postgres

# Create the test database (separate from the dev database; the backend
# test suite truncates all tables between tests, so it must not point at
# your dev data)
docker exec repomind-postgres-1 createdb -U repomind repomind_test
```

## Running the apps

```bash
# Backend (from backend)
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Frontend (from frontend, or `pnpm dev` from the repo root via Turborepo)
pnpm dev
```

- API: http://localhost:8000 (docs at `/docs` outside production)
- Web: http://localhost:3000

## Running everything in Docker

The setup above runs Postgres/Redis in Docker and the API/worker/web apps
natively, which is the faster inner loop (no image rebuild per code change)
and is what CI and the steps above assume. To instead run the **entire**
stack in containers — e.g. to sanity-check a production-shaped build, or to
hand someone a single command that doesn't require Python/Node installed
locally:

```bash
cp backend/.env.example backend/.env   # fill in secrets first — see below
docker compose up -d --build
```

This builds `backend/Dockerfile` (shared by the `api` and `worker`
services — same image, different `command:`, mirroring the two Fly.io
process groups in `docs/deployment/deployment.md`) and `frontend/Dockerfile`
(built with the repo root as context, since `frontend` participates in the
root pnpm workspace), then starts all five services. `api`'s command runs
`alembic upgrade head` before `uvicorn` starts, so migrations are applied
automatically on every `up`.

- API: http://localhost:8000
- Web: http://localhost:3000

Notes:

- `backend/.env` supplies secrets (`JWT_SECRET`, `GITHUB_*`,
  `ANTHROPIC_API_KEY`, `VOYAGE_API_KEY`, ...) via `env_file:` in
  `docker-compose.yml`; `DATABASE_URL`/`REDIS_URL` are overridden in the
  compose file itself to point at the `postgres`/`redis` service names
  instead of `localhost`, since containers don't share the host's network.
- If `AI_PROVIDER=ollama`, point `OLLAMA_HOST` at
  `http://host.docker.internal:11434` (not `localhost`) so the `api`/
  `worker` containers can reach Ollama running on the host.
- `NEXT_PUBLIC_API_URL` is baked into the `web` image at *build* time
  (Next.js inlines `NEXT_PUBLIC_*` vars into the client bundle) — override
  it via `docker compose build --build-arg NEXT_PUBLIC_API_URL=... web` if
  the API isn't reachable at `http://localhost:8000` from the browser.
- `docker compose down` stops everything; add `-v` to also drop the
  Postgres data volume.

## Quality gates

```bash
# Frontend
pnpm lint && pnpm exec tsc --noEmit && pnpm build   # from frontend

# Backend
uv run ruff check . && uv run mypy app && uv run pytest -q   # from backend
```

CI (`.github/workflows/ci.yml`) runs all of the above on every push and PR.
