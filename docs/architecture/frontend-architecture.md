# Frontend Architecture

> **Note:** the routing model below (`[workspaceSlug]/[repoSlug]/...`) was
> superseded before implementation. Phase 2 shipped flat routes
> (`/dashboard`, `/settings`, `/settings/members`) with the active
> organization tracked client-side instead of in the URL — see
> `docs/architecture/0002-auth-and-multi-tenancy.md`. Phase 3 continued
> that pattern for repositories: `/repositories/[repositoryId]` (not
> `[workspaceSlug]/[repoSlug]`), with `/dashboard` itself becoming the
> connected-repositories list — see
> `docs/architecture/0003-github-integration.md`. The data-fetching
> split, state-management reasoning, and UX conventions (loading/empty/
> error states) below still describe what was actually built. The chat
> routing sketch in §3 (`chat/page.tsx` / `chat/[sessionId]/page.tsx`,
> `ChatSession`, `/chat/sessions/{id}/...` endpoints) and the
> `useChatStream` hook in §4 anticipated the real shape closely —
> Phase 5 built the same two-route pattern under `/repositories/
> {id}/chat/` and `/repositories/{id}/chat/{conversationId}`, and SSE
> parsed by hand over `fetch` rather than `EventSource`, for the same
> reason given here (a POST body + custom CSRF header `EventSource`
> can't send) — but with different names throughout (`Conversation`
> not `ChatSession`, `/conversations/{id}/messages` not `/chat/
> sessions/{id}/messages`) and the streaming logic inlined into
> `components/chat/chat-shell.tsx` rather than factored into a
> standalone `useChatStream` hook. See
> `docs/architecture/0005-ai-rag-engine.md` for the real API surface,
> component list, and the reasoning behind each divergence.

**Status:** Design (Phase 1) — targets implementation in Phase 2
**Scope:** `frontend` routing, auth-aware layout, data-fetching split between
server and client components, state management, component organization,
rendering strategy, and UX conventions (loading/empty/error states,
accessibility, responsiveness).
**Companion docs:** `docs/architecture/system-architecture.md` (whole-system
view), `docs/architecture/backend-architecture.md` (the auth model and API
this frontend talks to), `docs/api/api-design.md` (exact request/response
shapes, once written), `docs/deployment/deployment.md` (Vercel deployment,
domain topology — relevant here because cookie auth depends on it, see §3).

This document extends the Phase 0 scaffold recorded in
`docs/architecture/0001-foundation.md`: Next.js App Router, TypeScript,
Tailwind v4, shadcn/ui on `@base-ui/react`, a React Query provider
(`components/providers.tsx`), and a single HTTP boundary
(`lib/api-client.ts`). None of that is revisited here except where Phase 2
requires extending it. It does not specify the visual design system or the
implementation of `components/shell/*` — those are a concurrent workstream;
this document specifies the architectural role those components play (what
data they need, what state they own), not their markup or styling.

## 1. Route structure

```
frontend/app/
  (auth)/
    login/page.tsx                       Public. "Sign in with GitHub".
  (dashboard)/
    page.tsx                             Resolves the active workspace, redirects.
    [workspaceSlug]/
      layout.tsx                         Shell: Sidebar, TopNav, switchers.
      page.tsx                           Repository list for the workspace.
      settings/page.tsx                  Workspace settings.
      [repoSlug]/
        layout.tsx                       Repo header, ingestion-status banner.
        page.tsx                         Repository detail / overview.
        chat/
          page.tsx                       Default/most-recent chat session.
          [sessionId]/page.tsx           A specific chat session.
  layout.tsx                             Root layout (existing).
  middleware.ts
```

Route groups `(auth)` and `(dashboard)` share no layout and impose no URL
segment — they exist purely to scope `middleware.ts` decisions and let each
side of the app have an independent root layout. A `(marketing)` group for a
public landing page is explicitly **out of scope for Phase 1**; it is
deferred, not designed here, and should not be inferred from this structure.

`workspaceSlug` resolves to a `Workspace` via `slug` (per the domain model in
`backend-architecture.md`). `repoSlug` is treated by the frontend as an
opaque route segment resolved through the repository list response, not a
value the frontend constructs itself — whether it is a stored `Repository`
slug column or a client-derived slug from `full_name` is a backend data-model
decision (`backend-architecture.md`/`database/README.md`); this doc only
requires that `GET /workspaces/{id}/repositories` return enough to map
`repoSlug` back to a `repository_id`.

`chat/page.tsx` vs `chat/[sessionId]/page.tsx`: a repository can have more
than one `ChatSession`. `chat/page.tsx` loads (or lazily creates) the most
recent session and is the link target from the repo overview page;
`chat/[sessionId]/page.tsx` is what a session switcher in the chat header
links to. Both render the same client chat surface — the outer route only
decides which session's history to fetch for the initial render.

## 2. `middleware.ts` — UX-layer redirect, not a security boundary

```ts
// frontend/middleware.ts (sketch, not final implementation)
export function middleware(request: NextRequest) {
  const hasSession = request.cookies.has("rm_session");
  const path = request.nextUrl.pathname;

  if (isDashboardPath(path) && !hasSession) {
    return NextResponse.redirect(new URL("/login", request.url));
  }
  if (path === "/login" && hasSession) {
    return NextResponse.redirect(new URL("/", request.url));
  }
  return NextResponse.next();
}
```

This checks only for the _presence_ of the `rm_session` cookie — it does not
decode or verify the JWT (no signature check, no expiry check). Middleware
runs on the Edge runtime and deliberately stays cheap and dependency-free;
real verification is the API's job on every request
(`get_current_user`, `backend-architecture.md` §2.4). A user with an expired
or tampered `rm_session` cookie passes this check, reaches a server component,
and gets a 401 from the API on the first fetch — that is expected and
correct. **This middleware exists to avoid flashing an authenticated shell at
a logged-out user and to avoid an unnecessary round trip to a page that will
immediately bounce; it grants no access and enforces nothing.** Removing it
entirely would degrade UX, not create a vulnerability — every route handler
downstream still enforces auth independently. This is stated explicitly
because it is a common misreading of middleware-based redirects in Next.js
apps, and the distinction matters for anyone extending this file later.

Redirecting an authenticated user away from `/login` targets `/`, not a
guessed workspace slug — middleware cannot decode `active_workspace_id` from
the JWT without the verification it deliberately skips. `(dashboard)/page.tsx`
is a server component that calls `GET /api/v1/auth/me`, reads the caller's
default/active workspace, and calls `redirect()` to `/{workspaceSlug}`. This
keeps the "which workspace is default" decision entirely server-side and out
of middleware.

## 3. Data fetching: server components fetch, client components sync

**Server components fetch once, for the initial render.** Every page listed
in §1 fetches its own data directly from the API in the server component body
— `(dashboard)/[workspaceSlug]/page.tsx` calls
`GET /workspaces/{id}/repositories`, `[repoSlug]/page.tsx` calls
`GET /repositories/{id}`, `chat/page.tsx` calls
`GET /repositories/{id}/chat/sessions` and
`GET /chat/sessions/{id}/messages` for history. There is no client-side
"loading" flash for data that was available at request time.

Server-side fetches must forward the incoming request's cookies explicitly —
a server component's `fetch` call to the API is a _server-to-server_ request
to a different origin, so cookies are never attached automatically the way a
browser attaches them to a same-origin request. The plan is a
`serverApiFetch` variant alongside the existing `apiFetch` in
`lib/api-client.ts` that reads `cookies()` from `next/headers` and sets the
`Cookie` header manually:

```ts
// lib/api-client.ts (planned addition, not yet implemented)
export async function serverApiFetch<T>(path: string, init?: RequestInit) {
  const cookieStore = await cookies();
  return apiFetch<T>(path, {
    ...init,
    headers: { ...init?.headers, Cookie: cookieStore.toString() },
    cache: "no-store",
  });
}
```

`cache: "no-store"` is deliberate for every authenticated fetch — Next.js's
fetch cache defaults are tuned for public content, and per-user data (a
workspace's repository list, chat history) must never be served from a
shared cache keyed only on URL.

**Client components own anything that refetches, mutates, or streams after
initial load.** Concretely:

- **Ingestion status polling.** `Repository.status` moves through
  `pending → indexing → ready|failed` over minutes, not seconds
  (`backend-architecture.md` §"Workers"). A client component wraps
  `GET /repositories/{id}/ingestion-status` in React Query with
  `refetchInterval`, active only while `status` is `pending` or `indexing`;
  the query stops refetching once a terminal status (`ready`/`failed`) is
  reached. The initial `status` value comes from the server-rendered fetch in
  §3 above — the client query hydrates from that, it does not start from
  nothing.
- **Chat message sending and streaming.** `POST /chat/sessions/{id}/messages`
  returns `text/event-stream` (token-deltas, then a final event carrying
  citations — `backend-architecture.md` §4, `system-architecture.md` §3.2).
  This is not read through React Query's request/response model; it's a
  dedicated hook, `useChatStream` (§4).
- **UI-only state with no server counterpart** — sidebar collapsed, command
  palette open, which switcher dropdown is open. Plain component state or the
  shared UI context described in §5; never modeled as a query.

## 4. `useChatStream` — manual SSE parsing over `fetch`, not `EventSource`

The browser's `EventSource` API cannot be used here: it only issues `GET`
requests, accepts no request body, and cannot attach the custom
`X-Requested-With` header the backend requires on mutating requests
(`backend-architecture.md` §2.5). Since sending a chat message is a `POST`
with a JSON body that must carry that header, `useChatStream` opens the
stream itself via `fetch` and reads the response body as a
`ReadableStream<Uint8Array>`, decoding and parsing SSE frames by hand:

```ts
// lib/use-chat-stream.ts (planned shape)
async function* parseSSE(body: ReadableStream<Uint8Array>) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buffer += decoder.decode(value, { stream: true });
    let boundary: number;
    while ((boundary = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);
      yield parseFrame(frame); // -> { event?: string; data: string }
    }
  }
}
```

`useChatStream` consumes this generator, appends each token-delta event to an
in-progress assistant message held in local component state, and on the
final event (carrying citations) hands the completed message off to React
Query's cache for the session's message list (`setQueryData`, appended once,
not on every token — avoid re-rendering the whole list per delta). Fetch
abort (`AbortController`) is used for stream cancellation if the user
navigates away or explicitly stops generation; there is no reconnect-on-drop
behavior planned for Phase 1 — a dropped stream ends the turn and the user
can re-ask, which is an acceptable MVP tradeoff given chat turns are short.

## 5. State management: no global state library

RepoMind's frontend does not use Redux, Zustand, Jotai, or any comparable
client-state library. This is a deliberate omission, not a gap:

- **Server state** (everything that originates from the API — workspaces,
  repositories, ingestion status, chat history) is owned by React Query. It
  already solves caching, refetching, and request de-duplication; a second
  store re-holding the same data would be a synchronization bug waiting to
  happen, not an abstraction.
- **UI-only state** (sidebar collapsed, command palette open/closed, which
  switcher is open, the in-progress streaming message before it's committed
  to the query cache) is small enough — a handful of booleans and one
  transient value — that it lives in either component-local `useState` where
  a single component tree needs it, or a single `app-shell-context.tsx`
  React context where the shell (`Sidebar`, `TopNav`, `CommandPalette`) needs
  to coordinate (e.g. closing the sidebar sheet when the command palette
  opens on a narrow viewport).

Reaching for Redux/Zustand here would be the kind of premature abstraction
RepoMind's engineering principles reject elsewhere in this codebase (see the
service/repository layering discipline in `backend-architecture.md`) — adding
a state-management dependency, a provider, and a set of actions/selectors to
manage a state surface that fits in one `useReducer` call is complexity with
no corresponding problem. Revisit only if the UI-state surface actually grows
past what a single context comfortably holds (it did not, as of this
writing, for any Phase 1 or Phase 2 screen).

## 6. Component organization

```
components/
  ui/       shadcn primitives on @base-ui/react (scaffolded Phase 0: button,
            card, dialog, sheet, tabs, tooltip, dropdown-menu, command,
            input, textarea, table, badge, avatar, popover, scroll-area,
            separator, skeleton, label, input-group).
  shell/    Composite app-shell components: Sidebar, TopNav, WorkspaceSwitcher,
            RepoSwitcher, CommandPalette, UserMenu, Breadcrumbs,
            NotificationsMenu. Built on components/ui/*. Implemented by a
            concurrent workstream; this doc governs their data contracts
            (e.g. WorkspaceSwitcher receives the workspace list already
            fetched by the layout server component, it does not fetch its
            own data) and where they sit relative to server/client
            boundaries (§7), not their visuals.
  chat/     Chat-specific components (Phase 2): MessageList, MessageBubble,
            Composer, CitationLink, SessionSwitcher. Consumes useChatStream.
lib/
  api-client.ts       Existing. Grows serverApiFetch (§3).
  use-chat-stream.ts  New (§4).
  query-keys.ts       New — centralizes React Query key factories so
                      invalidation (e.g. "ingestion status changed, also
                      refresh the repository list") isn't done by
                      string-matching keys ad hoc across files.
```

## 7. Rendering strategy: server components by default

Every component is a server component unless it has a concrete reason not to
be. A concrete reason is one of:

1. **Interactivity that needs event handlers** — a button's `onClick`, a
   form's `onSubmit`, a switcher's open/close state.
2. **A browser-only API** — `useChatStream`'s `fetch` + `ReadableStream`
   consumption, `localStorage` for any per-viewer preference, `EventListener`
   registration for keyboard shortcuts (command palette).
3. **Data that must update after the initial render without a full page
   navigation** — ingestion-status polling, chat streaming.

What is _not_ a sufficient reason: "this component is inside a page that has
some interactive parts elsewhere." The `"use client"` boundary should sit at
the leaf that actually needs it — e.g. on `[repoSlug]/page.tsx`, the static
repository metadata (name, connected date, default branch) renders as a
server component; only the small ingestion-status badge that polls is a
client component, imported into the server-rendered page. Marking the whole
page `"use client"` because one badge polls would lose server rendering for
everything else on the page for no benefit — this is the reflex this
document explicitly pushes back on.

**Code-splitting, forward-looking.** Nothing in Phase 1 needs it, but two
Phase 2+ features are known to warrant `next/dynamic` with `ssr: false`: a
syntax-highlighting library for rendering code in chat citations and repo
views, and an eventual architecture-visualization feature (graph rendering).
Both are heavy, browser-only-relevant dependencies that should never be part
of the initial page bundle or server-rendered; noting the expectation now so
it isn't reinvented ad hoc later.

> **Update (Phase 6):** the architecture-visualization feature was built —
> see `docs/architecture/0006-architecture-dependency-graph.md`. In
> practice it did not need `next/dynamic`: `@xyflow/react` is imported
> directly into `"use client"` route-scoped components, and the App
> Router's per-route chunking already keeps it out of every other page's
> bundle. `pnpm run build` confirmed both architecture routes compile and
> prerender without an SSR/window issue.

## 8. Loading, empty, and error states

These are conventions, not suggestions — every route segment listed in §1
follows them:

- **Loading: skeletons shaped like the final layout, never a bare spinner.**
  Each route segment with a server-fetched initial render gets a
  `loading.tsx` built from `components/ui/skeleton.tsx` sized and arranged
  like the real content — the repository list's `loading.tsx` renders N
  placeholder cards in the same grid the real list uses, not a centered
  spinner. This keeps layout shift near zero when real data arrives.
- **Empty states name the next action, not just the absence of data.** A
  workspace with zero connected repositories renders "Connect a repository"
  with the action inline, not "No repositories found." An empty chat session
  prompts a first question with example phrasing, not a blank pane. Every
  empty state answers "what do I do now," not just "there is nothing here."
- **Errors: `error.tsx` at the route-segment level, reserved for genuinely
  unexpected failures.** Next.js's `error.tsx` convention provides a
  segment-scoped client error boundary (with `reset()`) for render exceptions
  — a malformed response, a thrown error in a component. It is not used for
  documented, expected data states: a `Repository.status === "failed"` is
  rendered inline as a normal data state (an error summary and a "retry
  ingestion" action inside the page), not thrown to trigger `error.tsx`, and
  a repository that doesn't exist or isn't in the caller's workspace calls
  Next's `notFound()` to render `not-found.tsx`, not `error.tsx`. The
  distinction: `error.tsx` is for "something broke that shouldn't have";
  inline data states are for "the system told us this, correctly."

## 9. Accessibility and responsiveness

Desktop is the primary experience — this is a developer tool used at a
workstation, not a mobile-first product — but the shell does not merely
squeeze at narrower widths:

- **Command palette and switchers are fully keyboard-operable**: a global
  shortcut opens the command palette, arrow keys move selection, `Enter`
  activates, `Escape` closes and returns focus to the trigger that opened it.
  `WorkspaceSwitcher`/`RepoSwitcher` follow the same pattern as accessible
  combobox/listbox widgets (this falls out of `@base-ui/react`'s primitives
  used correctly, not custom ARIA wiring).
- **Semantic structure**: landmark elements (`nav`, `main`, `aside`) for the
  shell regions, real heading hierarchy per page, no `div`-as-button.
- **Visible focus states** are never suppressed; `prefers-reduced-motion` is
  respected for any transition (sidebar collapse, command palette open/close,
  streaming-message appearance) by disabling or shortening the animation, not
  just the default motion.
- **Responsive breakpoint strategy**: above a defined breakpoint (the shell
  workstream's implementation choice, expected around Tailwind's `lg`), the
  sidebar renders persistently; below it, the sidebar becomes a `Sheet`
  (already scaffolded in `components/ui/sheet.tsx`) triggered from the top
  nav, rather than shrinking in place. The chat view and repository list
  reflow to a single column below that same breakpoint. This is the shell
  workstream's implementation to build; this document records the expected
  architecture (collapse-to-drawer, not squeeze) so it isn't decided
  ad hoc per component.

## 10. A cross-cutting note on cookies and cross-origin fetch

Client components call the API directly from the browser (React Query
polling, `useChatStream`), which means those `fetch` calls must set
`credentials: "include"` — the browser does not attach cookies to a
cross-origin request by default even when `SameSite=Lax` would otherwise
permit it. Whether it _is_ permitted at all depends on the production domain
topology: `SameSite=Lax` allows a cookie on a cross-_origin_ request only if
it is still same-_site_ (same registrable domain). This only works if the web
app and the API are deployed under the same apex domain (e.g. `app.<domain>`
and `api.<domain>`) — see `deployment.md` §"Domains and the cookie/CORS
constraint" for the deployment-side implication, including a real gap this
creates for Vercel preview deployments that this document does not attempt to
resolve on its own.

## 11. What Phase 0 already built vs. what this document specifies

**Already built:** App Router skeleton, root layout, `Providers`
(`QueryClientProvider`, `TooltipProvider`), `lib/api-client.ts`'s `apiFetch`,
a full `components/ui/*` primitive set, a placeholder home page with a
`SystemStatus` health-check widget.

**Specified here, for Phase 2 implementation:** `middleware.ts`; the
`(auth)`/`(dashboard)` route groups and every page under them; the
server/client data-fetching split; `serverApiFetch`; `useChatStream`;
`app-shell-context.tsx`; `loading.tsx`/`error.tsx`/`not-found.tsx` per
segment; and the data contracts `components/shell/*` needs from its callers
(built concurrently, governed here). Nothing here requires revisiting the
Phase 0 provider setup or the shadcn/`@base-ui/react` choice.
