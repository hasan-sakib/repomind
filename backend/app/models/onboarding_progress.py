import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin


class OnboardingProgress(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One row = one (user, item) marked complete for one repository's
    onboarding guide; `created_at` doubles as the completion timestamp.
    Marking an item incomplete deletes the row rather than storing a
    `completed: false` — there's nothing else worth keeping once
    unmarked. `item_key` is either "section:<slug>" (one of the guide's
    fixed sections) or "step:<n>" (a learning-path step index)."""

    __tablename__ = "onboarding_progress"
    __table_args__ = (
        UniqueConstraint(
            "repository_id", "user_id", "item_key", name="uq_onboarding_progress_repo_user_item"
        ),
    )

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    item_key: Mapped[str] = mapped_column(String(100), nullable=False)
