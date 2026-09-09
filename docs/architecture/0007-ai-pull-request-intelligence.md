# ADR 0007: AI Pull Request Intelligence

**Status:** Accepted — implemented
**Date:** 2026-09-09

## What was built

- `app/pr_analysis/` — the deterministic, non-LLM analysis pipeline:
  - `diff_parser.py` — parses GitHub's unified-diff `patch` text into the
    set of added line numbers, in the new file's own line numbering.
  - `context.py` — resolves each of a PR's changed files against our
    already-indexed `CodeFile`/`CodeSymbol` rows (ADR 0004), finds which
    symbols the diff actually touches, which other files depend on those
    symbols (reusing `app/retrieval/dependency_graph.py` from ADR 0005),
    and which existing test files already reference them.
  - `prompt.py` / `result_schema.py` — builds the LLM prompt from that
    context and validates the LLM's structured JSON response, including
    dropping any file citation the model wasn't actually shown.
- `PullRequestAnalysis` (new table) — one row per analysis run, at a
  specific `head_sha`. This table *is* the cache (see below), not a layer
  in front of one.
- `head_sha` added to `PullRequest` (backfilled via `server_default=""`),
  populated from GitHub's PR payload on sync and on the `pull_request`
  webhook — the cache-invalidation signal for a new commit pushed to a PR.
- `GET /repositories/{id}/pull-requests/{number}`,
  `GET .../{number}/analysis`, `POST .../{number}/analysis` (trigger,
  enqueues the `analyze_pull_request` arq job) — mirrors the indexing
  job's trigger/poll pattern from ADR 0004 exactly.
- Frontend: `/repositories/{id}/pull-requests` (list, state-filterable)
  and `/repositories/{id}/pull-requests/{number}` (analysis view) — a
  structured risk/impact report, not a chat-style answer card.

## Decisions and why

### The context gathered for the LLM is entirely deterministic — the model never sees raw GitHub data unfiltered

`context.build_context` does all the real analytical work in plain code:
classifying each changed file's kind (`app/architecture/classifier.py`,
ADR 0006), finding which indexed symbols overlap the diff's added lines
(`diff_parser.parse_patch_added_lines`), finding dependents via the same
import-matching approach as the RAG dependency graph, and finding related
existing test files by scanning for import statements referencing the
changed symbols in files under a test-path convention
(`test_`/`_test.`/`.test.`/`.spec.`/`tests/`/`test/`). The LLM's job is
narrower than it looks: turn this already-gathered, already-grounded
structured context into a summary, a risk judgment, and a
plain-English write-up — not to independently discover what changed.

### Citations are validated server-side, not just requested in the prompt

"The analysis must cite actual repository files" is enforced twice: the
prompt enumerates every path the model is allowed to reference (the
changed files and the related test files) and instructs it to never cite
anything else, and `result_schema.validate_citations` then drops any
citation that isn't in that exact set before the result is ever persisted
— an `affected_components` entry that loses every one of its file paths
this way is dropped entirely, since an "affected component" backed by zero
real files isn't a citation, it's a guess. This mirrors ADR 0005's
"source reference is a database fact, not a hope that the model followed
instructions" design for chat citations.

### `PullRequestAnalysis` is the cache — analysis is keyed by `head_sha`, not re-run on every view

Triggering analysis (`pr_analysis_service.trigger_analysis`) checks the
latest analysis row for the PR: if one is already queued or running, that
row is returned instead of enqueueing a duplicate; if the latest succeeded
row's `head_sha` matches the PR's *current* `head_sha`, it's returned as-is
— no LLM call. Only a genuinely new commit (which moves `head_sha`, kept
in sync both by periodic GitHub sync and by the `pull_request` webhook)
or an explicit `force=true` triggers a fresh run. Like `AiRun` (ADR 0005),
a re-analysis creates a *new* row rather than overwriting the last one, so
history stays inspectable — but unlike chat, most calls are expected to
hit the cache, since a PR's diff doesn't change between page views.

### Generation runs on the arq job queue, not inline or as a background asyncio task

Chat (ADR 0005) runs its LLM call as a decoupled `asyncio.Task` specifically
because it needs to *stream* tokens back over an open HTTP connection.
Nothing here streams — the whole point is one finished, structured report
— so this reuses the existing arq worker (already running for indexing
and GitHub sync) instead of inventing a second concurrency pattern. The
route creates a `QUEUED` row and enqueues `analyze_pull_request`
(`app/workers/tasks.py`); the task loads the row, marks it `RUNNING`, does
the work, and — critically — a top-level `try/except` marks it `FAILED`
with the real error message on *any* exception, so a row can never be
stuck at `RUNNING` forever the way ADR 0005's disconnected-chat-client bug
demonstrated is easy to introduce by accident in async worker code.

### One retry on invalid JSON, then a real failure — never a silently blank result

`_complete_analysis` asks the model for a single JSON object matching an
exact shape. If parsing or schema validation fails, it retries exactly
once with the model's own bad output plus a stricter reminder appended to
the conversation; if that also fails, the analysis is marked `FAILED` with
the parse error as its message. There is no third attempt and no
"best-effort" partial result — a PR that can't be analyzed shows a clear
failure state with a retry button, not a report quietly missing sections.

### The PR's own diff patches are truncated per-file, not per-analysis

Each changed file's patch is capped at `pr_analysis_max_patch_chars_per_file`
(default 2,000 chars) before being included in the prompt — bounding a
single enormous file's diff without starving every *other* file in the
same PR of context, the same per-item-then-aggregate bounding
`app/retrieval/prompt.py`'s `build_context_block` uses for RAG chunks
(ADR 0005) and `indexing_max_chunk_lines` uses for chunking (ADR 0004).

### GitHub's PR-files endpoint is fetched fresh at analysis time, not stored

`list_pull_request_files` (a new REST client call) is only ever called
from inside the `analyze_pull_request` task — the diff itself is never
persisted independent of an analysis; `PullRequestAnalysis.files_analyzed`
snapshots each file's path/status/additions/deletions at the moment of
that specific analysis, which is enough for the UI to show "N files
changed, +X -Y" without a second live GitHub call on every page view.
Bounded to `MAX_PULL_REQUEST_FILES` (100) — the same
fetch-a-bounded-recent-window discipline as every other `rest_client.py`
call (ADR 0003).

## What this phase does not do

- No line-level diff rendering in the UI — the analysis cites files (and,
  for file-detail links, the analyzed commit's line ranges via existing
  symbol data), not a diff viewer. Files link out to GitHub's own blob
  view at the analyzed `head_sha`.
- No cross-PR comparison or trend view (e.g. "risk over time" for a
  repository) — one PR's analysis at a time, matching the brief.
- The PR's free-text description (`body`) is not fetched or given to the
  model — the diff and changed symbols carry enough signal for the
  summary and risk judgment this phase asks for, and skipping it avoids
  an extra GitHub call and prompt-size cost for a field the brief's own
  example output never references.
