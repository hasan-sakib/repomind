"""Redis pub/sub-backed transport for the unified real-time event system
(app/events/types.py). One channel per organization — every
generated-artifact service publishes onto it (from either the FastAPI
process or the arq worker process, whichever runs the transition); the
WebSocket route (app/api/v1/routes/websocket.py) is the only subscriber.
See docs/architecture/0010-realtime-infrastructure.md.
"""

import logging
import uuid
from collections.abc import AsyncIterator

import redis.asyncio as redis

from app.core.config import get_settings
from app.events.types import RealtimeEvent

logger = logging.getLogger("repomind.events")

# Lazily created, one per process — cheap to hold open, and publish() is
# called from many different call sites that shouldn't each have to
# manage their own connection.
_publish_client: redis.Redis | None = None


def _channel(organization_id: uuid.UUID) -> str:
    return f"realtime:org:{organization_id}"


def _get_publish_client() -> redis.Redis:
    global _publish_client
    if _publish_client is None:
        # redis-py ships py.typed but from_url() itself has no return
        # annotation, so mypy --strict sees it as untyped regardless.
        _publish_client = redis.from_url(get_settings().redis_url)  # type: ignore[no-untyped-call]
    return _publish_client


async def publish_event(event: RealtimeEvent) -> None:
    """Fire-and-forget: a real-time push is a convenience on top of state
    that's already durably committed to Postgres by the time this runs
    (see every call site in app/services/) — a transient Redis hiccup
    should never fail the caller's actual state transition, so failures
    are logged, not raised."""
    try:
        client = _get_publish_client()
        await client.publish(_channel(event.organization_id), event.model_dump_json())
    except Exception:  # noqa: BLE001 — see docstring
        logger.exception("Failed to publish realtime event %s (%s)", event.id, event.category)


async def subscribe(organization_id: uuid.UUID) -> AsyncIterator[RealtimeEvent]:
    """One dedicated Redis connection per subscriber — pub/sub connections
    can't multiplex regular commands, so each open WebSocket gets its own.
    Always drive this via `async for` so cancellation/GeneratorExit runs
    the `finally` below and releases the connection; the WebSocket route
    relies on exactly that to avoid leaking a connection per dropped
    client."""
    client = redis.from_url(get_settings().redis_url)  # type: ignore[no-untyped-call]
    pubsub = client.pubsub()
    channel = _channel(organization_id)
    await pubsub.subscribe(channel)
    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                yield RealtimeEvent.model_validate_json(message["data"])
            except Exception:  # noqa: BLE001 — one bad message must not kill the subscription
                logger.exception("Failed to parse realtime event from channel %s", channel)
    finally:
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await client.aclose()
