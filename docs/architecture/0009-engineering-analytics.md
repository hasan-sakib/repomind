# ADR 0009: Engineering Analytics

**Status:** Accepted — implemented
**Date:** 2026-09-09

## What was built

- `app/analytics/` — pure aggregation functions, one module per metric
  family, each operating on already-fetched GitHub data with no I/O of
  its own:
  - `commits.py` — buckets commits into per-(day, author) counts.
  - `pull_requests.py` — buckets PRs into per-day opened/merged/closed
    counts, and computes cycle time (median hours from open to
    merge/close, plus the slowest sampled PRs).
  - `issues.py` — buckets issues into per-day opened counts, and
    summarizes open issues (total count, plus the oldest ones past a
    configurable staleness threshold).
  - `contributors.py` — merges the commit and PR buckets into one
    per-contributor activity ranking.
  - `hotspots.py` — rolls per-commit file diffs up into file-level and
    package-level change-frequency rankings, reusing `package_of` and
    `classify_path` from `app/architecture/graph_builder.py` so a
    hotspot's package/kind is the same concept the architecture explorer
    already uses (ADR 0006).
- Two new `rest_client.py` calls, both bounded: `list_commits_paginated`
  (up to `MAX_ANALYTICS_COMMITS = 300` commits, for deep history the
  dashboard-level sync in ADR 0003 never keeps) and `get_commit_files`
  (a single commit's changed-file list, reusing
  `GitHubPullRequestFile.from_api` rather than a duplicate type).
- `AnalyticsSnapshot` (new table) — one row per generation, holding
  every aggregate as JSONB plus a few scalar summary fields
  (`median_cycle_time_hours`, `open_issues_total`, sample sizes).
- `app/services/analytics_service.py` — the trigger/cache/poll pattern
  from ADR 0004/0007/0008: `trigger_snapshot_generation` returns a
  cached row unless `force=True`; `run_generation` does the actual work
  in the `generate_analytics_snapshot` arq task, opening its own DB
  session and always reaching `mark_succeeded` or `mark_failed`.
- `GET/POST /repositories/{id}/analytics` — the same shape as every
  other generated-artifact route in this codebase.
- Frontend: `/analytics` (repository picker) and
  `/repositories/{id}/analytics` (the dashboard) — a time-range filter,
  a contributor filter that a leaderboard click also drives, and seven
  chart/panel sections ending in a two-level Code Hotspots view
  (files, then packages).

## Decisions and why

### No LLM anywhere in this phase

Every field on `AnalyticsSnapshot` is a computed aggregate over real
commit/PR/issue data — there is no `AIProvider` dependency anywhere in
`app/analytics/` or `analytics_service.py`. Commit frequency, PR
throughput, and hotspot counts are exactly-computable from the data;
asking a model to summarize them would add cost, latency, and a chance
of getting a count wrong for something that already has one correct
answer. This mirrors ADR 0008's reasoning for its non-AI sections,
applied to the whole phase rather than half of it.

### Deep history required new bounded GitHub calls, not a new sync

The dashboard-level sync (`sync_service.py`, ADR 0003) fetches only
~50 of each entity — enough for the repository overview, not enough for
a 90-day commit-frequency trend or a meaningful hotspot sample. Rather
than widen that sync (which every page pays for) analytics generation
makes its own live, bounded calls: up to 300 commits for the frequency
chart, and up to 100 of those (`MAX_HOTSPOT_COMMITS`) get their changed-
file list fetched for hotspot aggregation, using
`asyncio.Semaphore(10)` so that up to 100 HTTP calls never fire fully
concurrently. This is also why generation is an arq job rather than
inline in the request — a call volume this size doesn't belong in an
HTTP request/response cycle.

### PR "review latency" is measured as cycle time, and the UI says so

The brief asks for PR review latency. Literal time-to-first-review
needs GitHub's PR reviews API — another bounded fetch per PR, on top of
the commit-file fetches above — which is disproportionate to what this
phase's data already has synced. `compute_cycle_time` measures open to
merge/close instead, a legitimate and widely-used proxy metric, and
`CycleTimePanel` carries an explicit footnote: "Measured from PR open to
merge/close — not time to first review (this repository's synced data
doesn't track individual reviews)." Substituting a proxy silently would
violate the brief's own "use real data" instruction in spirit even
though every number shown is real; naming the substitution is what keeps
it honest.

### Snapshots are never auto-invalidated by a new sync

Unlike `PullRequestAnalysis`/`OnboardingGuide` (ADR 0007/0008), which
invalidate on `head_sha`/the latest indexed commit, `AnalyticsSnapshot`
has no invalidation key at all. Generation cost (up to ~100 GitHub
calls) is far higher than a sync, so re-running it automatically every
time a repository syncs would be wasteful for a metric set that doesn't
need to be real-time. `synced_through` records `repository.last_synced_at`
at generation time purely so the UI can tell the viewer how fresh the
underlying data is; regenerating only ever happens through an explicit
"Regenerate" click (`force=True`).

### Hotspot package rollup is computed from the full per-file data, before truncation

`aggregate_hotspots` builds the complete per-file `change_counts` dict
once, then derives *both* the top-N file hotspots and the package-level
rollup from that same full dict. Truncating to the top N files first and
then rolling those up to packages would silently undercount package
totals whenever a package's changes are spread across more files than
fit in the top N — a dedicated test
(`test_architecture_hotspots_roll_up_by_package_using_full_data_not_truncated_files`)
sets the file limit to 1 while asserting the package rollup still
reflects all underlying files.

### Chart colors are validated, not chosen by eye

The frontend's categorical palette (five hues, reused across all
multi-series charts) was picked and checked with a colorblind-simulation
validator before being wired into `globals.css`'s `--chart-1..5` tokens,
rather than eyeballed. Color is assigned by series identity everywhere
(never by rank), each chart has exactly one y-axis, and every chart has
tooltips/labels/borders in addition to color so the one contrast warning
the validator raised is mitigated by the "relief rule" rather than
ignored.

## What this phase does not do

- No time-to-first-review metric — see "cycle time" above.
- No cross-repository analytics rollup — one repository's snapshot at a
  time, matching every other generated-artifact page in this codebase.
- No scheduled/automatic regeneration — a snapshot is only ever
  generated or regenerated by an explicit user action.
- No per-contributor breakdown of PR/issue counts — the snapshot's daily
  PR/issue buckets are repository-wide; only commit counts are tracked
  per author, so the contributor filter on the combined activity chart
  only ever narrows the commit series.
