"""Read-only usage observability — how much of each plan's limits an
organization is actually using, plus AI token consumption, which no plan
limits today but which is the natural first thing a real billing
integration would eventually meter. See app/billing/entitlements.py for
the enforcement side of the same numbers."""

import uuid
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_run import AiRun
from app.models.analytics_snapshot import AnalyticsSnapshot
from app.models.conversation import Conversation
from app.models.indexing_job import IndexingJob
from app.models.onboarding_guide import OnboardingGuide
from app.models.organization import Organization
from app.models.pull_request import PullRequest
from app.models.pull_request_analysis import PullRequestAnalysis
from app.models.repository import Repository
from app.repositories import organization_member_repository, repository_repository


@dataclass(frozen=True)
class UsageSummary:
    repositories_used: int
    members_used: int
    ai_tokens_used: int
    indexing_runs: int
    pr_analyses_run: int
    onboarding_guides_generated: int
    analytics_snapshots_generated: int


async def _sum_tokens(db: AsyncSession, organization_id: uuid.UUID) -> int:
    chat_tokens = await db.scalar(
        select(func.coalesce(func.sum(AiRun.input_tokens + AiRun.output_tokens), 0))
        .select_from(AiRun)
        .join(Conversation, AiRun.conversation_id == Conversation.id)
        .join(Repository, Conversation.repository_id == Repository.id)
        .where(
            Repository.organization_id == organization_id,
            AiRun.input_tokens.is_not(None),
            AiRun.output_tokens.is_not(None),
        )
    )
    pr_tokens = await db.scalar(
        select(
            func.coalesce(
                func.sum(PullRequestAnalysis.input_tokens + PullRequestAnalysis.output_tokens), 0
            )
        )
        .select_from(PullRequestAnalysis)
        .join(PullRequest, PullRequestAnalysis.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .where(
            Repository.organization_id == organization_id,
            PullRequestAnalysis.input_tokens.is_not(None),
            PullRequestAnalysis.output_tokens.is_not(None),
        )
    )
    onboarding_tokens = await db.scalar(
        select(
            func.coalesce(func.sum(OnboardingGuide.input_tokens + OnboardingGuide.output_tokens), 0)
        )
        .select_from(OnboardingGuide)
        .join(Repository, OnboardingGuide.repository_id == Repository.id)
        .where(
            Repository.organization_id == organization_id,
            OnboardingGuide.input_tokens.is_not(None),
            OnboardingGuide.output_tokens.is_not(None),
        )
    )
    return int(chat_tokens or 0) + int(pr_tokens or 0) + int(onboarding_tokens or 0)


async def _count_indexing_runs(db: AsyncSession, organization_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(IndexingJob)
        .join(Repository, IndexingJob.repository_id == Repository.id)
        .where(Repository.organization_id == organization_id)
    )
    return result.scalar_one()


async def _count_pr_analyses(db: AsyncSession, organization_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(PullRequestAnalysis)
        .join(PullRequest, PullRequestAnalysis.pull_request_id == PullRequest.id)
        .join(Repository, PullRequest.repository_id == Repository.id)
        .where(Repository.organization_id == organization_id)
    )
    return result.scalar_one()


async def _count_onboarding_guides(db: AsyncSession, organization_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(OnboardingGuide)
        .join(Repository, OnboardingGuide.repository_id == Repository.id)
        .where(Repository.organization_id == organization_id)
    )
    return result.scalar_one()


async def _count_analytics_snapshots(db: AsyncSession, organization_id: uuid.UUID) -> int:
    result = await db.execute(
        select(func.count())
        .select_from(AnalyticsSnapshot)
        .join(Repository, AnalyticsSnapshot.repository_id == Repository.id)
        .where(Repository.organization_id == organization_id)
    )
    return result.scalar_one()


async def get_usage_summary(db: AsyncSession, organization: Organization) -> UsageSummary:
    return UsageSummary(
        repositories_used=await repository_repository.count_for_organization(db, organization.id),
        members_used=await organization_member_repository.count_for_organization(
            db, organization.id
        ),
        ai_tokens_used=await _sum_tokens(db, organization.id),
        indexing_runs=await _count_indexing_runs(db, organization.id),
        pr_analyses_run=await _count_pr_analyses(db, organization.id),
        onboarding_guides_generated=await _count_onboarding_guides(db, organization.id),
        analytics_snapshots_generated=await _count_analytics_snapshots(db, organization.id),
    )
