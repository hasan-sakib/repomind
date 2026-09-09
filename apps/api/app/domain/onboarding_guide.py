import uuid
from datetime import datetime
from typing import TypedDict

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.domain.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column
from app.domain.onboarding_status import OnboardingGuideStatus


class ImportantModuleRecord(TypedDict):
    name: str
    path: str
    kind: str
    file_count: int


class RecommendedFileRecord(TypedDict):
    path: str
    label: str
    kind: str
    dependents_count: int


class DependencyRecord(TypedDict):
    name: str
    version: str | None
    ecosystem: str


class SetupStepRecord(TypedDict):
    order: int
    description: str
    command: str | None
    detected_from: str


class DatabaseStructureEntryRecord(TypedDict):
    path: str
    class_name: str
    symbol_type: str


class LearningPathStepRecord(TypedDict):
    step: int
    label: str
    path: str | None
    reason: str


class FaqEntryRecord(TypedDict):
    question: str
    answer: str
    file_paths: list[str]


class OnboardingGuide(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One onboarding-guide generation for one repository, at a specific
    `commit_sha` (the latest **succeeded** IndexingJob's commit_sha at
    generation time — app/services/onboarding_service.py). Re-triggering
    generation for a repository that hasn't been re-indexed since returns
    the cached succeeded row instead of regenerating — this table *is*
    the cache, the same design as PullRequestAnalysis (ADR 0007).

    Most fields here are deterministic, computed from already-indexed
    data with no LLM involved (important_modules, recommended_files,
    key_dependencies, dev_setup_steps, database_structure, learning_path)
    — only architecture_overview, common_workflows, authentication_flow,
    and faq are AI-generated, and only when there's real grounding data to
    generate them from (authentication_flow stays null if no auth-related
    files were found at all, rather than inventing one). See
    docs/architecture/0008-developer-onboarding.md.
    """

    __tablename__ = "onboarding_guides"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    commit_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[OnboardingGuideStatus] = mapped_column(
        enum_column(OnboardingGuideStatus, "onboarding_guide_status"),
        nullable=False,
        default=OnboardingGuideStatus.QUEUED,
    )

    # AI-generated narrative sections — nullable until generation succeeds
    # (authentication_flow stays null forever if no auth was detected).
    architecture_overview: Mapped[str | None] = mapped_column(Text, nullable=True)
    common_workflows: Mapped[str | None] = mapped_column(Text, nullable=True)
    authentication_flow: Mapped[str | None] = mapped_column(Text, nullable=True)
    faq: Mapped[list[FaqEntryRecord]] = mapped_column(JSONB, nullable=False, default=list)

    # Deterministic sections — no LLM involved.
    important_modules: Mapped[list[ImportantModuleRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    recommended_files: Mapped[list[RecommendedFileRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    key_dependencies: Mapped[list[DependencyRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    dev_setup_steps: Mapped[list[SetupStepRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    database_structure: Mapped[list[DatabaseStructureEntryRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    learning_path: Mapped[list[LearningPathStepRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
