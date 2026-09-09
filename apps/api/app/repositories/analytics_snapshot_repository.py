import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics_snapshot import (
    AnalyticsSnapshot,
    ArchitectureHotspotRecord,
    ContributorActivityRecord,
    DailyCommitRecord,
    DailyPRIssueRecord,
    FileHotspotRecord,
    PRCycleTimeSampleRecord,
    StaleIssueRecord,
)
from app.domain.analytics_status import AnalyticsSnapshotStatus

_ACTIVE_STATUSES = (AnalyticsSnapshotStatus.QUEUED, AnalyticsSnapshotStatus.RUNNING)


async def get(db: AsyncSession, snapshot_id: uuid.UUID) -> AnalyticsSnapshot | None:
    return await db.get(AnalyticsSnapshot, snapshot_id)


async def get_latest_for_repository(
    db: AsyncSession, repository_id: uuid.UUID
) -> AnalyticsSnapshot | None:
    result = await db.execute(
        select(AnalyticsSnapshot)
        .where(AnalyticsSnapshot.repository_id == repository_id)
        .order_by(AnalyticsSnapshot.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def is_active(snapshot: AnalyticsSnapshot) -> bool:
    return snapshot.status in _ACTIVE_STATUSES


def create(db: AsyncSession, *, repository_id: uuid.UUID) -> AnalyticsSnapshot:
    snapshot = AnalyticsSnapshot(repository_id=repository_id, status=AnalyticsSnapshotStatus.QUEUED)
    db.add(snapshot)
    return snapshot


def mark_running(snapshot: AnalyticsSnapshot, *, started_at: datetime) -> None:
    snapshot.status = AnalyticsSnapshotStatus.RUNNING
    snapshot.started_at = started_at


def mark_succeeded(
    snapshot: AnalyticsSnapshot,
    *,
    finished_at: datetime,
    synced_through: datetime | None,
    daily_commit_activity: list[DailyCommitRecord],
    daily_pr_issue_activity: list[DailyPRIssueRecord],
    contributor_activity: list[ContributorActivityRecord],
    median_cycle_time_hours: float | None,
    pr_cycle_time_samples: list[PRCycleTimeSampleRecord],
    open_issues_total: int,
    stale_issues: list[StaleIssueRecord],
    file_hotspots: list[FileHotspotRecord],
    architecture_hotspots: list[ArchitectureHotspotRecord],
    commit_sample_size: int,
    hotspot_commit_sample_size: int,
    pr_sample_size: int,
) -> None:
    snapshot.status = AnalyticsSnapshotStatus.SUCCEEDED
    snapshot.finished_at = finished_at
    snapshot.synced_through = synced_through
    snapshot.daily_commit_activity = daily_commit_activity
    snapshot.daily_pr_issue_activity = daily_pr_issue_activity
    snapshot.contributor_activity = contributor_activity
    snapshot.median_cycle_time_hours = median_cycle_time_hours
    snapshot.pr_cycle_time_samples = pr_cycle_time_samples
    snapshot.open_issues_total = open_issues_total
    snapshot.stale_issues = stale_issues
    snapshot.file_hotspots = file_hotspots
    snapshot.architecture_hotspots = architecture_hotspots
    snapshot.commit_sample_size = commit_sample_size
    snapshot.hotspot_commit_sample_size = hotspot_commit_sample_size
    snapshot.pr_sample_size = pr_sample_size


def mark_failed(snapshot: AnalyticsSnapshot, *, finished_at: datetime, error: str) -> None:
    snapshot.status = AnalyticsSnapshotStatus.FAILED
    snapshot.finished_at = finished_at
    snapshot.error = error
