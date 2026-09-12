import secrets
import uuid
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Query
from fastapi.responses import RedirectResponse

from app.api.deps import DbSession, require_organization_role
from app.core.config import get_settings
from app.domain.organization_member import OrganizationMember
from app.domain.role import Role
from app.repositories import github_installation_repository
from app.schemas.github import AvailableRepositoryPublic, InstallationPublic
from app.services import github_service
from app.services.exceptions import InstallationNotFoundError

router = APIRouter(prefix="/organizations/{organization_id}/github", tags=["github"])
callback_router = APIRouter(prefix="/github", tags=["github"])
settings = get_settings()

INSTALL_STATE_COOKIE = "rm_github_install_state"


@router.get("/install")
async def start_install(
    organization_id: uuid.UUID,
    _actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
) -> RedirectResponse:
    state_token = secrets.token_urlsafe(24)
    redirect = RedirectResponse(github_service.build_install_url(state=state_token))
    redirect.set_cookie(
        INSTALL_STATE_COOKIE,
        f"{organization_id}:{state_token}",
        max_age=600,
        httponly=True,
        secure=settings.environment == "production",
        samesite="lax",
        path=f"{settings.api_v1_prefix}/github/callback",
    )
    return redirect


@router.get("/installations", response_model=list[InstallationPublic])
async def list_installations(
    organization_id: uuid.UUID,
    db: DbSession,
    _actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.VIEWER))],
) -> list[InstallationPublic]:
    installations = await github_installation_repository.list_for_organization(db, organization_id)
    return [InstallationPublic.model_validate(i) for i in installations]


@router.get(
    "/installations/{installation_id}/available-repositories",
    response_model=list[AvailableRepositoryPublic],
)
async def list_available_repositories(
    organization_id: uuid.UUID,
    installation_id: uuid.UUID,
    db: DbSession,
    _actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
) -> list[AvailableRepositoryPublic]:
    installation = await github_installation_repository.get_by_id(db, installation_id)
    if installation is None or installation.organization_id != organization_id:
        raise InstallationNotFoundError("GitHub installation not found")
    repos = await github_service.list_available_repositories(db, installation)
    return [AvailableRepositoryPublic.from_github_repo(r) for r in repos]


@callback_router.get("/callback")
async def install_callback(
    db: DbSession,
    installation_id: Annotated[int, Query()],
    state: Annotated[str, Query()],
    rm_github_install_state: Annotated[str | None, Cookie()] = None,
) -> RedirectResponse:
    if rm_github_install_state is None:
        return RedirectResponse(f"{settings.frontend_url}/dashboard?github_error=invalid_state")

    expected_org_id, _, expected_state = rm_github_install_state.partition(":")
    if not secrets.compare_digest(state, expected_state):
        return RedirectResponse(f"{settings.frontend_url}/dashboard?github_error=invalid_state")

    organization_id = uuid.UUID(expected_org_id)
    await github_service.connect_installation(
        db, organization_id=organization_id, github_installation_id=installation_id
    )

    redirect = RedirectResponse(f"{settings.frontend_url}/repositories/connect")
    redirect.delete_cookie(INSTALL_STATE_COOKIE, path=f"{settings.api_v1_prefix}/github/callback")
    return redirect
