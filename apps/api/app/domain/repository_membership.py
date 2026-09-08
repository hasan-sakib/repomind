import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.domain.repository import Repository
    from app.domain.user import User


class RepositoryMembership(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Who can see a connected repository. Auto-maintained (not manually
    managed in this phase): every current organization member gets a row
    when a repository is connected, and a new organization member gets a
    row for every existing repository in that organization — see
    app/services/repository_service.py. Exists as real infrastructure for
    future fine-grained per-repository access control, not just a stub."""

    __tablename__ = "repository_memberships"
    __table_args__ = (
        UniqueConstraint("repository_id", "user_id", name="uq_repository_memberships_repo_user"),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    repository: Mapped["Repository"] = relationship(back_populates="memberships")
    user: Mapped["User"] = relationship()
