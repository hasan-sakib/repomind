# RepoMind — Product Requirements Document

**Status:** Phase 1 (MVP) definition
**Date:** 2026-09-08
**Supersedes:** `docs/product/README.md`

## 1. Overview / problem statement

Developers lose a disproportionate amount of time answering questions a
codebase should be able to answer for itself: "where is this handled," "why
does this exist," "what calls this function," "is this still used anywhere."
This cost is highest in three recurring situations — a new hire ramping on
an unfamiliar repository, an engineer picking up a service they don't own to
fix an incident, and a contractor or reviewer who needs to understand code
they didn't write. In all three cases the fastest available "documentation"
is usually a teammate's time, and that teammate is interrupted to answer
questions the codebase's own commit history and source already contain the
answer to.

Generic AI chat tools (ChatGPT, a general Claude conversation) can discuss
code in the abstract, but they are not grounded in the actual repository:
they hallucinate file paths and function signatures, can't point to a line
number, and know nothing about a private repo unless it's pasted in by
hand. RepoMind's premise is narrow and specific: connect a real GitHub
repository, index it, and let a developer ask questions that are answered
from — and cited to — the actual code, not a plausible-sounding
approximation of it.

Phase 1 builds exactly that grounded question-answering loop. It does not
attempt to replace human-written documentation, generate onboarding guides,
or visualize architecture yet — those are real problems, but they depend on
the ingestion and retrieval core working first, so they are sequenced after
it (see §7).

## 2. Target users

- **New hires and recently onboarded engineers** joining a team with an
  existing, non-trivial codebase, who need to answer "how does X work here"
  questions without waiting on a teammate.
- **Engineers working outside their usual area** — cross-team contributors,
  on-call responders debugging an unfamiliar service, engineers picking up
  a repo after the original owner has left.
- **Individual contributors and small teams evaluating or auditing a
  codebase** they didn't write — due diligence, code review of an
  unfamiliar dependency, open-source contribution.

Phase 1 targets individual developers using RepoMind against repositories
they already have GitHub access to. Team-wide adoption and workspace
collaboration are supported by the data model (see `Workspace`,
`WorkspaceMember`) but are not a Phase 1 UX focus — see non-goals.

## 3. MVP scope (Phase 1): repo ingestion + AI chat Q&A

Phase 1 delivers exactly one vertical slice, end to end: **connect a GitHub
repository, index it, and ask grounded questions about it in a chat
interface, with every answer citing the specific files and line ranges it
was drawn from.**

### 3.1 Definition of "done"

Phase 1 is complete when a user can, without engineering assistance:

1. Sign in with their GitHub identity.
2. Install the RepoMind GitHub App on an account or organization and select
   one or more repositories to grant it access to.
3. Connect one of those repositories inside RepoMind and watch it move
   through indexing status (`pending` → `indexing` → `ready`, or `failed`
   with a visible reason) driven by real ingestion progress, not a fake
   progress bar.
4. Open a chat scoped to that repository, ask a natural-language question
   about the code, and receive a streamed answer that:
   - is grounded in retrieved chunks of the actual repository content at
     the indexed commit,
   - includes one or more citations, each naming a file path and a line
     range, that a user can trust corresponds to real code in the repo.
5. Push a commit to the connected repository's default branch and see the
   index update to reflect it (via webhook-triggered re-ingestion) without
   manually re-triggering anything.

### 3.2 In scope

- GitHub App–based authentication (login) and installation (repo access) —
  a single GitHub App serves both purposes.
- Personal workspace auto-provisioned per user on first login.
- Connecting repositories the installation has access to, one at a time,
  to a workspace.
- Full-repository ingestion: clone, chunk, embed, store.
- Incremental re-ingestion on `push` webhook events, scoped to changed
  content (via content hashing), not a full re-index per push.
- Chat Q&A scoped to a single connected repository, with streamed answers
  and file/line citations.
- Multiple chat sessions per repository, with basic history.
- Visible ingestion status and error surfacing (a failed clone or a
  malformed repo state is shown to the user, not swallowed).

### 3.3 Explicit non-goals for Phase 1

These are real, planned features — deferred because they depend on the
ingestion/retrieval core defined here, not because they're deprioritized
indefinitely:

- **Automated onboarding-guide generation.** Producing a structured,
  human-readable onboarding document from a repository is a distinct
  generation problem (structure, tone, completeness) layered on top of the
  same retrieval core. Not built in Phase 1.
- **Architecture / dependency visualization.** Rendering module or service
  dependency graphs requires a structural analysis pass beyond chunk-level
  retrieval. Not built in Phase 1.
- **Team workspace collaboration UI.** The data model supports multi-member
  workspaces (`WorkspaceMember`, roles) so it doesn't need to be
  retrofitted later, but there is no Phase 1 UI for inviting teammates,
  managing roles, or shared chat visibility across members. A workspace is,
  in practice, single-user in Phase 1.
- **Billing / plans / usage limits.** No pricing tiers, payment
  integration, or usage metering. Everything runs unmetered for Phase 1.
- **Multi-provider AI or embedding model switching in the UI.** The
  provider abstractions exist for engineering flexibility, not as a
  user-facing setting.

## 4. Core user flows

### 4.1 Sign up / login

1. User visits RepoMind and clicks "Sign in with GitHub."
2. RepoMind redirects to GitHub's OAuth authorization flow associated with
   the RepoMind GitHub App.
3. GitHub redirects back to RepoMind's callback with an authorization code.
4. Backend exchanges the code for the user's GitHub identity, creates or
   updates the `User` record (`github_user_id`, `username`, `avatar_url`,
   `email`), and — if this is the user's first login — auto-creates a
   personal `Workspace` with the user as `owner`.
5. Backend issues a session: a short-lived access token in an httpOnly
   `rm_session` cookie and a rotated refresh token in an httpOnly
   `rm_refresh` cookie.
6. User lands in their workspace dashboard, authenticated.

### 4.2 Install GitHub App + connect a repository

1. From the dashboard, user clicks "Connect a repository."
2. If no GitHub App installation exists yet for their account/org, user is
   sent to GitHub's App installation flow and selects which repositories
   (or "all repositories") to grant access to.
3. GitHub redirects back to RepoMind; backend records the installation as a
   `GitHubInstallation` (`github_installation_id`, `account_login`,
   `account_type`) tied to the user's workspace.
4. RepoMind lists the repositories the installation can see (via the GitHub
   API, using a freshly minted installation token).
5. User selects a repository; RepoMind creates a `Repository` record
   (`status = pending`) linked to that installation and workspace.
6. Backend enqueues an `IngestionJob` for the repository and returns
   immediately — the UI does not block on indexing.

### 4.3 Watch ingestion progress

1. User is shown the repository's status, polling or subscribing to
   `/repositories/{id}/ingestion-status`.
2. Status transitions: `pending` → `indexing` (job picked up by the worker)
   → `ready` (success) or `failed` (with an error message surfaced from
   `IngestionJob.error`).
3. On `ready`, the repository's chat entry point becomes available and
   `last_indexed_commit_sha` / `last_indexed_at` are shown so the user knows
   exactly what state the index reflects.

### 4.4 Ask questions in chat

1. From a `ready` repository, user opens or creates a `ChatSession`.
2. User types a question; it is appended as a `ChatMessage` with
   `role = user`.
3. Backend embeds the question, runs a similarity search against that
   repository's indexed `CodeChunk`s, assembles retrieved context, and
   streams an assistant response over Server-Sent Events.
4. The streamed response is persisted as a `ChatMessage` with
   `role = assistant` and a `citations` array of `{file_path, start_line,
end_line}` once complete.
5. User sees inline citation references in the answer and can jump to the
   cited file/line range (rendered, not fetched live from GitHub, in
   Phase 1 — the cited content comes from the indexed chunk).
6. User can continue the conversation in the same session; prior messages
   provide conversational context for follow-up questions.

### 4.5 Re-ingestion on push

1. A commit is pushed to the connected repository's default branch on
   GitHub.
2. GitHub sends a `push` webhook to `/webhooks/github`.
3. Backend verifies the webhook signature, resolves it to a `Repository`,
   and debounces: rapid successive pushes to the same repository collapse
   into a single re-ingestion rather than one job per push.
4. A new `IngestionJob` runs: changed files are re-chunked and re-embedded
   based on content hash (unchanged chunks are not re-embedded); the
   repository's `status`, `last_indexed_commit_sha`, and `last_indexed_at`
   are updated on completion.
5. Chat continues to work against the previous index until the new
   ingestion completes — a push in progress does not take chat offline.

## 5. Success criteria / what "shippable" means for Phase 1

Phase 1 is shippable when all of the following hold, demonstrably, against
a real (not synthetic/toy) public or private repository:

- A first-time user can go from "never used RepoMind" to "asking questions
  in chat about a real repo" without any manual intervention from the
  engineering team.
- Ingestion completes for a repository in the low-thousands-of-files range
  in a bounded, visible amount of time, with progress that reflects actual
  job state.
- At least a strong majority of test questions asked against a known
  repository return answers whose citations point to file/line ranges that
  actually contain content relevant to the answer (spot-checked manually
  across a fixed evaluation set — Phase 1 does not require an automated
  eval harness, but the team should hand-verify a representative sample
  before calling this done).
- A failed ingestion (bad clone, empty repo, unsupported content) fails
  visibly with a message the user can act on, rather than hanging in
  `pending`/`indexing` indefinitely or failing silently.
- Re-ingestion on push is verified end-to-end at least once against a real
  webhook delivery, not just triggered manually.
- Session handling (login, refresh, logout) works across a normal browser
  session without requiring re-login inside the 30-day refresh window.

## 6. Roadmap after Phase 1

With ingestion and grounded retrieval working, Phase 2 is expected to build
automated onboarding-guide generation on top of the same indexed chunks and
retrieval pipeline — producing a structured document (not just chat
answers) summarizing a repository's structure, entry points, and key
conventions. Phase 3 is expected to add architecture and dependency
visualization, which requires a structural analysis pass (import graphs,
service boundaries) beyond the chunk-level retrieval built here. Team
workspace collaboration (invites, roles, shared visibility) and billing are
expected to follow once there is a multi-user reason to need them — the
data model in Phase 1 (`Workspace`, `WorkspaceMember`) is deliberately built
to support this without a schema migration when that phase starts.
