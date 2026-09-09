"""Convenience wrappers around app/events/bus.py's `publish_event` — the
only two shapes any service needs to produce: a state-sync event (fresh
Public-schema data for a resource) or a notification (a short message for
toast/notification-center display). Keeps this package free of any
import on app/domain or app/schemas — callers pass in already-serialized
data, so the event bus stays a generic transport."""

import uuid
from datetime import UTC, datetime
from typing import Any

from app.events.bus import publish_event
from app.events.types import EventCategory, NotificationLevel, RealtimeEvent


async def publish_state(
    *,
    category: EventCategory,
    organization_id: uuid.UUID,
    repository_id: uuid.UUID | None,
    resource: str,
    data: dict[str, Any],
) -> None:
    await publish_event(
        RealtimeEvent(
            id=uuid.uuid4(),
            category=category,
            organization_id=organization_id,
            repository_id=repository_id,
            resource=resource,
            data=data,
            at=datetime.now(UTC),
        )
    )


async def publish_notification(
    *,
    organization_id: uuid.UUID,
    repository_id: uuid.UUID | None = None,
    title: str,
    level: NotificationLevel = "info",
) -> None:
    await publish_event(
        RealtimeEvent(
            id=uuid.uuid4(),
            category=EventCategory.NOTIFICATION,
            organization_id=organization_id,
            repository_id=repository_id,
            title=title,
            level=level,
            at=datetime.now(UTC),
        )
    )
