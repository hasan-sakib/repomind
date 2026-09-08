import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.domain.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin
from app.domain.repository_status import RepositoryStatus

if TYPE_CHECKING:
    from app.domain.branch import Branch
    from app.domain.commit import Commit
    from app.domain.github_installation import GitHubInstallation
    from app.domain.issue import Issue
    from app.domain.pull_request import PullRequest
    from app.domain.repository_membership import RepositoryMembership


class Repository(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "repositories"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "github_repo_id", name="uq_repositories_org_github_repo"
        ),
    )

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    installation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("github_installations.id", ondelete="CASCADE"),
        nullable=False,
    )
    github_repo_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(300), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    stargazers_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    forks_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    default_branch: Mapped[str] = mapped_column(String(200), nullable=False)
    private: Mapped[bool] = mapped_column(Boolean, nullable=False)
    html_url: Mapped[str] = mapped_column(String(500), nullable=False)

    status: Mapped[RepositoryStatus] = mapped_column(
        Enum(
            RepositoryStatus,
            name="repository_status",
            native_enum=True,
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=False,
        default=RepositoryStatus.PENDING,
    )
    sync_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    installation: Mapped["GitHubInstallation"] = relationship(back_populates="repositories")
    memberships: Mapped[list["RepositoryMembership"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    branches: Mapped[list["Branch"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    commits: Mapped[list["Commit"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    pull_requests: Mapped[list["PullRequest"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
    issues: Mapped[list["Issue"]] = relationship(
        back_populates="repository", cascade="all, delete-orphan"
    )
