# RepoMind

AI codebase intelligence and developer onboarding platform. Connect a GitHub
repository and get answers, onboarding documentation, and architecture
insight grounded in the actual code — not a generic AI chat wrapper.

## Status

Authentication, multi-tenancy, GitHub integration, and codebase indexing
are complete and tested: email/password auth, GitHub OAuth login,
organizations with role-based authorization (owner/admin/developer/viewer),
password reset, email verification, a GitHub App connection flow, a
repository overview (metadata, branches, commits, pull requests, issues,
secure idempotent webhook sync), and a full indexing pipeline (shallow
git clone, `.gitignore`-aware file discovery, tree-sitter AST parsing and
chunking for Python/JavaScript/TypeScript/Go, Voyage AI embeddings,
pgvector storage, an `arq`/Redis background job queue, and a live
indexing-progress screen on the frontend) — all backed by a real database
and 79 passing backend tests. AI-powered chat Q&A over connected
repositories (retrieval + citations, the core product loop) is next. See
[`docs/product/README.md`](docs/product/README.md) for scope,
[`docs/architecture/0001-foundation.md`](docs/architecture/0001-foundation.md)
for the initial architecture,
[`docs/architecture/0002-auth-and-multi-tenancy.md`](docs/architecture/0002-auth-and-multi-tenancy.md)
for the auth/tenancy phase,
[`docs/architecture/0003-github-integration.md`](docs/architecture/0003-github-integration.md)
for the GitHub integration phase, and
[`docs/architecture/0004-codebase-indexing.md`](docs/architecture/0004-codebase-indexing.md)
for the indexing pipeline.

## Stack

| Layer      | Choice                                                             |
| ---------- | ------------------------------------------------------------------- |
| Frontend   | Next.js (App Router), TypeScript, Tailwind CSS v4, shadcn/ui       |
| Backend    | FastAPI, Pydantic v2, SQLAlchemy (async), Alembic                 |
| Database   | PostgreSQL + pgvector                                              |
| Indexing   | tree-sitter (AST parsing/chunking), Voyage AI (`voyage-code-3`)   |
| Jobs       | arq + Redis                                                       |
| AI         | Anthropic Claude, behind a swappable provider abstraction          |
| Deployment | Vercel (web), Railway/Fly.io (API + database)                     |

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
