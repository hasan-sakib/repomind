import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import DbSession, require_csrf_header, require_organization_role
from app.models.organization_member import OrganizationMember
from app.models.role import Role
from app.schemas.api_key import ApiKeyCreatedPublic, ApiKeyPublic, CreateApiKeyRequest
from app.services import api_key_service

router = APIRouter(prefix="/organizations/{organization_id}/api-keys", tags=["api-keys"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=list[ApiKeyPublic])
async def list_api_keys(
    member: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
    db: DbSession,
) -> list[ApiKeyPublic]:
    keys = await api_key_service.list_api_keys(db, member.organization_id)
    return [ApiKeyPublic.from_api_key(k) for k in keys]


@router.post(
    "",
    response_model=ApiKeyCreatedPublic,
    status_code=201,
    dependencies=[Depends(require_csrf_header)],
)
async def create_api_key(
    body: CreateApiKeyRequest,
    request: Request,
    db: DbSession,
    actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
) -> ApiKeyCreatedPublic:
    api_key, secret = await api_key_service.create_api_key(
        db,
        organization_id=actor.organization_id,
        actor=actor,
        name=body.name,
        role=body.role,
        audit_ip=_client_ip(request),
    )
    await db.refresh(api_key, attribute_names=["created_by"])
    return ApiKeyCreatedPublic.from_api_key_and_secret(api_key, secret)


@router.delete(
    "/{api_key_id}",
    status_code=204,
    dependencies=[Depends(require_csrf_header)],
)
async def revoke_api_key(
    api_key_id: uuid.UUID,
    request: Request,
    db: DbSession,
    actor: Annotated[OrganizationMember, Depends(require_organization_role(Role.ADMIN))],
) -> None:
    await api_key_service.revoke_api_key(
        db,
        organization_id=actor.organization_id,
        api_key_id=api_key_id,
        actor=actor,
        audit_ip=_client_ip(request),
    )
