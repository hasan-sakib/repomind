from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.webhook_event import WebhookEvent


async def get_by_delivery_id(db: AsyncSession, github_delivery_id: str) -> WebhookEvent | None:
    result = await db.execute(
        select(WebhookEvent).where(WebhookEvent.github_delivery_id == github_delivery_id)
    )
    return result.scalar_one_or_none()


def create(
    db: AsyncSession, *, github_delivery_id: str, event_type: str, payload: dict[str, object]
) -> WebhookEvent:
    event = WebhookEvent(
        github_delivery_id=github_delivery_id,
        event_type=event_type,
        payload=payload,
        status="received",
    )
    db.add(event)
    return event


def mark_processed(event: WebhookEvent, *, at: datetime) -> None:
    event.status = "processed"
    event.processed_at = at


def mark_failed(event: WebhookEvent, *, error: str, at: datetime) -> None:
    event.status = "failed"
    event.error = error
    event.processed_at = at
