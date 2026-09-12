import uuid
from datetime import datetime
from typing import TypedDict

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.analytics_status import AnalyticsSnapshotStatus
from app.models.mixins import CreatedAtMixin, UUIDPrimaryKeyMixin, enum_column


class DailyCommitRecord(TypedDict):
    date: str  # ISO date (day bucket)
    login: str | None
    name: str | None
    count: int


class DailyPRIssueRecord(TypedDict):
    date: str
    prs_opened: int
    prs_merged: int
    prs_closed: int
    issues_opened: int


class ContributorActivityRecord(TypedDict):
    login: str | None
    name: str | None
    commit_count: int
    pr_count: int


class PRCycleTimeSampleRecord(TypedDict):
    number: int
    title: str
    html_url: str
    hours: float
    merged_at: str | None


class StaleIssueRecord(TypedDict):
    number: int
    title: str
    html_url: str
    age_days: int


class FileHotspotRecord(TypedDict):
    path: str
    kind: str
    change_count: int
    dependents_count: int


class ArchitectureHotspotRecord(TypedDict):
    package_path: str
    kind: str
    change_count: int
    file_count: int


class AnalyticsSnapshot(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One generated analytics snapshot for one repository. Unlike
    PullRequestAnalysis/OnboardingGuide (ADR 0007/0008), this is
    deliberately **not** auto-invalidated when the repository re-syncs —
    generation makes on the order of a hundred GitHub API calls (a deep
    commit history plus one call per commit for its file diff, to compute
    hotspots — see app/analytics/), so re-triggering happens only on an
    explicit "Regenerate", never silently. `synced_through` records the
    repository's `last_synced_at` at generation time purely so the UI can
    tell the viewer how fresh the underlying data is.

    No LLM is involved anywhere in this table — every field is a computed
    aggregate over real GitHub data. See
    docs/architecture/0009-engineering-analytics.md.
    """

    __tablename__ = "analytics_snapshots"

    repository_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("repositories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[AnalyticsSnapshotStatus] = mapped_column(
        enum_column(AnalyticsSnapshotStatus, "analytics_snapshot_status"),
        nullable=False,
        default=AnalyticsSnapshotStatus.QUEUED,
    )
    synced_through: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    daily_commit_activity: Mapped[list[DailyCommitRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    daily_pr_issue_activity: Mapped[list[DailyPRIssueRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    contributor_activity: Mapped[list[ContributorActivityRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    median_cycle_time_hours: Mapped[float | None] = mapped_column(Float, nullable=True)
    pr_cycle_time_samples: Mapped[list[PRCycleTimeSampleRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    open_issues_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    stale_issues: Mapped[list[StaleIssueRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    file_hotspots: Mapped[list[FileHotspotRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    architecture_hotspots: Mapped[list[ArchitectureHotspotRecord]] = mapped_column(
        JSONB, nullable=False, default=list
    )

    commit_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    hotspot_commit_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pr_sample_size: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
