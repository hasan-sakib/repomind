import uuid
from datetime import datetime
from typing import TypedDict

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column
from app.models.pr_analysis_status import PRAnalysisStatus, PRRiskLevel


class AffectedComponentRecord(TypedDict):
    name: str
    file_paths: list[str]


class PotentialConcernRecord(TypedDict):
    description: str
    file_path: str | None
    symbol_name: str | None


class RecommendedTestRecord(TypedDict):
    description: str
    existing_test_file: str | None


class ChangedFileRecord(TypedDict):
    path: str
    status: str
    additions: int
    deletions: int


class PullRequestAnalysis(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One analysis run over one pull request, at a specific `head_sha`.

    Re-triggering analysis for a PR whose `head_sha` hasn't moved since the
    latest **succeeded** row returns that row instead of calling the LLM
    again (app/services/pr_analysis_service.py) — this table *is* the
    cache, not a layer in front of one. A new commit pushed to the PR
    changes its head_sha, which invalidates the cache the same way an
    indexing job re-runs when a repository's commit_sha moves (ADR 0004).

    Like AiRun (ADR 0005), a re-analysis creates a *new* row rather than
    overwriting the last one — history stays inspectable.
    """

    __tablename__ = "pull_request_analyses"

    pull_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("pull_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    head_sha: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[PRAnalysisStatus] = mapped_column(
        enum_column(PRAnalysisStatus, "pr_analysis_status"),
        nullable=False,
        default=PRAnalysisStatus.QUEUED,
    )
    risk_level: Mapped[PRRiskLevel | None] = mapped_column(
        enum_column(PRRiskLevel, "pr_risk_level"), nullable=True
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    affected_components: Mapped[list[AffectedComponentRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    potential_concerns: Mapped[list[PotentialConcernRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    recommended_tests: Mapped[list[RecommendedTestRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    files_analyzed: Mapped[list[ChangedFileRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# Re-exported so callers constructing JSONB payloads don't need to reach
# into this module directly for the TypedDict shapes.
__all__ = [
    "AffectedComponentRecord",
    "ChangedFileRecord",
    "PotentialConcernRecord",
    "PullRequestAnalysis",
    "RecommendedTestRecord",
]
