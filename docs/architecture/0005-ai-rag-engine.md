# ADR 0005: Code-Aware AI/RAG Engine

**Status:** Accepted — implemented (backend and frontend)
**Date:** 2026-09-08
**Supersedes (in part):** the retrieval/chat sections of
`docs/architecture/ai-architecture.md` (section 2 onward — "2. Retrieval
pipeline", the chat streaming design) and the `conversations`/`messages`
schema sketch in `docs/database/database-design.md`. Those were written
in Phase 1 as a plan; this ADR is the source of truth for what was
actually built. Section 1 of `ai-architecture.md` (the `AIProvider`/
`EmbeddingProvider` abstraction pattern and the Voyage reasoning) held up
unchanged and is not superseded.

## What was built

- A hybrid retrieval pipeline (`app/retrieval/`) combining pgvector
  cosine search, an import-based dependency graph, and commit-message
  git-history search, merged and reranked into the context sent to the
  LLM.
- Query-intent-based routing (`app/retrieval/intent.py`,
  `app/retrieval/graph.py`) — a small LangGraph `StateGraph` that routes
  to a different retrieval strategy depending on what kind of question
  was asked.
- A `Reranker` provider abstraction (`app/ai/reranker.py`) implemented
  with Voyage's rerank endpoint, mirroring the existing `AIProvider`/
  `EmbeddingProvider` pattern.
- Streaming chat over Server-Sent Events (`app/api/v1/routes/chat.py`,
  `app/services/chat_service.py`), with sources delivered as soon as
  retrieval finishes — before generation even starts.
- Four new tables: `conversations`, `messages`, `ai_runs`,
  `retrieval_results`.
- Frontend: a three-pane code intelligence interface — conversation
  navigation, streaming markdown conversation with inline citations,
  and a source panel — deliberately not styled like a generic chat
  product.
- A second `AIProvider` implementation, `OllamaProvider`
  (`app/ai/providers/ollama_provider.py`), for free local chat
  generation — no API key, no per-token cost — added after initial
  delivery once cost became a concrete concern; see "Ollama as a free
  AIProvider" below.
- A fix for a real bug the above surfaced: a chat turn that outlived the
  client (a slow local model plus a closed tab, a navigation, or a
  dropped connection) left its `AiRun` stuck at `running` forever with
  no assistant message ever recorded; see "Chat turns survive a
  disconnected client" below.

## Decisions and why

### LangGraph: used for the one place it earns its keep

The brief was explicit: use LangGraph only where it genuinely improves
orchestration, not to say it was used. The retrieval pipeline has exactly
one real branch point — after intent detection, four meaningfully
different retrieval strategies apply (dependency-graph lookup, git-history
search, a symbol-definition-boosted vector search, or plain vector
search). `app/retrieval/graph.py`'s `StateGraph` makes that routing
declarative (`add_conditional_edges` keyed on `QueryIntent`) and each
node (`analyze`, `detect_intent`, `embed_query`, four retrieval
strategies, `rank`) independently testable, instead of a nested
if/elif inside one long function.

**What LangGraph is deliberately *not* used for:** the final LLM
generation call. Streaming tokens to the client over SSE happens
*outside* the compiled graph, via `AIProvider.stream()` directly in
`app/services/chat_service.py`. Once ranking finishes there is nothing
left to branch on — generation is a single linear step — and routing
token-level streaming through LangGraph's own streaming machinery would
add real integration complexity (translating its stream events into SSE
frames) for a step that has no conditional structure to justify a graph
node. The graph's job ends at `rank`; `_run_turn` in `chat_service.py`
takes the ranked context from there.

The graph is built fresh per query (`build_graph(db, embedding_provider,
reranker, settings)`) rather than once at startup — its nodes close over
the request-scoped `AsyncSession` and provider instances. Compiling a
handful of nodes/edges per call is not meaningfully expensive next to a
network round trip to an embedding/reranking/LLM API, and it avoids
fighting LangGraph's `context_schema`/runtime-injection machinery for
dependency injection that a plain closure already solves cleanly.

### Rule-based intent detection, not an LLM call

`app/retrieval/intent.py` classifies a query into `EXPLAIN` / `LOCATE` /
`DEPENDENCY` / `HISTORY` / `GENERAL` with keyword/regex patterns, not a
model call. A 4-way classification doesn't need a language model, and
adding one would put a full LLM round trip — real latency, real cost —
in front of *every* query just to decide how to retrieve context for it.
The module is deliberately small and swappable (two functions,
`detect_intent`/`extract_symbol_name`) so replacing it with an
LLM-based classifier later is a contained change, not a rewrite of
`app/retrieval/graph.py`.

`extract_symbol_name` is a companion heuristic — the longest
PascalCase-looking token in the query — used to feed the dependency
graph and the locate-intent definition lookup. It is best-effort by
design: a query with no PascalCase identifier (e.g. "how does refresh
token rotation work") returns `None`, and callers fall back to vector
search rather than guessing.

### The dependency graph is import-based, not a real resolver

"Which services depend on UserService?" is answered by
`app/retrieval/dependency_graph.py` scanning every file's recorded
import statements (from `app/indexing/chunker.py`, extended in this
phase to capture the **line number** each import appears on — see
below) for a word-boundary match on the symbol's name. This is
precise for the common case and honestly limited: a file that
references a symbol via `from x import *`, a dynamically-resolved
import, or without importing it by that exact name at all (e.g. a
re-exported alias) won't be found. A real per-language import resolver
or call graph is meaningfully more engineering than this phase's scope
justifies — the import-line-scan approach directly answers the
architecture's example question with real file/line citations, which is
the bar this phase needs to clear. Revisit if usage shows the recall gap
matters in practice.

**`CodeFile.imports` gained line numbers in this phase.** It was
`list[str]` (raw import statement text) in Phase 4; a dependency
citation needs a real line number to be clickable, so
`app/indexing/chunker.py`'s `ExtractedImport` now carries `(text, line)`
and `CodeFile.imports` is `list[ImportRecord]` (a `TypedDict`, still a
plain JSONB column — no migration needed for the shape change, since
JSONB doesn't encode a schema). Existing indexed data written before
this change simply gets the new shape on the next re-index; there is no
production data to migrate.

### Git history: keyword search over synced commit messages, not file-level history

Same honest-scope pattern as the dependency graph.
`app/retrieval/git_history.py` keyword-matches the query against
`Commit.message` (already synced, bounded, per ADR 0003) and returns
recent matches as commit citations. It cannot answer "which commits
touched file X" — commits are synced without a per-commit changed-file
list, and fetching that from GitHub per commit was explicitly out of
scope for ADR 0003's bounded sync. A git-history-sourced
`RetrievedChunk` has `file_path=None` and a `commit_sha` instead — it
cites a commit, not a code location, and the frontend renders it
differently (a commit reference, not a file+line reference).

### Context Ranking: a real reranker, reusing the Voyage integration

`app/ai/reranker.py` is a new provider abstraction (mirroring
`AIProvider`/`EmbeddingProvider`), implemented with Voyage's
`rerank()` endpoint (`rerank-2.5`, confirmed against the installed
`voyageai` SDK before use — same discipline as every other library API
in this codebase). Candidates from all three retrieval sources are
pooled, deduped (`app/retrieval/ranking.py`), and reranked together
against the actual query text — pgvector's cosine distance and "this
file imports X" aren't comparable scores, so blending sources without a
real relevance pass would rank essentially arbitrarily. **A ranking
failure degrades, it doesn't break the query:** if the rerank call
raises, `ranking.rank()` catches it, logs, and falls back to the
candidates' original discovery order truncated to `top_k` — a chat
answer with slightly worse context ordering beats a chat answer that
fails outright because a secondary service hiccupped.

### Source references are a database fact, not a parsed model citation

The `[N]` markers the system prompt (`app/retrieval/prompt.py`) asks the
model to use are cosmetic — they let the frontend highlight which
retrieved source the model's answer leaned on. **They are never the
source of a citation's file path or line numbers.** Every ranked chunk
is persisted as a `RetrievalResult` row *before* generation starts (so
sources are available to stream to the client immediately, without
waiting for the LLM), and the API's `sources` list is always built from
those rows. This was a deliberate rejection of the alternative design
(parse `[N]` markers out of the streamed text and look up what they
refer to) — that approach makes a citation's correctness depend on the
model not hallucinating a marker or getting one out of range, for a
result (file path + line numbers) that must be exactly right to be
useful at all.

**`RetrievalResult` snapshots file_path/start_line/end_line/symbol_name
rather than only storing a `chunk_id` foreign key.** A later re-index
deletes and recreates `CodeChunk` rows wholesale (ADR 0004's incremental
pipeline), which would silently invalidate every past conversation's
citations if this table only held a live reference. `chunk_id` is kept
(nullable, `ON DELETE SET NULL`) for a best-effort "jump to the current
version" link, but the snapshot columns are what the UI actually
renders — a citation from three re-indexes ago still shows the line
range it was accurate for at the time.

### `AiRun`/`Message` shape: regenerate creates a new run, not an overwrite

`AiRun.user_message_id` + `AiRun.assistant_message_id` (nullable until
the answer is persisted) let "regenerate" create an entirely new
`AiRun` row pointing at the *same* user message with a *new* assistant
message, rather than mutating the original run or message. Both
attempts, and both attempts' `retrieval_results`, stay queryable — this
was a deliberate choice for observability (comparing what changed
between a regeneration and the original) over the simpler "just
overwrite the last answer" design, at the cost of a slightly wider join
to render a conversation (`app/services/chat_service.py::
get_conversation_messages` batch-fetches the `AiRun` for each assistant
message rather than following a single FK backward).

### Token usage on `AiRun` is an approximation, not measured

`AIProvider.stream()` (unchanged from Phase 1) yields raw text with no
final usage total attached — the Anthropic SDK's streaming context
manager can expose one, but capturing it would mean changing the
existing streaming interface's contract for every caller, not just this
one. `AiRun.input_tokens`/`output_tokens` are `len(text) // 4`, the same
rough heuristic already used for `CodeChunk.token_count` (ADR 0004) —
good enough for the observability this field exists for, explicitly not
a billing figure. Revisit by extending `AIProvider.stream()` (or adding
a variant that yields a final usage event) if real usage tracking
becomes a requirement.

### `AIProvider` gained a `model` property

A small, direct addition: `chat_service.py` needs to record which model
produced an `AiRun` for observability, and reaching into
`AnthropicProvider`'s private `_model` attribute from outside the
abstraction would violate the same encapsulation the provider pattern
exists to enforce. `AIProvider.model` is now a required abstract
property; `AnthropicProvider.model` returns the existing `self._model`.

### Frontend: not a chatbot

The interface is a three-pane layout (conversation navigation left,
streaming conversation center, source/context panel right) rather than
a centered single-column chat thread — explicitly to read as a
developer tool inspecting a specific codebase, not a general-purpose
assistant. Left and right panes are fixed-width (`w-56`/`w-72`) and
collapse entirely below `md`/`lg` breakpoints rather than being
draggable-resizable — no resizable-panel library is installed, and
adding one just for this would be scope beyond what the brief asked
for; the center conversation pane is what has to work on a phone,
sources/history are a desktop-tier affordance. `app/(dashboard)/
repositories/[repositoryId]/chat/` has two routes — `chat/page.tsx`
(no conversation yet) and `chat/[conversationId]/page.tsx` — sharing
one `<ChatShell>` component, matching the existing project convention
of pages owning their own header rather than a shared `layout.tsx`
(see ADR 0004's indexing screen).

**SSE is hand-rolled, not `EventSource`.** The browser's built-in
`EventSource` only supports GET requests with no body and no custom
headers — this endpoint is a POST carrying the query JSON and the
app's CSRF header (`X-Requested-With`, checked by `require_csrf_header`
on the backend). `lib/sse.ts` does a plain `fetch()` and reads
`response.body.getReader()` itself, parsing `event:`/`data:` frames on
`\n\n` boundaries. This is also why it doesn't reuse `apiFetch` (`lib/
api-client.ts`) — that helper always awaits `response.json()`, which
would buffer the entire stream before returning anything.

**Citation markers are markdown links in disguise, not a custom remark
plugin.** `[N]` in the model's raw text is rewritten to
`[N](citation:N)` before handing the string to `react-markdown`, and a
custom `a` component intercepts any `href` starting with `citation:`
to render a small clickable badge instead of a real link — clicking it
focuses that source in the right panel and scrolls it into view. This
reuses react-markdown's own link parsing instead of writing a remark
AST transform, at the cost of a known, accepted edge case: the
replacement regex runs over the raw string before parsing, so a
literal `[1]`-shaped substring inside a fenced code block can also get
linkified. Harmless when it happens (a stray clickable badge inside a
code sample), not worth a markdown-aware pass to prevent.

**Source links resolve differently per source type.** A vector/
dependency citation has no commit pinned to it in the API response
(`RetrievalResult` snapshots line numbers, not a commit SHA — see
above), so the frontend links to `{repository.html_url}/blob/
{repository.default_branch}/{path}#L{start}-L{end}` — the file at the
current default-branch HEAD, not the exact indexed commit. This is an
accepted approximation: a re-index between the citation being created
and the user clicking it could shift the cited lines slightly. A
git-history citation links to the commit's own `html_url` (looked up
server-side from `Commit.html_url` — see `commit_url` on
`SourceReferencePublic`), which has no such drift since a commit is
immutable.

**Syntax highlighting is deliberately not "rainbow."** `rehype-
highlight` (highlight.js) drives token classification, but the CSS in
`globals.css` colors only comments (muted) and strings (the app's one
`--brand` accent) — everything else stays the same monochrome
foreground as body text, keywords picking up weight instead of a
color. This matches the project's "monochrome palette + one restrained
accent" design system (`docs/architecture/design-system.md`) instead
of importing a stock highlight.js theme that would introduce five or
six colors nothing else in the app uses.

**The new-conversation URL only updates after the stream finishes, not
before.** `/chat` (no conversation yet) and `/chat/[conversationId]`
are different `page.tsx` files; navigating between them unmounts the
component tree. `handleAsk` in `chat-shell.tsx` creates the
`Conversation` row and starts streaming while still on `/chat`, and
only calls `router.replace` to the permanent URL once the stream's
`done`/`error` event has been handled — never mid-stream, which would
otherwise cut off an in-flight answer at the exact moment the route
changed.

Verified live in a browser (Playwright) against the real backend with
the AI providers swapped for fakes via `app.dependency_overrides` (no
real Anthropic/Voyage credentials in this environment) and real seeded
`CodeFile`/`CodeSymbol`/`CodeChunk` rows, so retrieval itself — not
just generation — was exercised for real: a dependency-intent question
("Which services depend on UserService?") correctly returned a
`Dependency` source citing the exact seeded import line, alongside
`Semantic match` vector sources; light mode, dark mode, and a mobile
viewport (conversation nav and source panel correctly collapse,
center pane remains fully usable); and a full reload at a conversation's
permanent URL correctly rehydrated the same messages, sources, and
intent label from the server.

### Ollama as a free AIProvider

Anthropic's API has no meaningful free tier — real usage costs real
money per token. Voyage AI's free tier (~200M tokens each for embeddings
and reranking) comfortably covers this project's scale, so embeddings
and reranking stayed on Voyage, but the chat model was worth making free
too: `app/ai/providers/ollama_provider.py` implements `AIProvider`
against a local `ollama serve` instance (default `qwen3:4b`, whatever's
already pulled) via the official `ollama` Python client. `AI_PROVIDER=
ollama` is now the `.env.example` default — `anthropic` is documented
as the paid, hosted alternative for whoever wants Opus-tier answer
quality instead.

Two things only showed up by actually running a local model, not by
reading its docs:

1. **Reasoning models stream empty `content` for a while.** `qwen3:4b`
   thinks before answering, and Ollama surfaces that thinking as
   `message.thinking`, separate from `message.content` — a streamed
   chunk's `content` is genuinely `""` for as long as the model is
   "thinking," not a bug in `OllamaProvider.stream()`. This happened to
   already work correctly on the frontend without any change: the
   assistant message starts as an empty string and `MessageItem` shows
   a "Thinking…" spinner for exactly as long as `content` stays empty —
   the UI built for a fast hosted model turned out to be exactly the
   right UI for a slow local one too.
2. **Disabling thinking (`think=False`) is not a free latency win.**
   Measured against this repository's actual system prompt + context
   shape: with thinking on, `qwen3:4b` took ~16s to the first visible
   token and produced a clean, well-formed answer. With `think=False`,
   the first token arrived almost instantly, but total wall-clock time
   was *longer* (the model narrated its reasoning into the visible
   answer instead — "We are given a specific context... Analysis:
   ..." — instead of thinking it silently), and the final answer was
   messier. `OllamaProvider` deliberately does not pass `think` at all,
   leaving each model's own default behavior in place, rather than
   assuming "no thinking" is faster or better — it measurably wasn't,
   for this model, on this prompt shape.

### Chat turns survive a disconnected client

Verifying the Ollama integration against a real local model — genuinely
tens of seconds per answer, unlike the sub-second fake providers every
earlier test in this ADR used — surfaced a real bug: closing the
browser tab (or navigating away, or a dropped connection) mid-generation
left the `AiRun` stuck at `running` forever, with no assistant message
ever recorded and no error surfaced anywhere. Every test written before
this point had used a chat provider fast enough, or a test harness that
fully awaited the response, that this failure mode never had a chance to
occur — it was real, just previously unreachable.

**Root cause:** `_run_turn` originally ran inline inside the same async
generator the HTTP route streamed from, using the *request's* database
session. When the client disconnects, Starlette stops iterating that
generator; the request's session is torn down once the request handler
returns, and neither of `_run_turn`'s own `except`/`mark_failed` blocks
ever runs, because the generator wasn't given the chance to reach them.

**Fix:** `app/services/chat_service.py::_stream_turn` spawns the actual
work — retrieval, generation, persistence — as an independent
`asyncio.Task`, using its own database session (`async_session_factory`,
the same pattern `sync_service` and the indexing pipeline already use
for exactly this reason: a session tied to the request cannot outlive
it) and relays events to whichever client is still listening through a
queue. If nobody is listening, the task still runs to completion and the
`AiRun` still reaches a consistent terminal state (`succeeded` or
`failed`) rather than being silently abandoned mid-flight at `running`.
A module-level set of tasks
(`_background_turns`) holds a strong reference to each spawned turn —
asyncio only keeps a *weak* reference to a created task, and without an
explicit strong reference the task can be garbage-collected mid-run the
moment nothing else holds it, which is exactly the situation a
disconnected client creates.

Regression-tested in `tests/integration/test_chat_service.py::
test_ask_completes_in_the_background_after_the_client_disconnects` —
abandons the stream immediately after the sources event (before any
answer text has streamed), then asserts, from a **fresh** database
session, that the assistant message and a `succeeded` `AiRun` show up
anyway.

## Testing

Backend suite grew from 79 to 100 tests. New coverage:

- **Intent classification** (`tests/unit/test_retrieval_intent.py`):
  every one of the brief's example questions, plus symbol-name
  extraction edge cases (no PascalCase token, leading question words).
- **Dependency graph** (`tests/integration/test_retrieval_dependency_graph.py`):
  definition lookup preferring a class over a same-named method,
  unknown-symbol handling, import-based dependents matching, and the
  word-boundary check that stops `UserServiceV2` from matching a
  `UserService` query.
- **Chat service** (`tests/integration/test_chat_service.py`): a full
  ask() run against a fake embedding provider/reranker/chat provider and
  real seeded `CodeFile`/`CodeChunk`/`CodeEmbedding` rows — asserting
  the streamed sources event cites the right file/line, the streamed
  tokens match the fake provider's output, both messages and the
  `AiRun` persist correctly with the right intent; a regenerate test
  confirming two independent `AiRun` rows for one question; a failure
  test confirming a retrieval error surfaces as an `ErrorEvent` and
  marks the run failed without leaving an orphaned assistant message;
  and a feedback-persistence test.
- **Chat routes over real HTTP** (`tests/integration/test_chat_routes.py`):
  the full connect-repository-then-ask flow through `ASGITransport`
  with the AI providers swapped for fakes via `app.dependency_overrides`
  — verifying actual SSE framing (`event: sources` / `event: token` /
  `event: done` lines appear in the real streamed response body), CSRF
  enforcement on the ask endpoint, and the feedback endpoint end to end.

Frontend: no automated tests (same gap noted in every prior ADR) —
verified live via Playwright, see the frontend section above for what
was exercised.
