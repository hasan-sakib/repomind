import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column


class UUIDPrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


class CreatedAtMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


def enum_column[E: enum.Enum](enum_cls: type[E], name: str) -> Enum:
    """A native Postgres enum column storing each member's `.value` (e.g.
    "owner"), not its Python name (e.g. "OWNER") — SQLAlchemy's `Enum`
    stores the name by default, which reads oddly from outside the ORM and
    doesn't match every other place these values appear (API JSON, docs)."""
    return Enum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda ec: [member.value for member in ec],
    )
