# RepoMind

AI codebase intelligence and developer onboarding platform. Connect a GitHub
repository and get answers, onboarding documentation, and architecture
insight grounded in the actual code — not a generic AI chat wrapper.

## Status

Authentication, multi-tenancy, GitHub integration, codebase indexing, the
AI/RAG chat engine, the architecture/dependency explorer, AI pull request
intelligence, automatic developer onboarding, engineering analytics,
real-time infrastructure, and SaaS management are complete and tested:
email/password auth, GitHub OAuth login, organizations with role-based
authorization (owner/admin/developer/viewer), password reset, email
verification, a GitHub App connection flow, a repository overview
(metadata, branches, commits, pull requests, issues, secure idempotent
webhook sync), a full indexing pipeline (shallow git clone,
`.gitignore`-aware file discovery, tree-sitter AST parsing and chunking
for Python/JavaScript/TypeScript/Go, Voyage AI embeddings, pgvector
storage, an `arq`/Redis background job queue, and a live
indexing-progress screen), a code-aware chat engine — hybrid retrieval
(pgvector + an import-based dependency graph + git history), query-intent
routing via a small LangGraph pipeline, Voyage reranking, streamed
responses with real file/line source citations, and a three-pane chat
interface (conversation history, streaming markdown with syntax
highlighting and clickable citations, source panel) — an architecture
explorer (package- and module-level dependency graphs derived from the
same indexed data, pan/zoom/search/filter, a click-to-inspect detail
panel with symbols/dependencies/dependents/recent commits, and
progressive package → module expansion) — AI pull request intelligence
(risk-level analysis grounded in real changed files/symbols/dependents/
existing tests, cached per commit, with a structured PR risk report UI)
— automatic developer onboarding (a generated guide — architecture
overview, important modules, a learning path, dev setup, database
structure, and FAQ — mostly deterministic from indexed data, with AI
reserved for the parts that genuinely need synthesis, plus per-developer
progress tracking) — and engineering analytics (repository activity,
commit frequency, PR throughput and cycle time, open issues, contributor
activity, and file/architecture-level code hotspots — every metric
computed from real commit/PR/issue data with no AI involved, charted with
time-range and contributor filters) — and real-time infrastructure (a
unified WebSocket event system pushing indexing progress, repository
sync, webhook processing, and AI generation status straight into the
frontend's cache with no polling refresh while connected, a reconnecting
connection with backoff and a live connection-status indicator, and a
wired-up notification bell) — and SaaS management (a centralized
entitlement system enforcing Free/Pro/Team plan limits — e.g. 3/25/
unlimited connected repositories — through one module rather than
scattered checks; organization rename, member roles, and per-repository
access management; organization-scoped API keys with hashed storage and
one-time secret reveal; a usage dashboard combining plan quotas with
real AI-token and generation-run counts; an admin-visible audit log; and
a billing-provider abstraction with a Null implementation and an
interim, owner-only manual plan switch while no real payment provider is
configured) — all backed by a real database and
294 passing backend tests. See
[`docs/product/README.md`](docs/product/README.md) for scope,
[`docs/architecture/0001-foundation.md`](docs/architecture/0001-foundation.md)
for the initial architecture,
[`docs/architecture/0002-auth-and-multi-tenancy.md`](docs/architecture/0002-auth-and-multi-tenancy.md)
for the auth/tenancy phase,
[`docs/architecture/0003-github-integration.md`](docs/architecture/0003-github-integration.md)
for the GitHub integration phase,
[`docs/architecture/0004-codebase-indexing.md`](docs/architecture/0004-codebase-indexing.md)
for the indexing pipeline,
[`docs/architecture/0005-ai-rag-engine.md`](docs/architecture/0005-ai-rag-engine.md)
for the AI/RAG chat engine,
[`docs/architecture/0006-architecture-dependency-graph.md`](docs/architecture/0006-architecture-dependency-graph.md)
for the architecture explorer,
[`docs/architecture/0007-ai-pull-request-intelligence.md`](docs/architecture/0007-ai-pull-request-intelligence.md)
for PR intelligence, and
[`docs/architecture/0008-developer-onboarding.md`](docs/architecture/0008-developer-onboarding.md)
for developer onboarding, and
[`docs/architecture/0009-engineering-analytics.md`](docs/architecture/0009-engineering-analytics.md)
for engineering analytics, and
[`docs/architecture/0010-realtime-infrastructure.md`](docs/architecture/0010-realtime-infrastructure.md)
for real-time infrastructure, and
[`docs/architecture/0011-saas-management.md`](docs/architecture/0011-saas-management.md)
for SaaS management.

## Stack

| Layer      | Choice                                                                                                                                              |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend   | Next.js (App Router), TypeScript, Tailwind CSS v4, shadcn/ui                                                                                        |
| Backend    | FastAPI, Pydantic v2, SQLAlchemy (async), Alembic                                                                                                   |
| Database   | PostgreSQL + pgvector                                                                                                                               |
| Indexing   | tree-sitter (AST parsing/chunking), Voyage AI (`voyage-code-3`)                                                                                     |
| Jobs       | arq + Redis                                                                                                                                         |
| Real-time  | WebSockets + Redis pub/sub (one event bus, one channel per organization)                                                                            |
| AI         | Anthropic Claude or a free local Ollama model (Qwen/Llama/Gemma) for chat, Voyage AI (embeddings, reranking), LangGraph for retrieval orchestration |
| Graph viz  | `@xyflow/react` (React Flow) + `@dagrejs/dagre` for layout                                                                                          |
| Charting   | `recharts`                                                                                                                                          |
| Deployment | Vercel (web), Render/Railway (API + worker), Supabase (Postgres), Upstash (Redis) — see `docs/deployment/ci-cd.md`                                  |

## Repository layout

```
frontend/    Next.js frontend
backend/     FastAPI backend
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
