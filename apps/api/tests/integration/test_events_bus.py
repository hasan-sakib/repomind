"""Tests the Redis pub/sub transport underneath the unified real-time
event system directly (app/events/bus.py), independent of the WebSocket
route — see tests/integration/test_websocket_route.py for the route
itself. Requires a real Redis connection (the same one the FastAPI app's
arq pool already requires at startup)."""

import asyncio
import contextlib
import uuid
from datetime import UTC, datetime

import pytest

from app.events.bus import publish_event, subscribe
from app.events.types import EventCategory, RealtimeEvent

pytestmark = pytest.mark.asyncio


def _notification(organization_id: uuid.UUID, title: str) -> RealtimeEvent:
    return RealtimeEvent(
        id=uuid.uuid4(),
        category=EventCategory.NOTIFICATION,
        organization_id=organization_id,
        title=title,
        level="info",
        at=datetime.now(UTC),
    )


async def test_publish_and_subscribe_round_trip() -> None:
    organization_id = uuid.uuid4()
    subscription = subscribe(organization_id)
    try:
        first = asyncio.ensure_future(anext(subscription))
        # Give the SUBSCRIBE command a moment to land before publishing —
        # otherwise the publish could fire before Redis has registered
        # this connection as a subscriber to the channel.
        await asyncio.sleep(0.2)

        event = _notification(organization_id, "Test notification")
        await publish_event(event)

        received = await asyncio.wait_for(first, timeout=2)
        assert received.id == event.id
        assert received.category == EventCategory.NOTIFICATION
        assert received.title == "Test notification"
    finally:
        await subscription.aclose()


async def test_subscribe_only_receives_events_for_its_own_organization() -> None:
    organization_id = uuid.uuid4()
    other_organization_id = uuid.uuid4()
    subscription = subscribe(organization_id)
    try:
        pending_next = asyncio.ensure_future(anext(subscription))
        await asyncio.sleep(0.2)

        await publish_event(_notification(other_organization_id, "Not for you"))
        _, pending = await asyncio.wait({pending_next}, timeout=0.5)
        assert pending_next in pending, "received an event meant for a different organization"

        await publish_event(_notification(organization_id, "For you"))
        done, _ = await asyncio.wait({pending_next}, timeout=2)
        assert pending_next in done
        assert pending_next.result().title == "For you"
    finally:
        await subscription.aclose()


async def test_subscribe_cleans_up_its_redis_connection_on_cancel_and_aclose() -> None:
    """The WebSocket route relies on this exact cleanup path (driving
    `subscribe` via `async for` inside a task it cancels on disconnect) to
    avoid leaking a Redis connection per dropped client."""
    organization_id = uuid.uuid4()
    subscription = subscribe(organization_id)
    pending_next = asyncio.ensure_future(anext(subscription))
    await asyncio.sleep(0.2)  # let it actually reach pubsub.subscribe()/listen()

    pending_next.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await pending_next

    # Must complete without raising — the generator's `finally` unsubscribes
    # and closes its Redis client even though it was cancelled mid-listen.
    await subscription.aclose()
