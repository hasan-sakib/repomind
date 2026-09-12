# Built with the repo root as build context (see docker-compose.yml's
# `build.context: ..`) because `frontend` participates in the root pnpm
# workspace (pnpm-workspace.yaml) — installing from `frontend/` alone would
# resolve a different dependency tree than local dev / CI use.

FROM node:20-alpine AS base
RUN apk add --no-cache libc6-compat
RUN corepack enable

FROM base AS deps
WORKDIR /repo
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY frontend/package.json frontend/package.json
COPY packages packages
RUN pnpm install --frozen-lockfile

FROM base AS builder
WORKDIR /repo
COPY --from=deps /repo/node_modules ./node_modules
COPY --from=deps /repo/frontend/node_modules ./frontend/node_modules
COPY . .

# Baked in at build time — Next.js inlines NEXT_PUBLIC_* vars into the
# client bundle, so this must be set at `docker build`, not just at
# `docker run` (see docker-compose.yml's `build.args`).
ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN pnpm --filter frontend build

FROM base AS runtime
WORKDIR /app
ENV NODE_ENV=production \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs && adduser --system --uid 1001 nextjs

COPY --from=builder --chown=nextjs:nodejs /repo/frontend/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /repo/frontend/.next/static ./frontend/.next/static
COPY --from=builder --chown=nextjs:nodejs /repo/frontend/public ./frontend/public

USER nextjs
EXPOSE 3000

CMD ["node", "frontend/server.js"]
