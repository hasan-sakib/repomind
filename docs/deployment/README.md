# Deployment

## Target

- **Web** (`frontend`): Vercel.
- **API + worker** (`backend`): Render or Railway.
- **Database**: Supabase PostgreSQL.
- **Redis**: Upstash.

See **`docs/deployment/ci-cd.md`** for the full plan: CI/CD workflows,
environments (development/staging/production), why this stack, the
environment-variable reference, and branch protection recommendations.
`docs/deployment/deployment.md` covers earlier Fly.io-specific groundwork,
most of which (the CORS/cookie same-site constraint, migration safety
rules, observability approach) still applies regardless of which platform
runs the API — see the superseding note at its top for exactly what
changed.

## Current status

Not yet deployed — no environment has been provisioned. `ci-cd.md` is the
plan to provision against.

## CI

Three GitHub Actions workflows run on every push/PR:
`.github/workflows/frontend-ci.yml`, `backend-ci.yml`, and `security.yml`
— see `docs/deployment/ci-cd.md` for what each one does.

## Environment variables

See `backend/.env.example` (a complete, field-by-field mirror of
`app/core/config.py`) and `frontend/.env.example` for the full list.
Never commit populated `.env` files — both are gitignored. See
`docs/deployment/ci-cd.md`'s "Environment variables" section for where
each one actually lives per environment.
