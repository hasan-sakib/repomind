# ADR 0011: SaaS Management — Plans, Entitlements, and Organization Administration

**Status:** Accepted — implemented
**Date:** 2026-09-12

## What was built

- `app/billing/` — the centralized entitlement system:
  - `plans.py` — `Plan` (free/pro/team), `PlanLimits` (max repositories,
    max members — `None` means unlimited), and `PLAN_LIMITS`, the single
    table every limit is read from.
  - `entitlements.py` — `ensure_can_add_repository` /
    `ensure_can_add_member`, the only two functions in the codebase that
    compare a count against a plan limit. Every call site that creates a
    metered resource calls one of these instead of touching
    `organization.plan` or a hardcoded number itself.
  - `usage.py` — read-only usage observability: the same repository/member
    counts entitlements checks, plus AI token consumption and
    generation-run counts aggregated across a repository's conversations,
    PR analyses, onboarding guides, and analytics snapshots.
  - `provider.py` / `factory.py` — `BillingProvider`, an abstraction with
    the same shape as `AIProvider`/`EmbeddingProvider` (app/ai/), and
    `NullBillingProvider`, the only implementation today.
- `Organization.plan` (new column, defaults to Free) and `ApiKey` (new
  table) — see the migration for the Postgres-enum-on-an-existing-table
  wrinkle this needed.
- Wired into the two places that actually create metered resources:
  `repository_service.connect_repository` (repository limit) and
  `organization_service.add_member` (member limit) — both now call
  `entitlements.ensure_can_add_repository`/`ensure_can_add_member` before
  doing anything else, and both surface a `402 plan_limit_reached` error
  the frontend already knows how to show.
- Organization administration: `PATCH /organizations/{id}` (rename,
  admin+), `POST /organizations/{id}/plan` (the interim, no-billing-
  provider way to change plans — owner-only), `GET .../usage`, `GET
  .../billing` (the Free/Pro/Team catalog plus whether a real billing
  provider is configured), `GET .../audit-logs` (admin+ — `AuditLog` and
  its write side already existed from ADR 0002; this phase adds the read
  side).
- API keys (`app/models/api_key.py`, `app/services/api_key_service.py`,
  `app/api/v1/routes/api_keys.py`) — organization-scoped, role-capped
  credentials. Only a SHA-256 hash is ever stored; the plaintext secret
  is returned exactly once, at creation.
- Repository permissions: `RepositoryMembership` (ADR 0002) already
  existed and was already documented as "real infrastructure for future
  fine-grained access control" — this phase adds the manual override
  it was built for: `grant_repository_access`/`revoke_repository_access`
  let an admin add or remove a specific member's access to a specific
  repository, independent of the existing auto-grant-on-connect/
  auto-grant-on-join behavior (which is unchanged).
- Frontend: `/settings/general` (moved from `/settings`, now with an
  organization-rename form), `/settings/members` (unchanged, now also
  handles `plan_limit_reached`), `/settings/repositories` (new — per-
  repository access management), `/settings/security` (new — API keys
  and the audit log), `/settings/usage` (new — quota bars plus activity
  counts), `/settings/billing` (new — plan catalog and the interim
  plan-switch control).

## Decisions and why

### One centralized entitlement module, not scattered plan checks

The brief's explicit instruction — "do not hardcode plan checks
throughout the application" — is why `app/billing/entitlements.py`
exists as its own module rather than, say, an `if organization.plan ==
"free": ...` inline in `repository_service.py`. Every limit (today: two)
is defined once in `PLAN_LIMITS` and enforced through exactly one
function per resource type. Adding a third limited resource later means
adding one field to `PlanLimits` and one `ensure_can_add_X` function —
not hunting down every place that resource gets created.

### API keys authenticate through one dependency, not every route

`require_repository_access` (`app/api/deps.py`) now accepts either the
session cookie or an `Authorization: Bearer <key>` header — resolved
into a `Repository` either way. Only this dependency was extended, which
means only the repository-scoped GET/read routes (overview, branches,
commits, PRs, issues, indexing jobs) and the two indexing/sync triggers
that use it accept API-key auth today; routes that separately depend on
`get_current_user` for a real `User` (e.g. disconnecting a repository)
still require a session. This is a deliberate, bounded scope — the
brief asks for API keys as a management feature, not for a complete
parallel auth system covering every endpoint — and it's a real,
functioning integration end to end (`tests/integration/test_api_keys.py`
creates a key over HTTP and uses it to authenticate a cookie-free
request), not a CRUD-only stub.

One consequence worth naming: mutating routes gated behind
`require_csrf_header` still require that header regardless of auth
method, even though CSRF protection is specifically about cookie-borne
requests and doesn't apply to a bearer token. Since the only routes that
currently accept API-key auth are read-only, this doesn't bite in
practice; it would need addressing before extending API-key auth to a
mutating route.

### API keys hash with SHA-256, not bcrypt/argon2

A password hash is deliberately slow to resist offline brute-forcing a
low-entropy, human-chosen secret. An API key's secret is a 32-byte
`secrets.token_urlsafe` value — brute-forcing it is already infeasible
regardless of hash speed — so a fast, collision-resistant hash is the
right tool: it makes the lookup-by-hash query on every authenticated
request cheap, with no security given up for it.

### Repository permissions extend the existing table, not a new visibility enum

`RepositoryMembership` already governs exactly one thing — whether a
user can see a repository — and was already auto-maintained on connect
and on joining an organization. Rather than adding a `Repository.
visibility` enum (organization-wide vs. restricted) and a parallel code
path, this phase adds `grant_repository_access`/`revoke_repository_access`
as direct, admin-gated mutations of the same table the existing
auto-grant logic already writes to. A newly connected repository or a
newly added member still gets auto-granted access exactly as before;
an admin can additionally revoke or restore any individual member's
access afterward. This is the smaller change and the one the model's
own docstring already anticipated.

### Billing changes hands are manual today, and the UI says so

`NullBillingProvider` is the only `BillingProvider` implementation —
there is no Stripe/Paddle integration in this phase, per the brief's
"billing integration can remain optional." `POST /organizations/{id}/
plan` is the interim mechanism: owner-only, takes effect immediately,
no payment step. The billing page's own banner states this plainly
("no payment provider is connected yet... this is a temporary stand-in")
rather than presenting a manual toggle as if it were real checkout —
the same "don't quietly substitute something narrower for what was
asked" discipline as ADR 0009's PR-cycle-time footnote. Wiring up a real
provider later means implementing `BillingProvider` once and switching
`settings.billing_provider` — no route or entitlement-check code needs
to change, since they already depend only on the abstraction.

### Usage tracking observes the same numbers entitlements enforces, plus a preview of what a real meter would need

`UsageSummary` reuses `repository_repository.count_for_organization`/
`organization_member_repository.count_for_organization` — the exact
counts `entitlements.py` checks against — so the usage page can never
disagree with what's actually being enforced. AI token consumption and
generation-run counts are included even though nothing limits them
today, because they're the first things a real usage-based billing
metric would need, and they were already sitting in the database
(`AiRun`/`PullRequestAnalysis`/`OnboardingGuide` all already recorded
token counts from ADR 0005/0007/0008) — surfacing them costs a handful
of aggregate queries, not a new tracking system.

## What this phase does not do

- No pending-invitation flow for members who don't have an account yet
  — `add_member` still requires the invitee to already be a registered
  user, unchanged from ADR 0002.
- No per-repository read/write permission levels — repository
  permissions in this phase are visibility only (can see it or not), not
  a finer-grained ACL.
- No real payment integration, webhooks, or invoicing — see
  `NullBillingProvider` above.
- No rate limiting or per-key scopes/expiration beyond role and
  revocation — an API key acts at a fixed role with no expiry date; this
  covers the brief's ask without building a feature no one requested yet.
- API-key auth is not wired into every route — see the CSRF caveat and
  scope decision above.
