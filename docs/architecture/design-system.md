# Design System

This documents the actual token and component decisions implemented in
`apps/web` for Phase 1 (application shell). It supersedes any tokens
shadcn's `init` scaffolded by default — see `apps/web/src/app/globals.css`
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
