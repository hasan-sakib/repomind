from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class WebhookEvent(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One row per GitHub webhook delivery. `github_delivery_id` (the
    `X-GitHub-Delivery` header) is GitHub's own idempotency key — its
    uniqueness constraint is what makes webhook processing idempotent: a
    redelivered event hits this constraint and is skipped rather than
    reprocessed. See app/services/webhook_service.py."""

    __tablename__ = "webhook_events"

    github_delivery_id: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    payload: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="received")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
