"""Per-IP fixed-window rate limiting for unauthenticated, abuse-prone
endpoints (login, register, refresh, password reset, email verification) —
see docs/architecture/security.md. Nothing else in the app was rate-limited
before this; these are the routes a real attacker would actually script
against (credential stuffing, account enumeration, email bombing), not a
general-purpose API gateway.

Backed by Redis (already a hard dependency of this app — see
app/events/bus.py for the same `redis.asyncio` client pattern) so the limit
is shared across every API process, not per-process in memory."""

import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as redis
from fastapi import Request

from app.core.config import get_settings
from app.services.exceptions import RateLimitExceededError

logger = logging.getLogger("repomind.rate_limit")

RATE_LIMIT_KEY_PREFIX = "ratelimit:"

_client: redis.Redis | None = None


def _get_client() -> redis.Redis:
    global _client
    if _client is None:
        _client = redis.from_url(get_settings().redis_url)  # type: ignore[no-untyped-call]
    return _client


def _client_ip(request: Request) -> str:
    # No trusted-proxy/X-Forwarded-For handling: this app isn't deployed
    # behind a proxy that sets it today (see docs/deployment/deployment.md).
    # If one is added later, this must read the proxy's header instead —
    # otherwise every request would report the proxy's own IP and share
    # one rate-limit bucket.
    return request.client.host if request.client else "unknown"


async def _increment_and_check(*, key: str, max_requests: int, window_seconds: int) -> bool:
    """Returns True if the request is allowed. A plain INCR+EXPIRE fixed
    window (not a sliding log) — good enough for "stop a scripted burst",
    not meant to be exact at the boundary."""
    client = _get_client()
    count = int(await client.incr(key))
    if count == 1:
        await client.expire(key, window_seconds)
    return count <= max_requests


def rate_limit(
    *, name: str, max_requests: int, window_seconds: int = 60
) -> Callable[[Request], Awaitable[None]]:
    """Dependency factory. `name` scopes the Redis key to this endpoint so
    separate routes don't share a bucket."""

    async def dependency(request: Request) -> None:
        key = f"{RATE_LIMIT_KEY_PREFIX}{name}:{_client_ip(request)}"
        try:
            allowed = await _increment_and_check(
                key=key, max_requests=max_requests, window_seconds=window_seconds
            )
        except redis.RedisError:
            # Fail open: Redis being briefly unavailable shouldn't take
            # down login/registration entirely — it already isn't the
            # only defense (see account lockout / password hashing cost).
            logger.warning("rate limit check failed for %s; allowing request", name)
            return
        if not allowed:
            raise RateLimitExceededError("Too many requests — try again shortly")

    return dependency


async def reset_all_rate_limits() -> None:
    """Test-only helper: clears every rate-limit counter. Without this,
    Redis state (unlike Postgres) isn't reset between tests, so an earlier
    test's requests would count against a later test's limit — see
    tests/conftest.py."""
    client = _get_client()
    cursor = 0
    while True:
        cursor, keys = await client.scan(cursor, match=f"{RATE_LIMIT_KEY_PREFIX}*", count=500)
        if keys:
            await client.delete(*keys)
        if cursor == 0:
            break
