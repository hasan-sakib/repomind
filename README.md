# RepoMind

AI codebase intelligence and developer onboarding platform. Connect a GitHub
repository and get answers, onboarding documentation, and architecture
insight grounded in the actual code — not a generic AI chat wrapper.

## Status

Authentication and multi-tenancy foundation is complete and tested: email/
password auth, GitHub OAuth login, organizations with role-based
authorization (owner/admin/developer/viewer), password reset, email
verification, and a real dashboard shell — all backed by a real database
and 39 passing backend tests. Repository connection and AI chat Q&A (the
core product loop) are the next phase. See
[`docs/product/README.md`](docs/product/README.md) for scope,
[`docs/architecture/0001-foundation.md`](docs/architecture/0001-foundation.md)
for the initial architecture, and
[`docs/architecture/0002-auth-and-multi-tenancy.md`](docs/architecture/0002-auth-and-multi-tenancy.md)
for what this phase actually built.

## Stack

| Layer      | Choice                                                       |
| ---------- | ------------------------------------------------------------ |
| Frontend   | Next.js (App Router), TypeScript, Tailwind CSS v4, shadcn/ui |
| Backend    | FastAPI, Pydantic v2, SQLAlchemy (async), Alembic            |
| Database   | PostgreSQL                                                   |
| AI         | Anthropic Claude, behind a swappable provider abstraction    |
| Deployment | Vercel (web), Railway/Fly.io (API + database)                |

## Repository layout

```
apps/web     Next.js frontend
apps/api     FastAPI backend
packages/    Shared code across apps (as needed)
docs/        Architecture, API, database, deployment, development, product docs
```

## Getting started

See [`docs/development/getting-started.md`](docs/development/getting-started.md).

## Documentation

- [`docs/architecture/`](docs/architecture/) — architectural decision records
- [`docs/api/`](docs/api/) — API reference
- [`docs/database/`](docs/database/) — schema documentation
- [`docs/deployment/`](docs/deployment/) — deployment guides
- [`docs/development/`](docs/development/) — local dev setup
- [`docs/product/`](docs/product/) — product scope and roadmap
