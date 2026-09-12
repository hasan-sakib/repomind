# Design System

This documents the actual token and component decisions implemented in
`frontend` for Phase 1 (application shell). It supersedes any tokens
shadcn's `init` scaffolded by default — see `frontend/app/globals.css`
for the source of truth; this file explains the _why_ behind it.

## Foundation

shadcn/ui in this project version is built on `@base-ui/react` (not Radix —
this shadcn release moved off Radix; component internals use base-ui's
`render` prop for polymorphism and its own Menu/Popover/Dialog primitives).
All customization happens at two levels:

1. **Design tokens** — CSS custom properties in `globals.css`, consumed via
   Tailwind v4's `@theme inline` block. Changing a token changes every
   component that uses it; this is the only place color/radius decisions
   are made.
2. **Component variants** — `class-variance-authority` variant maps in
   `components/ui/*.tsx`, extended (not replaced) with project-specific
   variants where needed (e.g. `success`/`warning`/`brand` badge variants).

## Color

Base palette is a neutral OKLCH grayscale (near-black text on near-white
background in light mode, inverted in dark) — deliberately monochrome for
the majority of the UI, matching the Linear/Vercel/GitHub reference
aesthetic rather than a colorful "AI SaaS" look.

One accent color (`--brand`, a desaturated blue at `oklch(0.546 0.215
262.881)` in light mode / `oklch(0.646 0.194 259.2)` in dark) is used
narrowly: focus rings, active nav indicators, links, the active repository
dot, primary interactive affordances in switchers. It was chosen over a
violet/purple accent specifically to avoid the "purple AI aesthetic" the
project brief calls out, and over no accent at all (pure monochrome) because
a single consistent accent color meaningfully helps scan a dense,
information-heavy UI (which repository is indexing right now, which nav
item is active).

Two semantic status colors were added beyond shadcn's defaults:
`--success` and `--warning`. `--destructive` (already provided by shadcn)
covers failure states. Used today for account/member status (email
verified/unverified, owner role) in `(dashboard)/settings/page.tsx` and
`(dashboard)/settings/members/page.tsx`; the original repository-status
mapping this section described (`pending`/`indexing`/`ready`/`failed`,
via a `status-dot.tsx` component) was Phase 1 shell demo data and was
removed when Phase 2 replaced the demo shell with real auth data — it
will return once repository ingestion is actually built (Phase 3+), using
the same tokens.

## Typography

Geist Sans / Geist Mono (already the create-next-app default) — kept as-is;
both are restrained, technical typefaces consistent with the developer-tool
reference products. No root font-size change: the browser default 16px base
is preserved so shadcn's component paddings (calibrated against the
standard Tailwind rem scale) don't silently drift. Information density is
achieved by convention, not by shrinking the base scale: UI chrome (nav,
table cells, badges, breadcrumbs) uses `text-sm`/`text-xs`; `text-lg` and
above are reserved for page-level headings only, and there are very few of
those in a developer tool.

## Spacing & radius

Tailwind's default spacing scale is unchanged. Radius was tightened from
shadcn's default (`--radius: 0.625rem` / 10px base) to `--radius: 0.5rem`
(8px base), cascading to smaller values for `sm`/`md` and slightly larger
for `xl`/`2xl`. This keeps cards, dialogs, and popovers looking precise
rather than "soft" — avoiding the "giant rounded cards" pattern the project
brief explicitly warns against. Pill-shaped badges (`rounded-4xl`, from
shadcn's default) were kept as-is: a fully-rounded small status pill reads
as a label, not a card, and is standard in every reference product (GitHub
labels, Linear status pills).

## Borders & shadows

Borders are hairline (1px, low-contrast neutral) and are the primary way
surfaces are separated — the sidebar, top nav, table, and cards all use
`border-border` rather than shadows. Shadows are reserved for genuinely
elevated, transient surfaces: dropdown menus, popovers, dialogs, sheets,
and the command palette (all inherited from shadcn's defaults, `shadow-md`/
`shadow-lg`). Nothing in the persistent layout (sidebar, top nav, table,
cards) carries a shadow.

## Components used, and what was added

Reused as-is from shadcn's default primitives: Button, Input, Badge (with
added variants), Card, Dialog, AlertDialog, DropdownMenu, Select, Tabs,
Table, Command (palette), Popover, Sheet, Tooltip, Skeleton, Avatar,
Separator.

Project-specific composites, all under `components/shell/` unless noted:

- `empty-state.tsx` / `error-state.tsx` (under `components/`, not
  `shell/` — used outside the dashboard too) — a consistent icon + title +
  description + optional action pattern, used instead of ad hoc "no data"
  text.
- `app-shell.tsx`, `sidebar.tsx`, `top-nav.tsx`, `mobile-nav.tsx`,
  `org-switcher.tsx` (+ `create-org-dialog.tsx`), `breadcrumbs.tsx`,
  `command-palette.tsx`, `user-menu.tsx`, `notifications-menu.tsx`,
  `nav-items.tsx`, `shell-context.tsx`, `dashboard-shell-client.tsx` — see
  `docs/architecture/0002-auth-and-multi-tenancy.md` for the real routing
  and data-flow decisions (this section originally described a
  `[workspaceSlug]`-based shell with a repository switcher and demo data;
  Phase 2 replaced both with flat routes, an organization switcher, and
  real API data).

## Compact panel pattern (Phase 3)

Introduced on the repository overview page
(`(dashboard)/repositories/[repositoryId]/page.tsx`) for grouped list data
(recent commits, open pull requests, open issues) — the reference case for
the project's "no giant dashboard cards" rule:

- A metadata **strip**, not stat cards: repo language/stars/forks/branch/
  last-sync all sit inline in one bordered row
  (`flex flex-wrap items-center gap-x-4 ... rounded-lg border`), not as
  separate padded cards each showing one number.
- A **bordered list panel** (`OverviewSection` in that file) for each
  grouped collection: a small header (icon + title + count, not a large
  card title), then a `divide-y` list of dense rows — never a shadcn
  `Card` with its default padding for this kind of repeated-row content.
  Reuse this pattern (not `Card`) for any future page showing "N items of
  the same shape" (a status badge's `StatusBadge`-style component,
  `components/repositories/status-badge.tsx`, is the model for per-domain
  status badges — add one per new status enum rather than inlining
  variant-selection logic at each call site).
- Empty state within a panel is a single centered muted line
  (`emptyLabel`), not the full `EmptyState` component — `EmptyState` is
  for a whole page/section having nothing, not one column of a
  multi-column layout.

## Loading, empty, and error state convention

- **Loading**: route-segment `loading.tsx` renders skeletons shaped like
  the real layout (a heading-sized bar, a button-sized bar, N row-sized
  bars matching the table), never a centered spinner.
- **Empty**: `EmptyState` — icon in a circular muted background, a title
  stating what's missing, a one-sentence description of how to fix it, and
  an action button when one exists.
- **Error**: route-segment `error.tsx` (a client component, per Next.js
  convention) renders `ErrorState` with a retry button wired to Next's
  `reset()`.

## Phase 12 — professional product design audit

A full pass over every screen (landing, auth, dashboard, repository
overview, indexing, chat, architecture, PR intelligence, onboarding,
analytics, settings, 404) at desktop/laptop/tablet/mobile widths, looking
for AI-generated-looking visual patterns and concrete UX bugs rather than
a redesign — the token system, card radius, and border/shadow discipline
from earlier phases were already sound and are unchanged.

**Icon language.** `SparklesIcon` had spread to six files as the generic
marker for "this is AI-generated" (the Onboarding nav item, onboarding/PR
regenerate buttons, empty states, and a `animate-pulse` "queued" spinner)
— exactly the "AI sparkle icon" pattern the brief calls out. Replaced with
icons that describe what the control actually does: `BookOpenIcon` for the
onboarding feature identity (nav, command palette, repository quick-links),
`RefreshCwIcon` for every regenerate/re-analyze action (already the icon
"Sync now" used, so this now reads as one consistent verb across the app
instead of two), and a static `ClockIcon` for "queued/waiting to start"
states, freeing `RefreshCwIcon` + `animate-spin` to mean "actively
running" without colliding with the queued state's old pulsing sparkle.

**`Button` + `render` accessibility.** Composing `Button` with
`render={<Link .../>}` (used for every button-styled navigation link) was
tripping Base UI's dev-mode warning on every affected page, because the
underlying primitive defaults `nativeButton` to `true` and a `<Link>`
renders an `<a>`, not a `<button>`. Fixed once in `components/ui/button.tsx`
— it now defaults `nativeButton` to `false` whenever a `render` prop is
present — rather than patching every call site individually.

**Chart Y-axis clipping.** `commit-frequency-chart.tsx` and
`pr-throughput-chart.tsx` both hardcoded `<YAxis width={28} />`; a two-digit
tick (e.g. "12") is wider than that, and recharts' right-aligned tick text
was rendering partly outside the container, clipping the leading digit —
ticks silently read as "2, 9, 5, 3" instead of "12, 9, 6, 3, 0". The
working `repository-activity-chart.tsx` never set an explicit `width`; both
broken charts now follow that same pattern (auto-sized axis).

**Responsive fixes.** The repository overview header packed the title
block and an eight-item action/icon-button row into one `shrink-0` flex
row; on mobile, `shrink-0` squeezed the `min-w-0` title container to
near-zero width and the description wrapped one word per line. Now the
header is `flex-col` below `sm:` and the action row wraps
(`flex-wrap`) instead of forcing a single line.

**Breadcrumbs.** `security`/`usage`/`billing`/`general` were missing from
`SEGMENT_LABELS` (rendered as raw lowercase URL segments), and the
`repositories → /dashboard` href override applied unconditionally, so the
"Repositories" crumb under `/settings/repositories` silently linked to
`/dashboard` instead of staying on the settings tab. Both fixed —
labels added, and the override now only applies when `repositories` is
the first path segment.

**Landing page.** `app/page.tsx` was a Phase 1 placeholder (a bare
`<h1>`, a live API-health badge, two buttons). Replaced with a real,
restrained marketing page — a header, a one-sentence hero, and a feature
grid grounded entirely in what's actually built (chat, architecture
explorer, PR intelligence, onboarding, analytics — the same five items in
this repo's `README.md`), with no invented metrics, logos, or
testimonials. The API-health `SystemStatus` badge was removed from the
public page (it's an internal debug signal, not something a real product
shows visitors) and deleted as dead code once nothing referenced it.

**404 page.** There was no `app/not-found.tsx`, so an unmatched route fell
through to Next's unstyled default 404. Added one matching the app's
existing `ErrorState`-style tone (a small "404" label, a heading, a
one-line description, a button back to `/dashboard`).

**Framer Motion.** Added as a dependency and used narrowly, per the
brief's "only where useful" instruction:

- **Page transitions** — `components/shell/page-transition.tsx`, a small
  `AnimatePresence`/`motion.div` keyed by `usePathname()`, wrapping only
  `<main>`'s children in `app-shell.tsx` (sidebar/top nav never
  remount/transition).
- **Sidebar** — `nav-items.tsx`'s active item now has a `motion.div
  layoutId` pill that slides between items on navigation, instead of a
  static background swap. The desktop sidebar and the mobile sheet render
  the same `NavList`, so each is given a distinct `layoutGroupId` to keep
  their layout animations independent.
- **Loading states** — `components/fade-in.tsx`, a small settle-in wrapper
  applied where a skeleton is replaced by real content (repository
  overview, PR analysis panel) — not applied blanket-wide.
- **Hover** — a subtle `whileHover={{ y: -2 }}` lift on the landing page's
  feature cards (`components/landing/feature-grid.tsx`). Ordinary button/
  link hovers remain plain CSS (`hover:bg-...`), which is the right tool
  for a color/opacity change — framer-motion was reserved for hovers doing
  something a CSS transition can't.
- **Command palette** — deliberately *not* framer-motion: cmdk already
  exposes the list's measured height as `--cmdk-list-height`, so animating
  it is one `transition-[height]` Tailwind class on `CommandList`, not a
  new dependency.
- **Left alone, on purpose**: the existing CSS-based Dialog/AlertDialog/
  Sheet open/close transitions (`data-open:animate-in ...`). They already
  work, are consistent with each other, and the brief warns against
  animation that doesn't add anything — replacing a working transition
  with an equivalent framer-motion one would be exactly that.

## Known gaps carried forward

- No dark-mode toggle is wired up yet (tokens are fully defined and
  verified for both `:root` and `.dark`, but nothing sets the `.dark` class
  today — that's a small addition once real user settings exist).
- No `kbd`/tooltip shadcn components beyond what's used inline; if a richer
  shortcuts UI is needed later, add the dedicated `kbd` primitive rather
  than continuing to inline `<kbd>` styling.
- No frontend test runner configured — Phase 2's frontend was verified via
  ad hoc Playwright scripts, not a committed test suite (see ADR 0002's
  Testing section).
