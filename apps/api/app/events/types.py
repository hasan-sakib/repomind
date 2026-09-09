import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel


class EventCategory(StrEnum):
    INDEXING = "indexing"
    SYNC = "sync"
    WEBHOOK = "webhook"
    AI_GENERATION = "ai_generation"
    NOTIFICATION = "notification"


NotificationLevel = Literal["info", "success", "error"]


class RealtimeEvent(BaseModel):
    """One message on an organization's real-time channel (see
    app/events/bus.py). For the four state-sync categories (indexing,
    sync, webhook, ai_generation), `resource`/`data` carry a fresh
    Public-schema-shaped payload — the same shape the equivalent REST
    endpoint returns — so the frontend can write it straight into its
    React Query cache instead of refetching. `title`/`level` are set only
    for `category=notification`, a distinct summary event fired alongside
    the state event at terminal (succeeded/failed) transitions, meant for
    toast/notification-center display rather than cache updates. See
    docs/architecture/0010-realtime-infrastructure.md.
    """

    id: uuid.UUID
    category: EventCategory
    organization_id: uuid.UUID
    repository_id: uuid.UUID | None = None
    resource: str | None = None
    data: dict[str, Any] | None = None
    title: str | None = None
    level: NotificationLevel | None = None
    at: datetime
