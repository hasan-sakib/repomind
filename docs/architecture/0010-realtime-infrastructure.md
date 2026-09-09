# ADR 0010: Real-Time Infrastructure

**Status:** Accepted — implemented
**Date:** 2026-09-09

## What was built

- `app/events/` — a small, domain-agnostic event bus:
  - `types.py` — `RealtimeEvent`, the one envelope shape every category
    uses (`indexing`, `sync`, `webhook`, `ai_generation`,
    `notification`), and `EventCategory`.
  - `bus.py` — Redis pub/sub transport: `publish_event` (fire-and-forget,
    one channel per organization) and `subscribe` (an async generator,
    one dedicated Redis connection per subscriber).
  - `publish.py` — the two shapes every service actually needs:
    `publish_state` (a fresh Public-schema payload for a resource) and
    `publish_notification` (a short message for toast/notification-center
    display).
- Publish calls wired into every status transition that already existed:
  `app/indexing/pipeline.py` (progress + terminal states),
  `app/services/sync_service.py` (syncing/synced/failed),
  `app/services/webhook_service.py` (processed/failed, resolved to an
  organization via the installation id every GitHub App webhook carries),
  and the three AI-generation services — `pr_analysis_service.py`,
  `onboarding_service.py`, `analytics_service.py` (running/succeeded/
  failed). No new domain logic — every call site already had a
  `mark_running`/`mark_succeeded`/`mark_failed` transition; this only
  adds a publish alongside the existing commit.
- `GET /api/v1/ws/organizations/{organization_id}` (`app/api/v1/routes/
  websocket.py`) — the one subscriber: authenticates via the same
  `rm_session` cookie and membership check as every other endpoint,
  forwards whatever `subscribe()` yields, and sends a `{"category":
  "ping"}` heartbeat every 25s so a half-open connection (network
  dropped without a clean close) gets torn down instead of leaking.
- Frontend: `lib/realtime/connection.ts` (a reconnecting WebSocket with
  exponential backoff + jitter, capped at 30s, plus an immediate
  reconnect on the browser's `online` event), `lib/realtime/apply-event.ts`
  (writes a state event straight into the matching React Query cache
  entry — no refetch), `lib/realtime-context.tsx` (`RealtimeProvider` /
  `useRealtime()`, mounted once per organization in the dashboard shell),
  a connection-status indicator in the top nav, and a wired-up
  notification bell (previously a static stub).

## Decisions and why

### One channel per organization, not per repository or per resource

Every real-time event this phase needs to carry (indexing, sync, webhook,
AI generation, notifications) already has an organization behind it, and
the frontend already scopes its whole session to one current organization
(`lib/current-org.tsx`) — so the WebSocket route takes an
`organization_id` path param and the frontend opens exactly one
connection per session, reopening only when the organization switcher
changes it. A per-repository channel would mean either one connection
per open repository page (needless churn as the user navigates) or a
client-side fan-in the organization-level channel already gives for
free — the event's own `repository_id` field is what a given page
filters on client-side.

### The event payload is the same Public schema the REST endpoint returns

`publish_state` takes an already-serialized `IndexingJobPublic`/
`RepositoryPublic`/etc. dict, not a bespoke event-specific shape. This
means `lib/realtime/apply-event.ts` can call `queryClient.setQueryData`
directly with the event's `data` — the exact same shape a `GET` request
would have produced — rather than treating the event as a "something
changed, go refetch" signal. That's what makes the frontend update
without a loading flash: the fresh data already arrived, in the shape
the page's query cache expects. The one deliberate exception is
`pull_request_analysis`, whose event `data` also carries
`pull_request_number` alongside the schema's own fields — the REST
response doesn't need it (it's already in the URL), but the WS event
does, since events aren't scoped to a single URL and the query key
(`["pull-request-analysis", repositoryId, number]`) needs it to know
which PR's cache entry to touch.

### `notification` is its own category, published alongside the state event

A terminal (succeeded/failed) transition publishes *two* events on the
same channel: the raw state event (for cache updates) and a
`notification`-category event (title + level, for the bell). Overloading
one event with both meanings — e.g. inferring "toast-worthy" from
category plus status — would couple the notification UI's behavior to
every service's exact status enum. A separate, explicit category means
the frontend's notification handling is the same regardless of which of
the four state categories triggered it, and a future event source that
only ever wants a notification (with no cache to patch) doesn't need a
fake resource to hang one off of.

### Publishing never fails the caller's own transition

`publish_event` catches and logs everything — a Redis hiccup must never
turn a successful `mark_succeeded` (already committed to Postgres) into
a failed request or task. This mirrors the project's existing "never
silently swallow an exception that matters" principle in the other
direction: the *state transition* is the thing that matters and is
already durable by the time publishing runs; the real-time push is a
convenience layered on top, not a second source of truth.

### Auth reuses the session cookie exactly as HTTP does — no new token scheme

`_authenticated_member` in the WebSocket route is a close mirror of
`app/api/deps.py::get_current_user_and_session` + `require_role(VIEWER)`,
just inlined as a function returning `bool` (a WebSocket dependency can't
raise `HTTPException` the way an HTTP one does — the route closes the
connection itself instead). The browser attaches the `rm_session` cookie
to the WebSocket handshake automatically, the same way it would to any
other same-site request; no separate WS auth token or query-string
credential was introduced. Cross-site WebSocket hijacking is mitigated
the same way CSRF is for mutating HTTP requests
(`require_csrf_header`'s own docstring): the cookie is `SameSite=Lax`,
so a cross-*site* page's script-initiated WebSocket handshake never
carries it. An `Origin` header check against `cors_origins` is layered
on top as defense in depth.

### Reconnect: exponential backoff, plus an immediate retry on `online`

A fixed retry interval either hammers the server during a real outage or
leaves the client stuck waiting out a long backoff right after
connectivity actually returns (e.g. a laptop waking from sleep, or
Wi-Fi reconnecting). `RealtimeConnection` backs off exponentially
(1s → 30s cap, with jitter to avoid a thundering herd if many clients
drop at once) on an unexpected close, but also listens for the browser's
`online` event and reconnects immediately, resetting the backoff — the
two together cover both failure modes without polling.

### Existing polling stays, but only fires when the connection isn't open

Every page that used to poll a status field (indexing jobs, repository
sync status, PR analysis, onboarding guide, analytics snapshot) still
has its `refetchInterval`, unchanged in every way except one added
condition: it returns `false` whenever `useRealtime().status === "open"`.
This is a deliberate fallback-not-replacement design — if the real-time
connection is down (reconnecting, or the browser doesn't support/allow
WebSockets in some edge case), the page still updates itself, just less
instantly. Removing polling entirely would make a real-time outage a
silent, total loss of "is this thing done yet?" feedback; keeping it
conditional makes the WebSocket connection a strict improvement rather
than a single point of failure for it.

### No memory leaks: one connection, one set of listeners, always torn down

`RealtimeConnection.stop()` is the only way this class's lifecycle ends,
and it always clears the pending reconnect timer and removes the
`online` listener before closing the socket — called from the
`RealtimeProvider` effect's cleanup function, which React guarantees
runs before the effect re-runs (organization switch) and on unmount. On
the server, the WebSocket route's three tasks (forwarding Redis
messages, the heartbeat, and draining client messages to detect a
disconnect) are cancelled and awaited in a `finally` block regardless of
which one ends the connection first; `subscribe()`'s own `finally`
unsubscribes and closes its Redis connection when the `async for`
consuming it is cancelled, so a dropped WebSocket doesn't leak a Redis
subscription behind it. `tests/integration/test_events_bus.py`'s
`test_subscribe_cleans_up_its_redis_connection_on_cancel_and_aclose`
exercises exactly this path.

## What this phase does not do

- No per-user notification history/read-state persisted server-side —
  the notification list is in-memory per browser tab, capped at 30, and
  reset on organization switch or page reload. A durable notification
  center was not asked for and would need its own storage model.
- No selective subscription to a subset of repositories within an
  organization — the frontend receives every event for the current
  organization and filters client-side by `repository_id`; the volume
  this produces (progress ticks, sync/webhook/AI-generation transitions)
  is not high enough in this product's scope to justify a finer-grained
  channel scheme.
- No message replay/catch-up for events published while a client was
  disconnected — a reconnecting client relies on its still-in-place
  polling fallback and/or a normal page load to pick up whatever state
  changed while it was offline, rather than the server buffering a
  backlog per client.
