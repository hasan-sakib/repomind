# Deployment

## Target

- **Web** (`apps/web`): Vercel.
- **API** (`apps/api`) + **Postgres**: Railway or Fly.io.

This split was chosen for low cost and minimal ops overhead, appropriate for
a portfolio-stage SaaS product. See `docs/architecture/0001-foundation.md`.

## Current status

Not yet deployed — no environment has been provisioned. This section will be
filled in with concrete provisioning steps, environment variable checklists,
and CI/CD release flow once the app has a deployable vertical slice
(Phase 1).

## Environment variables

See `apps/api/.env.example` and `apps/web/.env.example` for the full list.
Never commit populated `.env` files — both are gitignored.
