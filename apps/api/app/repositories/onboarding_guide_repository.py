import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.onboarding_guide import (
    DatabaseStructureEntryRecord,
    DependencyRecord,
    FaqEntryRecord,
    ImportantModuleRecord,
    LearningPathStepRecord,
    OnboardingGuide,
    RecommendedFileRecord,
    SetupStepRecord,
)
from app.domain.onboarding_status import OnboardingGuideStatus

_ACTIVE_STATUSES = (OnboardingGuideStatus.QUEUED, OnboardingGuideStatus.RUNNING)


async def get(db: AsyncSession, guide_id: uuid.UUID) -> OnboardingGuide | None:
    return await db.get(OnboardingGuide, guide_id)


async def get_latest_for_repository(
    db: AsyncSession, repository_id: uuid.UUID
) -> OnboardingGuide | None:
    result = await db.execute(
        select(OnboardingGuide)
        .where(OnboardingGuide.repository_id == repository_id)
        .order_by(OnboardingGuide.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def is_active(guide: OnboardingGuide) -> bool:
    return guide.status in _ACTIVE_STATUSES


def create(db: AsyncSession, *, repository_id: uuid.UUID, commit_sha: str) -> OnboardingGuide:
    guide = OnboardingGuide(
        repository_id=repository_id, commit_sha=commit_sha, status=OnboardingGuideStatus.QUEUED
    )
    db.add(guide)
    return guide


def mark_running(guide: OnboardingGuide, *, started_at: datetime) -> None:
    guide.status = OnboardingGuideStatus.RUNNING
    guide.started_at = started_at


def mark_succeeded(
    guide: OnboardingGuide,
    *,
    finished_at: datetime,
    architecture_overview: str,
    common_workflows: str,
    authentication_flow: str | None,
    faq: list[FaqEntryRecord],
    important_modules: list[ImportantModuleRecord],
    recommended_files: list[RecommendedFileRecord],
    key_dependencies: list[DependencyRecord],
    dev_setup_steps: list[SetupStepRecord],
    database_structure: list[DatabaseStructureEntryRecord],
    learning_path: list[LearningPathStepRecord],
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> None:
    guide.status = OnboardingGuideStatus.SUCCEEDED
    guide.finished_at = finished_at
    guide.architecture_overview = architecture_overview
    guide.common_workflows = common_workflows
    guide.authentication_flow = authentication_flow
    guide.faq = faq
    guide.important_modules = important_modules
    guide.recommended_files = recommended_files
    guide.key_dependencies = key_dependencies
    guide.dev_setup_steps = dev_setup_steps
    guide.database_structure = database_structure
    guide.learning_path = learning_path
    guide.model = model
    guide.input_tokens = input_tokens
    guide.output_tokens = output_tokens


def mark_failed(guide: OnboardingGuide, *, finished_at: datetime, error: str) -> None:
    guide.status = OnboardingGuideStatus.FAILED
    guide.finished_at = finished_at
    guide.error = error
