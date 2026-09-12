"""The one place plan limits are enforced. Every call site that creates a
metered resource (connecting a repository, adding an organization member)
calls one of these functions instead of comparing `organization.plan` or a
hardcoded number itself — see app/billing/plans.py for the limits table
and docs/architecture/0011-saas-management.md for why this exists as its
own module rather than being folded into organization_service."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.plans import PlanLimits, limits_for
from app.models.organization import Organization
from app.repositories import (
    organization_member_repository,
    organization_repository,
    repository_repository,
)
from app.services.exceptions import OrganizationNotFoundError, PlanLimitReachedError


def get_limits(organization: Organization) -> PlanLimits:
    return limits_for(organization.plan)


async def ensure_can_add_repository(db: AsyncSession, organization: Organization) -> None:
    limit = get_limits(organization).max_repositories
    if limit is None:
        return
    current = await repository_repository.count_for_organization(db, organization.id)
    if current >= limit:
        raise PlanLimitReachedError(
            f"The {organization.plan.value} plan allows up to {limit} connected "
            "repositories. Upgrade your plan to connect more."
        )


async def ensure_can_add_member(db: AsyncSession, organization: Organization) -> None:
    limit = get_limits(organization).max_members
    if limit is None:
        return
    current = await organization_member_repository.count_for_organization(db, organization.id)
    if current >= limit:
        raise PlanLimitReachedError(
            f"The {organization.plan.value} plan allows up to {limit} members. "
            "Upgrade your plan to add more."
        )


async def get_organization_or_raise(db: AsyncSession, organization_id: uuid.UUID) -> Organization:
    """Small helper for call sites that only have an id (not an already-
    loaded Organization) and need entitlements — e.g. repository_service,
    which loads a Repository/Installation but not the parent Organization
    row itself today."""
    organization = await organization_repository.get_by_id(db, organization_id)
    if organization is None:
        raise OrganizationNotFoundError("Organization not found")
    return organization
