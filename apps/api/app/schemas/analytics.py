import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.domain.analytics_snapshot import AnalyticsSnapshot
from app.domain.analytics_status import AnalyticsSnapshotStatus


class DailyCommitPublic(BaseModel):
    date: str
    login: str | None
    name: str | None
    count: int


class DailyPRIssuePublic(BaseModel):
    date: str
    prs_opened: int
    prs_merged: int
    prs_closed: int
    issues_opened: int


class ContributorActivityPublic(BaseModel):
    login: str | None
    name: str | None
    commit_count: int
    pr_count: int


class PRCycleTimeSamplePublic(BaseModel):
    number: int
    title: str
    html_url: str
    hours: float
    merged_at: str | None


class StaleIssuePublic(BaseModel):
    number: int
    title: str
    html_url: str
    age_days: int


class FileHotspotPublic(BaseModel):
    path: str
    kind: str
    change_count: int
    dependents_count: int


class ArchitectureHotspotPublic(BaseModel):
    package_path: str
    kind: str
    change_count: int
    file_count: int


class AnalyticsSnapshotPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: AnalyticsSnapshotStatus
    synced_through: datetime | None
    daily_commit_activity: list[DailyCommitPublic]
    daily_pr_issue_activity: list[DailyPRIssuePublic]
    contributor_activity: list[ContributorActivityPublic]
    median_cycle_time_hours: float | None
    pr_cycle_time_samples: list[PRCycleTimeSamplePublic]
    open_issues_total: int
    stale_issues: list[StaleIssuePublic]
    file_hotspots: list[FileHotspotPublic]
    architecture_hotspots: list[ArchitectureHotspotPublic]
    commit_sample_size: int
    hotspot_commit_sample_size: int
    pr_sample_size: int
    error: str | None
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None

    @classmethod
    def from_snapshot(cls, snapshot: AnalyticsSnapshot) -> "AnalyticsSnapshotPublic":
        return cls.model_validate(snapshot)
