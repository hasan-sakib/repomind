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

## Quality gates

```bash
# Frontend
pnpm lint && pnpm exec tsc --noEmit && pnpm build   # from frontend

# Backend
uv run ruff check . && uv run mypy app && uv run pytest -q   # from backend
```

CI (`.github/workflows/ci.yml`) runs all of the above on every push and PR.
