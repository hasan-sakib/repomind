# ADR 0006: Architecture and Dependency Visualization

**Status:** Accepted — implemented
**Date:** 2026-09-09

## What was built

- `app/architecture/` — the graph-generation algorithm, computed entirely
  at query time from data the indexing pipeline (ADR 0004) and the import
  line-number extraction (ADR 0005) already store. **No new database
  tables.**
  - `classifier.py` — `classify_path(path) -> NodeKind` (route / service /
    repository / model / schema / other), a path-segment heuristic.
  - `graph_builder.py` — `build_package_graph`, `build_module_graph`,
    `get_file_detail`, `search_nodes`.
- `GET /repositories/{id}/architecture/graph` (optional `?package=` query
  param switches between the two aggregation levels below), `GET
  .../files/{file_id}`, `GET .../files/{file_id}/recent-changes`, `GET
  .../search?q=`.
- Frontend: `@xyflow/react` + `@dagrejs/dagre` dependency graph at
  `/architecture` (repository picker) and
  `/repositories/{id}/architecture` (the explorer) — pan/zoom/minimap,
  click-to-inspect detail panel, kind filters, search-to-jump, and
  progressive package → module expansion.

## Decisions and why

### The graph is computed at query time, not pre-stored

Every prior indexing run already records each file's `imports` (with line
numbers, ADR 0005) and each file's `CodeSymbol` rows. That is a complete
enough source of truth to derive the whole dependency graph on demand —
adding a `dependency_edges` table would mean keeping a second
representation in sync with `code_files`/`code_symbols` on every
re-index, for a computation that is O(files + imports + symbols) and
finishes fast enough to run per-request. Recomputing also means the
graph is never stale relative to the last index: there is nothing to
invalidate.

### Path-based classification is an explicit heuristic, not decorator/AST introspection

`classify_path` matches whole lowercase path *segments* against an
ordered pattern list (`routes`/`controllers`/`endpoints`/`views` → route;
`services`/`usecases` → service; `repositories`/`repository`/`dao` →
repository; `domain`/`models`/`entities` → model;
`schemas`/`dto`/`serializers` → schema; else other) — never a substring
match, so a directory literally named `modeling` does not match `model`
(see `test_matches_whole_path_segments_only`). This is deliberately a
convention-based guess, not a decorator- or base-class-aware analysis
(e.g. `@router.get(...)`, `class X(BaseModel)`): it works across every
language the indexer supports (Python, JavaScript, TypeScript, Go)
without a language-specific analyzer per kind, at the cost of
misclassifying a codebase that doesn't follow the common
routes/services/repositories layering convention. That tradeoff is
consistent with `app/retrieval/dependency_graph.py`'s import-matching
precedent from ADR 0005 — both favor a cheap, generic heuristic over a
precise, per-language one.

### The import graph is name-index lookup, not per-language import parsing

`graph_builder._resolve_import_edges` does not parse `import`/`from`
syntax per language. It builds one `name_index: dict[name, set[file_id]]`
from every file's own module stem (`Path(file.path).stem`) and every
symbol name defined in it, then regex-extracts bare identifiers
(`[A-Za-z_][A-Za-z0-9_]*`, keyword-stripped) out of each import's raw
text and resolves them against that index. This is O(files + imports +
symbols) — one pass to build the index, one pass over imports — not the
quadratic file × file scan a naive "does A's import text contain B's
name" comparison would be, and it needs no per-language grammar for
import statements the way `app/indexing/parser.py`'s tree-sitter grammars
are needed for chunking. The cost is the same class of heuristic as
classification above: a name match is not a resolved import path, so a
coincidental name collision (two unrelated files each defining a `User`
symbol) can produce a false edge. `_referenced_names` excludes a
stopword set (`import`, `from`, `as`, `export`, `interface`, ...) so
language keywords appearing in import statements never masquerade as a
match.

### Two aggregation levels, not one graph

`build_package_graph` returns one node per directory, with edges
aggregated across every file-pair whose files live in different
directories — this is the top-level view and satisfies "do NOT render
thousands of nodes simultaneously." `build_module_graph(package)` returns
one node per file *within that one package*, plus a single collapsed
node for every *other* package any of those files touches (not that
package's individual files) — so drilling into `app/services` shows
`AuthService`/`PaymentService` as real file nodes, while `app/routes`,
`app/repositories`, and `app/schemas` each collapse to one external
package box. This is the "intelligent grouping and progressive
expansion" the brief asked for: expanding one package never re-expands
every package it touches.

### File nodes are labeled by their dominant symbol, not their filename

`_dominant_label` picks the largest class/interface/struct/type symbol
defined in a file (by line span) and uses its name; only a file with no
such symbol (e.g. a route module that's just top-level functions) falls
back to the filename stem. This directly reproduces the brief's own
example — `UserRepository`, not `user_repository.py` — for the common
case of one dominant class per file, and degrades sensibly otherwise.

### A synthetic "database" node, not a modeled data store

Any file classified `repository` or `model` gets an edge to a single
synthetic `database` node (id `"database"`, only added to the graph when
at least one such edge exists). RepoMind has no metadata about which
actual database(s) a repository talks to — this is a deliberate stand-in
representing "persistence," matching the brief's own
`UserRepository → PostgreSQL` example, not a claim about the real
infrastructure.

### "Recent changes" is fetched live from GitHub, not stored

`Commit` rows (ADR 0003) have no per-commit changed-file list — that
limitation was already noted in ADR 0004. Rather than adding a table to
store one, `get_recent_changes` calls GitHub's commits API with a `path`
filter (`rest_client.list_commits_for_path`) on demand, scoped to the one
file the user is inspecting. This avoids ingesting and storing a
changed-file list for every commit in every indexed repository when the
architecture explorer is the only feature that needs it, and only for
whichever files a user actually opens.

### Frontend: `@xyflow/react` + `@dagrejs/dagre`, not a hand-rolled canvas

`@xyflow/react` (React Flow) supplies pan/zoom/minimap/click handling and
a controlled `nodes`/`edges` model; `@dagrejs/dagre` computes a clean
top-to-bottom hierarchical layout from the edge list before nodes are
handed to React Flow (the API returns node positions, React Flow only
renders them — RepoMind owns the layout algorithm, not the library).
Progressive expansion is a click on a package node's "Expand package"
detail-panel action (not a hover or implicit gesture) so it stays
discoverable and keyboard-navigable.

Double-click was also wired as a faster path to the same expand action
(`onNodeDoubleClick` on package nodes) — but shipping it took an extra
step. With `nodesDraggable={false}` on the `<ReactFlow>` instance (the
initial choice, since nothing here needs drag-repositioning), React
Flow's internal drag-gesture handling silently swallowed the native
`dblclick` event before it ever reached the node's `onDoubleClick`
handler — confirmed by instrumenting the handler and by testing an
ordinary React element's `onDoubleClick` in the same page (which fired
correctly), isolating the failure to React Flow's node wrapper
specifically under `nodesDraggable={false}`. Leaving nodes draggable
(their dragged position isn't persisted — the controlled `nodes` prop is
recomputed from the dagre layout on the next render regardless) restores
double-click without disabling anything the explorer relies on; the
"Expand package" button remains the primary, always-reliable affordance.

## What this phase does not do

- No decorator-, type-annotation-, or inheritance-aware classification —
  `classify_path` is a path heuristic only (see above).
- No cross-repository graph — one repository's graph at a time, scoped
  the same way every other repository-scoped endpoint is (ADR 0002's
  `require_repository_access`).
- No persisted node layout or user-arranged positions — the graph is
  recomputed and re-laid-out by dagre on every fetch.
