from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import (
    ArqPool,
    DbSession,
    get_current_user,
    require_csrf_header,
    require_repository_access,
)
from app.models.repository import Repository
from app.models.user import User
from app.schemas.onboarding import OnboardingGuidePublic, SetProgressRequest
from app.services import onboarding_service

router = APIRouter(prefix="/repositories/{repository_id}/onboarding", tags=["onboarding"])


@router.get("", response_model=OnboardingGuidePublic)
async def get_guide(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
) -> OnboardingGuidePublic:
    guide = await onboarding_service.get_latest_guide_or_raise(db, repository.id)
    return OnboardingGuidePublic.from_guide(guide)


@router.post(
    "",
    status_code=202,
    response_model=OnboardingGuidePublic,
    dependencies=[Depends(require_csrf_header)],
)
async def trigger_guide(
    repository: Annotated[Repository, Depends(require_repository_access)],
    db: DbSession,
    arq_pool: ArqPool,
    force: bool = False,
) -> OnboardingGuidePublic:
    guide, started = await onboarding_service.trigger_guide_generation(
        db, repository=repository, force=force
    )
    if started:
        await arq_pool.enqueue_job("generate_onboarding_guide", str(guide.id))
    return OnboardingGuidePublic.from_guide(guide)


@router.get("/progress", response_model=list[str])
async def get_progress(
    repository: Annotated[Repository, Depends(require_repository_access)],
    user: Annotated[User, Depends(get_current_user)],
    db: DbSession,
) -> list[str]:
    completed = await onboarding_service.get_progress(
        db, repository_id=repository.id, user_id=user.id
    )
    return sorted(completed)


@router.put("/progress/{item_key}", status_code=204, dependencies=[Depends(require_csrf_header)])
async def set_progress(
    repository: Annotated[Repository, Depends(require_repository_access)],
    user: Annotated[User, Depends(get_current_user)],
    item_key: str,
    body: SetProgressRequest,
    db: DbSession,
) -> None:
    await onboarding_service.set_progress(
        db,
        repository_id=repository.id,
        user_id=user.id,
        item_key=item_key,
        completed=body.completed,
    )
