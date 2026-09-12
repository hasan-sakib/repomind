import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing import entitlements
from app.models.plan import Plan
from app.models.role import Role
from app.repositories import (
    github_installation_repository,
    organization_member_repository,
    organization_repository,
    repository_repository,
    user_repository,
)
from app.services.exceptions import PlanLimitReachedError

pytestmark = pytest.mark.asyncio


async def _seed_organization(db: AsyncSession, *, plan: Plan) -> uuid.UUID:
    organization = organization_repository.create(
        db, name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}"
    )
    await db.flush()
    organization_repository.update_plan(organization, plan=plan)
    await db.commit()
    return organization.id


async def _add_repository(db: AsyncSession, organization_id: uuid.UUID, n: int) -> None:
    installation = github_installation_repository.create(
        db,
        organization_id=organization_id,
        github_installation_id=1000 + n,
        account_login="acme",
        account_type="Organization",
    )
    await db.flush()
    repository_repository.create(
        db,
        organization_id=organization_id,
        installation_id=installation.id,
        github_repo_id=n,
        full_name=f"acme/repo-{n}",
        name=f"repo-{n}",
        description=None,
        language=None,
        stargazers_count=0,
        forks_count=0,
        default_branch="main",
        private=False,
        html_url=f"https://github.com/acme/repo-{n}",
    )
    await db.commit()


async def _add_member(db: AsyncSession, organization_id: uuid.UUID, n: int) -> None:
    user = user_repository.create(
        db, email=f"member{n}-{uuid.uuid4().hex[:6]}@example.com", full_name=f"Member {n}"
    )
    await db.flush()
    organization_member_repository.create(
        db, organization_id=organization_id, user_id=user.id, role=Role.VIEWER
    )
    await db.commit()


async def test_free_plan_blocks_the_fourth_repository(db_session: AsyncSession) -> None:
    organization_id = await _seed_organization(db_session, plan=Plan.FREE)
    for n in range(3):
        await _add_repository(db_session, organization_id, n)

    organization = await organization_repository.get_by_id(db_session, organization_id)
    assert organization is not None
    with pytest.raises(PlanLimitReachedError):
        await entitlements.ensure_can_add_repository(db_session, organization)


async def test_free_plan_allows_up_to_the_third_repository(db_session: AsyncSession) -> None:
    organization_id = await _seed_organization(db_session, plan=Plan.FREE)
    for n in range(2):
        await _add_repository(db_session, organization_id, n)

    organization = await organization_repository.get_by_id(db_session, organization_id)
    assert organization is not None
    await entitlements.ensure_can_add_repository(db_session, organization)  # must not raise


async def test_team_plan_has_no_repository_limit(db_session: AsyncSession) -> None:
    organization_id = await _seed_organization(db_session, plan=Plan.TEAM)
    for n in range(10):
        await _add_repository(db_session, organization_id, n)

    organization = await organization_repository.get_by_id(db_session, organization_id)
    assert organization is not None
    await entitlements.ensure_can_add_repository(db_session, organization)  # must not raise


async def test_free_plan_blocks_the_fourth_member(db_session: AsyncSession) -> None:
    organization_id = await _seed_organization(db_session, plan=Plan.FREE)
    for n in range(3):
        await _add_member(db_session, organization_id, n)

    organization = await organization_repository.get_by_id(db_session, organization_id)
    assert organization is not None
    with pytest.raises(PlanLimitReachedError):
        await entitlements.ensure_can_add_member(db_session, organization)
