import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.pr_analysis_status import PRAnalysisStatus, PRRiskLevel
from app.models.pull_request_analysis import (
    AffectedComponentRecord,
    ChangedFileRecord,
    PotentialConcernRecord,
    PullRequestAnalysis,
    RecommendedTestRecord,
)

_ACTIVE_STATUSES = (PRAnalysisStatus.QUEUED, PRAnalysisStatus.RUNNING)


async def get(db: AsyncSession, analysis_id: uuid.UUID) -> PullRequestAnalysis | None:
    return await db.get(PullRequestAnalysis, analysis_id)


async def get_latest_for_pull_request(
    db: AsyncSession, pull_request_id: uuid.UUID
) -> PullRequestAnalysis | None:
    result = await db.execute(
        select(PullRequestAnalysis)
        .where(PullRequestAnalysis.pull_request_id == pull_request_id)
        .order_by(PullRequestAnalysis.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def is_active(analysis: PullRequestAnalysis) -> bool:
    return analysis.status in _ACTIVE_STATUSES


def create(db: AsyncSession, *, pull_request_id: uuid.UUID, head_sha: str) -> PullRequestAnalysis:
    analysis = PullRequestAnalysis(
        pull_request_id=pull_request_id, head_sha=head_sha, status=PRAnalysisStatus.QUEUED
    )
    db.add(analysis)
    return analysis


def mark_running(analysis: PullRequestAnalysis, *, started_at: datetime) -> None:
    analysis.status = PRAnalysisStatus.RUNNING
    analysis.started_at = started_at


def mark_succeeded(
    analysis: PullRequestAnalysis,
    *,
    finished_at: datetime,
    risk_level: PRRiskLevel,
    summary: str,
    affected_components: list[AffectedComponentRecord],
    potential_concerns: list[PotentialConcernRecord],
    recommended_tests: list[RecommendedTestRecord],
    files_analyzed: list[ChangedFileRecord],
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    analysis.status = PRAnalysisStatus.SUCCEEDED
    analysis.finished_at = finished_at
    analysis.risk_level = risk_level
    analysis.summary = summary
    analysis.affected_components = affected_components
    analysis.potential_concerns = potential_concerns
    analysis.recommended_tests = recommended_tests
    analysis.files_analyzed = files_analyzed
    analysis.model = model
    analysis.input_tokens = input_tokens
    analysis.output_tokens = output_tokens


def mark_failed(analysis: PullRequestAnalysis, *, finished_at: datetime, error: str) -> None:
    analysis.status = PRAnalysisStatus.FAILED
    analysis.finished_at = finished_at
    analysis.error = error
