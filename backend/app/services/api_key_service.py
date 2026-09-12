"""Programmatic (organization-scoped) credentials — see app/models/api_key.py
for the storage shape and docs/architecture/0011-saas-management.md for
the auth-integration scope decision. Mirrors the audit-logging and
role-guard conventions already established in organization_service.py."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import ApiKey
from app.models.organization_member import OrganizationMember
from app.models.role import Role, role_at_least
from app.repositories import api_key_repository, audit_log_repository
from app.services.exceptions import (
    ApiKeyNotFoundError,
    InsufficientRoleError,
    NotAuthenticatedError,
)

_TOKEN_PREFIX = "rm_"
_DISPLAY_PREFIX_LENGTH = len(_TOKEN_PREFIX) + 12


def _hash_secret(secret: str) -> str:
    # SHA-256, not a slow password hash (bcrypt/argon2): the secret is a
    # 256-bit random token, not a user-chosen password, so there's no
    # brute-force risk a slow hash would mitigate — only a fast, reliable
    # equality check on lookup.
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


async def create_api_key(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    actor: OrganizationMember,
    name: str,
    role: Role,
    audit_ip: str | None = None,
) -> tuple[ApiKey, str]:
    """Returns (api_key, plaintext_secret) — the secret is never
    recoverable again after this call returns."""
    if not role_at_least(actor.role, role):
        raise InsufficientRoleError("Cannot create a key with a role higher than your own")

    secret = f"{_TOKEN_PREFIX}{secrets.token_urlsafe(32)}"
    api_key = api_key_repository.create(
        db,
        organization_id=organization_id,
        created_by_user_id=actor.user_id,
        name=name,
        key_prefix=secret[:_DISPLAY_PREFIX_LENGTH],
        key_hash=_hash_secret(secret),
        role=role,
    )
    await db.flush()
    audit_log_repository.create(
        db,
        action="api_key.created",
        actor_user_id=actor.user_id,
        organization_id=organization_id,
        target_type="api_key",
        target_id=str(api_key.id),
        ip_address=audit_ip,
        extra={"name": name, "role": role.value},
    )
    await db.commit()
    await db.refresh(api_key)
    return api_key, secret


async def list_api_keys(db: AsyncSession, organization_id: uuid.UUID) -> list[ApiKey]:
    return await api_key_repository.list_for_organization(db, organization_id)


async def revoke_api_key(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    api_key_id: uuid.UUID,
    actor: OrganizationMember,
    audit_ip: str | None = None,
) -> ApiKey:
    api_key = await api_key_repository.get(db, api_key_id)
    if api_key is None or api_key.organization_id != organization_id:
        raise ApiKeyNotFoundError("API key not found")

    api_key_repository.revoke(api_key, at=datetime.now(UTC))
    audit_log_repository.create(
        db,
        action="api_key.revoked",
        actor_user_id=actor.user_id,
        organization_id=organization_id,
        target_type="api_key",
        target_id=str(api_key.id),
        ip_address=audit_ip,
    )
    await db.commit()
    await db.refresh(api_key)
    return api_key


async def authenticate(db: AsyncSession, secret: str) -> ApiKey:
    """Looks up and validates a raw `Authorization: Bearer <secret>` value.
    Used only by the API-key branch of app/api/deps.py's repository-access
    dependency — see that module for which routes actually accept this."""
    api_key = await api_key_repository.get_by_hash(db, _hash_secret(secret))
    if api_key is None or api_key.revoked_at is not None:
        raise NotAuthenticatedError("Invalid or revoked API key")

    api_key_repository.mark_used(api_key, at=datetime.now(UTC))
    await db.commit()
    return api_key
