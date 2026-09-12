import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.role import Role

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User


class ApiKey(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """A programmatic credential scoped to one organization, acting at a
    fixed role (never above its creator's role at issue time — see
    app/services/api_key_service.py). Only `key_hash` is ever stored; the
    plaintext secret is shown to the creator exactly once, at creation.
    See docs/architecture/0011-saas-management.md for why this checks
    against a fast SHA-256 hash rather than a slow password hash: the
    secret itself is a high-entropy random token, not a user-chosen
    password, so there's nothing a rainbow table or brute force gains by
    attacking the hash offline."""

    __tablename__ = "api_keys"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    # First 12 chars of the secret (after the "rm_" prefix) — enough for a
    # user to recognize which key is which in a list, never enough to be
    # useful to an attacker.
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    role: Mapped[Role] = mapped_column(enum_column(Role, "api_key_role"), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    organization: Mapped["Organization"] = relationship()
    created_by: Mapped["User | None"] = relationship()
