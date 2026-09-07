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
cd apps/api && uv sync && cd ../..

# Copy env files and fill in secrets
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env

# Start local Postgres
docker compose up -d postgres
```

## Running the apps

```bash
# Backend (from apps/api)
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Frontend (from apps/web, or `pnpm dev` from the repo root via Turborepo)
pnpm dev
```

- API: http://localhost:8000 (docs at `/docs` outside production)
- Web: http://localhost:3000

## Quality gates

```bash
# Frontend
pnpm lint && pnpm exec tsc --noEmit && pnpm build   # from apps/web

# Backend
uv run ruff check . && uv run mypy app && uv run pytest -q   # from apps/api
```

CI (`.github/workflows/ci.yml`) runs all of the above on every push and PR.
