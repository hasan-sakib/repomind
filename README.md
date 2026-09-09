# RepoMind

AI codebase intelligence and developer onboarding platform. Connect a GitHub
repository and get answers, onboarding documentation, and architecture
insight grounded in the actual code — not a generic AI chat wrapper.

## Status

Authentication, multi-tenancy, GitHub integration, codebase indexing, the
AI/RAG chat engine, the architecture/dependency explorer, and AI pull
request intelligence are complete and tested: email/password auth, GitHub
OAuth login, organizations with role-based authorization
(owner/admin/developer/viewer), password reset, email verification, a
GitHub App connection flow, a repository overview (metadata, branches,
commits, pull requests, issues, secure idempotent webhook sync), a full
indexing pipeline (shallow git clone, `.gitignore`-aware file discovery,
tree-sitter AST parsing and chunking for Python/JavaScript/TypeScript/Go,
Voyage AI embeddings, pgvector storage, an `arq`/Redis background job
queue, and a live indexing-progress screen), a code-aware chat engine —
hybrid retrieval (pgvector + an import-based dependency graph + git
history), query-intent routing via a small LangGraph pipeline, Voyage
reranking, streamed responses with real file/line source citations, and
a three-pane chat interface (conversation history, streaming markdown
with syntax highlighting and clickable citations, source panel) — an
architecture explorer (package- and module-level dependency graphs
derived from the same indexed data, pan/zoom/search/filter, a
click-to-inspect detail panel with symbols/dependencies/dependents/recent
commits, and progressive package → module expansion) — and AI pull
request intelligence (risk-level analysis grounded in real changed
files/symbols/dependents/existing tests, cached per commit, with a
structured PR risk report UI) — all backed by a real database and 158
passing backend tests. See
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
for the architecture explorer, and
[`docs/architecture/0007-ai-pull-request-intelligence.md`](docs/architecture/0007-ai-pull-request-intelligence.md)
for PR intelligence.

## Stack

| Layer      | Choice                                                             |
| ---------- | ------------------------------------------------------------------- |
| Frontend   | Next.js (App Router), TypeScript, Tailwind CSS v4, shadcn/ui       |
| Backend    | FastAPI, Pydantic v2, SQLAlchemy (async), Alembic                 |
| Database   | PostgreSQL + pgvector                                              |
| Indexing   | tree-sitter (AST parsing/chunking), Voyage AI (`voyage-code-3`)   |
| Jobs       | arq + Redis                                                       |
| AI         | Anthropic Claude or a free local Ollama model (Qwen/Llama/Gemma) for chat, Voyage AI (embeddings, reranking), LangGraph for retrieval orchestration |
| Graph viz  | `@xyflow/react` (React Flow) + `@dagrejs/dagre` for layout        |
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
