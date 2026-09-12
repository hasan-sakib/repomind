import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.repository import Repository


class GitHubInstallation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "github_installations"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    github_installation_id: Mapped[int] = mapped_column(unique=True, nullable=False, index=True)
    account_login: Mapped[str] = mapped_column(String(200), nullable=False)
    account_type: Mapped[str] = mapped_column(String(20), nullable=False)

    # passive_deletes=True: let the DB's ON DELETE CASCADE (on
    # Repository.installation_id) remove child rows directly. Without it,
    # SQLAlchemy's default ORM-level cascade instead tries to UPDATE each
    # child's FK to NULL before the parent delete, which fails outright
    # since that column is NOT NULL — deleting an installation must
    # actually remove its repositories, never orphan them.
    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="installation", passive_deletes=True
    )
