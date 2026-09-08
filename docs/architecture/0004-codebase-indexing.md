# ADR 0004: Codebase Indexing Pipeline

**Status:** Accepted — implemented
**Date:** 2026-09-08
**Supersedes (in part):** the AI-ingestion sketch in
`docs/architecture/ai-architecture.md`, the `code_chunks`/`IngestionJob`
schema in `docs/database/database-design.md`, and the ingestion-related
routes in `docs/api/api-design.md`. Those docs were written in Phase 1
before any of this existed and describe a plan, not the system; this ADR
is the source of truth for the indexing pipeline actually built. Notably,
this phase does **not** build retrieval/search (pgvector cosine-search
chat context) — only ingestion. That stays future work.

## What was built

- A six-stage indexing pipeline (`app/indexing/`, orchestrated by
  `app/indexing/pipeline.py`): clone → discover → filter → parse → chunk
  → embed → store, matching the stage sequence in `IndexingStage`.
- `app/integrations/git/fetcher.py` — shallow git clone via an
  installation-token-embedded URL, fetch-by-commit-SHA, temp-directory
  cleanup guaranteed via `finally`.
- `app/indexing/discovery.py` — `.gitignore`-aware file discovery
  (`pathspec`) plus a hardcoded directory denylist, binary detection, and
  a size cap.
- `app/indexing/parser.py` + `app/indexing/chunker.py` — tree-sitter
  parsing (Python, JavaScript, TypeScript, TSX, Go) and AST-boundary
  chunking; a heading/paragraph-aware prose fallback for every other
  recognized text file (Markdown, JSON, YAML, plain text, ...).
- `app/ai/embedding_provider.py` + `app/ai/providers/voyage_provider.py`
  — an `EmbeddingProvider` abstraction mirroring `AIProvider`
  (`app/ai/provider.py`), implemented with Voyage AI's `voyage-code-3`.
- Six new tables: `code_files`, `code_symbols`, `code_chunks`,
  `code_embeddings`, `indexing_jobs`, `indexing_errors`, plus the
  `pgvector` extension and an HNSW index on `code_embeddings.embedding`
  (both hand-written in the Alembic migration — autogenerate doesn't see
  either).
- `arq` + Redis background job queue (`app/workers/`), replacing Phase
  3's FastAPI `BackgroundTasks` for GitHub sync too — see below.
- Frontend: a repository indexing screen showing live stage/progress via
  polling, and a "Start indexing" action from the repository overview.

## Decisions and why

### Six new tables, not one `code_chunks` table with an inline embedding column

The Phase 1 sketch put `embedding vector(N)` directly on `code_chunks`.
This phase splits `CodeChunk` (the unit of retrieval — content, line
range, token count) from `CodeEmbedding` (one vector row per chunk, with
its own `model` column) for two reasons: the HNSW index only ever needs
to cover rows that actually have a vector (re-embedding after a model
change becomes a row replacement, not a schema migration), and a chunk
can legitimately exist without an embedding yet (e.g. embedding failed
for that batch — see "Partial success" below) without a nullable vector
column muddying the schema. `CodeSymbol` is likewise its own table, not a
`symbol_name` column on `CodeChunk` — a class has one symbol row and
(often) several method symbol rows and chunk rows, and the
`parent_symbol_id` self-reference (method → enclosing class) has nowhere
sensible to live on a flat chunk row.

### AST-boundary chunking, never raw character splitting

`app/indexing/chunker.py` walks the tree-sitter parse tree and creates
one chunk per function/method/interface/type declaration — never a
fixed-size character or token window. A class with nested methods gets a
small **header-only** chunk (docstring + class-level statements before
the first nested symbol), not a chunk containing the full class body —
the methods already have their own chunks, and duplicating their content
into the class chunk would double-count everything in embedding search
later. Docstrings are extracted per language: Python's actual docstring
convention (first string-expression statement in the body) for Python,
and the leading `comment` sibling node (JSDoc/line comments) for
JavaScript/TypeScript/Go — found via index lookup in the parent's
children list, since tree-sitter's `prev_sibling` skips over comment
nodes (they're "extra" nodes, excluded from the normal sibling chain).

Files with no tree-sitter grammar (Markdown, JSON, YAML, plain text, ...)
still get indexed, via a structural prose fallback: Markdown splits on
heading boundaries, everything else on blank-line paragraph boundaries;
a line-count cap (`indexing_max_chunk_lines`, default 200) only decides
where an oversized section splits *between* whole lines, never mid-line.
A source file that parses but yields zero symbols (e.g. a script that's
all top-level statements) falls back to the same prose chunker rather
than being silently unindexed.

Oversized individual symbol chunks (a 500-line function) are deliberately
**not** split further — cutting a function body at an arbitrary line
would violate the same "don't blindly split code" principle chunking
exists to satisfy, and Voyage's `embed()` call is used with its default
truncation behavior as the safety valve for the rare outlier.

`token_count` is `len(content) // 4` — a standard rough heuristic, not a
real tokenizer call, since no tokenizer for `voyage-code-3` is exposed
for local use. It sizes chunks sensibly; it is not used for billing.

### Content-hash incremental re-indexing, not a diff against git

Re-indexing (manual "index now", or a webhook-triggered push) reprocesses
every file GitHub thinks might have changed, but *skips* re-parsing/
re-chunking/re-embedding a file whose SHA-256 content hash is unchanged
from what's already stored on its `CodeFile` row. This is simpler and
more robust than diffing against git's own changed-file list (which
would need the previous commit's tree, not just the new one, and
wouldn't help re-index-after-a-parser-bugfix scenarios anyway) at the
cost of hashing every discovered file's bytes — cheap relative to
parsing/chunking/embedding. Files that exist in the DB but were no
longer discovered (deleted or renamed) are removed via
`code_file_repository.delete_missing`, cascading to their symbols/
chunks/embeddings.

**Real bug caught by tests, not designed around upfront:** the first
version of the per-file loop only wrote `files_skipped` onto the
`IndexingJob` row inside the "file was processed" branch, at the bottom
of the loop — a file that hit the *skip* branch and `continue`d never
reached that write, so a re-index of an unchanged repository reported
`files_skipped: 0` even though the skip logic itself ran correctly. Fixed
by committing progress on the skip path too. Caught by
`test_run_indexing_job_skips_unchanged_files_on_rerun`
(`tests/integration/test_indexing_pipeline.py`), not by inspection.

### Progress committed incrementally, not once at the end

Every stage transition and every processed/skipped file commits the
`IndexingJob` row's progress fields immediately
(`app/indexing/pipeline.py`), rather than accumulating in memory and
writing once at the end. A client polling the job status endpoint sees
genuine incremental progress — files discovered, then processed one by
one, then embeddings generated batch by batch — never a job that jumps
straight from `queued` to `succeeded`. This does mean many small commits
over a large repository (up to `indexing_max_files_per_repository`,
default 3000); acceptable at this project's target scale, and a
deliberate trade against a production-scale system indexing millions of
files, where batched progress writes would be the right call instead.

### `arq` + Redis, and sync moves onto it too

ADR 0003 deferred `arq`/Redis for GitHub sync because sync is a few
seconds of REST calls with no need for a durable queue, but flagged that
"at that point sync should move onto the same queue rather than staying
a special case" once something *did* need arq. Indexing — cloning,
parsing, embedding, potentially minutes per repository — is that
something, so this phase stands up arq/Redis for indexing and migrates
`sync_service` onto the same queue (`app/workers/tasks.py`), removing
`BackgroundTasks` from `app/api/v1/routes/repositories.py` and
`app/api/v1/routes/webhooks.py` entirely. This closes the real limitation
ADR 0003 named explicitly: a `BackgroundTasks` job is lost on process
restart with no retry; an arq job survives in Redis and is picked up by
any live worker.

**One indexing task, not one per trigger source.** The obvious API shape
("index repository", "re-index changed files", "process webhook
updates", "generate embeddings" as four background jobs) would duplicate
the same pipeline call four ways for no behavioral difference: the
content-hash skip already makes "re-index" and "process webhook update"
identical to "index repository" in what work actually happens, and
embedding generation is inherently a stage inside that one run, not a
freestanding job (there's nothing to embed without the parse/chunk step
that precedes it in the same job). `app/workers/tasks.py::index_repository`
is a single arq task; `IndexingTrigger` (`initial` / `manual` / `webhook`)
records *why* a job ran as data on the row, not as a code branch.

**Duplicate-job prevention is a database check, not an arq job-id
dedup.** `indexing_service.trigger_indexing` queries for an existing
`queued`/`running` `IndexingJob` for the repository before creating a
new one, returning the existing job (`started: false`) instead. This
needs to behave identically whether the trigger came from the API
(user clicks "index now") or a webhook (push to default branch) — an
arq-level `_job_id` dedup would only catch the arq-task layer, not the
"a human already clicked the button and the job hasn't been enqueued
yet" window, and a single DB-backed check covers both call sites with no
duplicated logic.

### GitHub webhook push → reindex, reusing ADR 0003's push handler

`webhook_service._handle_push` already resolved "does this push touch
the default branch" for the metadata resync ADR 0003 built.
`WebhookResult` gained a `reindex: tuple[repository_id, commit_sha] |
None` field so the same push event that triggers a resync also triggers
an indexing job at the exact pushed commit (`payload["after"]`), without
a second webhook-payload-parsing code path. A branch-deletion push
(`payload["deleted"]` true, or no `after`) is explicitly skipped — there
is no commit to sync or index — which ADR 0003's resync path had not
guarded against either; fixed here since the same payload shape now
feeds two consumers instead of one.

### Partial success is a real job status, not swallowed

`IndexingJobStatus` includes `partial`, distinct from `succeeded` and
`failed`: a job where every file was discovered and most indexed
successfully, but one file's tree-sitter parse threw or one embedding
batch call failed, still completes and is queryable — the failure is
recorded as an `IndexingError` row (`file_path`, `stage`, `message`) and
surfaced on the job, not swallowed and not treated as fatal for the
whole repository. Only an error that prevents the pipeline from running
at all (clone failure, the repository no longer existing) produces
`failed`.

### Embedding provider: Voyage, `voyage-code-3`, dimension 1024

Unchanged from the reasoning already recorded in
`docs/architecture/ai-architecture.md` (Anthropic has no first-party
embeddings API; Voyage is Anthropic's recommended partner;
`voyage-code-3` is tuned for source code, not general prose) — this
phase just implements it. `voyage-code-3` supports Matryoshka output
truncation (256/512/1024/2048 dimensions);
`Settings.embedding_dimension = 1024` balances retrieval quality against
HNSW index size/build time and is threaded through both the
`VoyageEmbeddingProvider`'s `output_dimension` parameter and the
hand-written `Vector(1024)` column / HNSW index in the migration — those
three have to agree, and there is no runtime check that they do, since
changing any of them requires a migration plus a full re-embed regardless.

### `pgvector/pgvector:pg16`, `docker-compose.yml`

The dev/test Postgres image changed from plain `postgres:16` to
`pgvector/pgvector:pg16` (`postgres:16` + the extension pre-installed) —
confirmed via `docker exec ... psql -c "SELECT * FROM
pg_available_extensions"` before relying on it. Existing dev data
survived the image swap (bind-mounted volume, same Postgres major
version). The test database (`repomind_test`) doesn't run Alembic
migrations at all — `tests/conftest.py` uses
`Base.metadata.create_all`/`drop_all` — so `CREATE EXTENSION vector` was
applied there directly, once, outside the migration; `create_all` does
not create the HNSW index either (that's hand-written raw SQL in the
migration, not part of the SQLAlchemy `Vector` type's DDL), so the test
suite runs without an ANN index — fine, since no test needs approximate
nearest-neighbor performance, only correct row insertion.

## Testing

Backend suite grew from 61 to 79 tests. New coverage:

- **File discovery/filtering** (`tests/unit/test_indexing_discovery.py`):
  denylisted directories, `.gitignore` patterns, binary detection, size
  cap, empty-file exclusion, the `max_files` cap, and extension-based
  language detection.
- **Parsing/chunking** (`tests/unit/test_indexing_chunker.py`): AST
  symbol/chunk boundaries and parent-child nesting for Python and
  JavaScript, docstring extraction (Python native + JSDoc), stable
  content hashing, the "never split a symbol by character offset"
  property, and the Markdown/plain-text prose fallback (including that
  it never splits a chunk mid-line).
- **Indexing pipeline + duplicate prevention**
  (`tests/integration/test_indexing_pipeline.py`): a full clone → parse →
  chunk → embed → store run against a fake `EmbeddingProvider` and a
  monkeypatched `clone_repository` (no real GitHub/Voyage calls), a
  content-hash-based re-index that skips unchanged files with no
  duplicate `CodeFile` rows, and the job-level duplicate-active-job
  guard in `indexing_service.trigger_indexing`.

**Existing test regression from the arq migration, and how it was
handled:** every test that previously relied on `BackgroundTasks`
running synchronously under `httpx.ASGITransport` (`test_repository_
connect.py`, `test_webhooks.py`) broke when sync/indexing moved onto a
real queue with no worker process running in tests. Fixed with a
`FakeArqPool` test double (`tests/conftest.py`) whose `enqueue_job` runs
the named task function inline instead of pushing to Redis — preserving
the existing tests' "the background work already happened by the time
the request returns" assumption without needing a live Redis + worker in
CI. The `client` fixture now overrides `get_arq_pool` with a
per-test `FakeArqPool` instance so tests can also assert on what was (or
wasn't) enqueued.

Frontend: verified via Playwright against the running app (Voyage/GitHub
credentials aren't available in this environment, so an indexing job was
driven against a directly-seeded repository rather than a live
clone/embed round trip) — indexing screen states (idle, running with
live stage/progress, succeeded, partial with errors listed), and that
progress numbers genuinely change across polls rather than jumping
straight to "done."
