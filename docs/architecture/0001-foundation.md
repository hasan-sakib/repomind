# ADR 0001: Foundational Architecture

**Status:** Accepted
**Date:** 2026-09-08

## Context

RepoMind needed a foundation before any feature work: a monorepo layout, a
backend framework and data layer, a frontend framework, an AI provider
abstraction, and a deployment target.

## Decisions

### Monorepo layout

```
apps/web     Next.js (App Router) frontend
apps/api     FastAPI backend
packages/    Shared code (TypeScript types, config) — populated as needed
docs/        Architecture, API, database, deployment, development, product docs
```

pnpm workspaces + Turborepo manage the JS side. The Python API is a separate
`uv`-managed project under `apps/api` — it does not participate in Turborepo
task graphs, since Python and JS have independent toolchains.

**Why:** A single repo keeps frontend/backend contracts easy to review
together in one PR, without forcing Python into a JS build graph it doesn't
belong in.

### Backend: FastAPI + Pydantic v2 + SQLAlchemy (async) + Alembic

Layered structure under `apps/api/app/`:

- `api/v1/routes/` — HTTP handlers only. No business logic.
- `services/` — business logic, orchestrates repositories and integrations.
- `repositories/` — database access, isolated from service logic.
- `domain/` — ORM models (SQLAlchemy `Base` subclasses).
- `schemas/` — Pydantic request/response models.
- `integrations/github/` — GitHub API client, isolated from domain logic.
- `ai/` — AI provider abstraction (see below).
- `core/` — settings, cross-cutting config.
- `db/` — engine/session setup, Alembic migrations.

**Why:** Route handlers stay thin and testable; swapping the DB driver or the
AI vendor never touches business logic, per the project's core engineering
principles.

### AI provider abstraction

`app/ai/provider.py` defines an `AIProvider` ABC (`complete`, `stream`).
`app/ai/providers/anthropic_provider.py` is the current (and only)
implementation, using Claude Opus 5 with adaptive thinking by default.
`app/ai/factory.py` selects the provider from `Settings.ai_provider`.

**Why:** Business logic and API routes depend only on `AIProvider`, never on
the `anthropic` SDK directly — a second provider can be added without
touching call sites.

### Frontend: Next.js (App Router) + TypeScript + Tailwind v4 + shadcn/ui

shadcn/ui is initialized with its `@base-ui/react`-backed components (shadcn
moved off Radix in this version). React Query handles server state; a thin
`apiFetch` wrapper in `lib/api-client.ts` is the only place that talks to the
backend over HTTP.

**Why:** Server components by default, client components only where
interactivity requires it. The full design-system customization (tokens,
typography scale, component variants) is deliberately deferred to the next
phase — see the Design System phase in project scope — rather than bundled
into foundational scaffolding.

### Database: PostgreSQL, async driver (`asyncpg`)

Local dev runs Postgres via `docker-compose.yml`. Alembic is wired for async
autogenerate: `app/db/migrations/env.py` imports `Base.metadata` from
`app/domain/models.py`, which will aggregate model modules as they're added.

### Deployment target

Next.js on Vercel; FastAPI + Postgres on Railway or Fly.io. Revisit if cost or
platform limits become an issue — see `docs/deployment/`.

### MVP scope (Phase 1)

The first vertical slice is **repo ingestion + AI chat Q&A**: connect a GitHub
repo, index it, let a user ask grounded questions about the codebase. Every
other product surface (onboarding guide generation, architecture
visualization) builds on this ingestion + retrieval core, so it goes first.

## Consequences

- Adding a second AI provider means implementing `AIProvider`, not touching
  callers.
- Adding the first domain models (Phase 1) will produce the first real
  Alembic migration — none exists yet because there's nothing to migrate.
- The frontend has no visual design system yet beyond shadcn defaults; this
  is intentional and tracked as the next phase of work, not an oversight.
