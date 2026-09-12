"""Repository-layer tests: exercise app/repositories/*.py functions
directly against a real database session, bypassing the service/route
layers entirely. These catch query-construction bugs (wrong filter,
missing scope, wrong ordering) that a service- or route-level test can
miss if its happy path never needed the edge case — e.g. a service test
for "get my organization's members" only proves the query returns
something, not that it excludes another organization's members too.

Uses tests/factories.py for setup so each test states only the fields it
actually cares about."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.role import Role
from app.repositories import (
    conversation_repository,
    organization_member_repository,
    pull_request_repository,
    repository_membership_repository,
    user_repository,
)
from tests.factories import (
    create_conversation,
    create_organization,
    create_organization_member,
    create_pull_request,
    create_repository,
    create_repository_membership,
    create_user,
)

pytestmark = pytest.mark.asyncio


class TestUserRepository:
    async def test_get_by_email_finds_an_exact_match(self, db_session: AsyncSession) -> None:
        user = await create_user(db_session, email="ada@example.com")

        found = await user_repository.get_by_email(db_session, "ada@example.com")

        assert found is not None
        assert found.id == user.id

    async def test_get_by_email_is_case_sensitive(self, db_session: AsyncSession) -> None:
        await create_user(db_session, email="ada@example.com")

        found = await user_repository.get_by_email(db_session, "ADA@EXAMPLE.COM")

        assert found is None

    async def test_get_by_email_returns_none_for_an_unregistered_address(
        self, db_session: AsyncSession
    ) -> None:
        assert await user_repository.get_by_email(db_session, "ghost@example.com") is None


class TestOrganizationMemberRepository:
    async def test_get_returns_none_when_the_user_is_not_a_member(
        self, db_session: AsyncSession
    ) -> None:
        organization = await create_organization(db_session)
        outsider = await create_user(db_session)

        member = await organization_member_repository.get(
            db_session, organization_id=organization.id, user_id=outsider.id
        )

        assert member is None

    async def test_list_for_organization_only_returns_that_organizations_members(
        self, db_session: AsyncSession
    ) -> None:
        org_a = await create_organization(db_session, name="Org A")
        org_b = await create_organization(db_session, name="Org B")
        member_a = await create_organization_member(db_session, organization=org_a)
        await create_organization_member(db_session, organization=org_b)

        members = await organization_member_repository.list_for_organization(
            db_session, org_a.id
        )

        assert [m.user_id for m in members] == [member_a.user_id]

    async def test_count_with_role_only_counts_the_given_role(
        self, db_session: AsyncSession
    ) -> None:
        organization = await create_organization(db_session)
        await create_organization_member(db_session, organization=organization, role=Role.OWNER)
        await create_organization_member(db_session, organization=organization, role=Role.ADMIN)
        await create_organization_member(db_session, organization=organization, role=Role.ADMIN)

        assert (
            await organization_member_repository.count_with_role(
                db_session, organization_id=organization.id, role=Role.ADMIN
            )
            == 2
        )
        assert (
            await organization_member_repository.count_with_role(
                db_session, organization_id=organization.id, role=Role.OWNER
            )
            == 1
        )


class TestRepositoryMembershipRepository:
    async def test_get_returns_none_for_a_user_without_access(
        self, db_session: AsyncSession
    ) -> None:
        repository = await create_repository(db_session)
        outsider = await create_user(db_session)

        membership = await repository_membership_repository.get(
            db_session, repository_id=repository.id, user_id=outsider.id
        )

        assert membership is None

    async def test_a_membership_in_one_repository_does_not_grant_another(
        self, db_session: AsyncSession
    ) -> None:
        """The exact cross-tenant-isolation invariant require_repository_access
        depends on — a membership row is scoped to one specific repository,
        not "any repository in the member's organization"."""
        organization = await create_organization(db_session)
        repo_a = await create_repository(db_session, organization=organization, full_name="acme/a")
        repo_b = await create_repository(db_session, organization=organization, full_name="acme/b")
        user = await create_user(db_session)
        await create_repository_membership(db_session, repository=repo_a, user=user)

        assert (
            await repository_membership_repository.get(
                db_session, repository_id=repo_a.id, user_id=user.id
            )
            is not None
        )
        assert (
            await repository_membership_repository.get(
                db_session, repository_id=repo_b.id, user_id=user.id
            )
            is None
        )

    async def test_list_repository_ids_for_user_reflects_only_their_own_memberships(
        self, db_session: AsyncSession
    ) -> None:
        repo_a = await create_repository(db_session, full_name="acme/a")
        repo_b = await create_repository(db_session, full_name="acme/b")
        user = await create_user(db_session)
        await create_repository_membership(db_session, repository=repo_a, user=user)

        ids = await repository_membership_repository.list_repository_ids_for_user(
            db_session, user.id
        )

        assert ids == [repo_a.id]
        assert repo_b.id not in ids


class TestPullRequestRepository:
    async def test_get_is_scoped_to_the_given_repository(self, db_session: AsyncSession) -> None:
        repo_a = await create_repository(db_session, full_name="acme/a")
        repo_b = await create_repository(db_session, full_name="acme/b")
        await create_pull_request(db_session, repository=repo_a, number=1)

        # Same PR number, but it belongs to a different repository — must
        # not be found via repo_b's scope even though the number matches.
        found_in_a = await pull_request_repository.get(
            db_session, repository_id=repo_a.id, number=1
        )
        found_in_b = await pull_request_repository.get(
            db_session, repository_id=repo_b.id, number=1
        )

        assert found_in_a is not None
        assert found_in_b is None

    async def test_list_for_repository_filters_by_state(self, db_session: AsyncSession) -> None:
        repository = await create_repository(db_session)
        await create_pull_request(db_session, repository=repository, number=1, state="open")
        await create_pull_request(db_session, repository=repository, number=2, state="closed")

        open_prs = await pull_request_repository.list_for_repository(
            db_session, repository.id, state="open"
        )

        assert [pr.number for pr in open_prs] == [1]

    async def test_get_returns_none_for_an_unknown_number(
        self, db_session: AsyncSession
    ) -> None:
        repository = await create_repository(db_session)
        assert (
            await pull_request_repository.get(db_session, repository_id=repository.id, number=999)
            is None
        )


class TestConversationRepository:
    async def test_list_for_repository_orders_most_recently_updated_first(
        self, db_session: AsyncSession
    ) -> None:
        repository = await create_repository(db_session)
        user = await create_user(db_session)
        older = await create_conversation(db_session, repository=repository, created_by=user)
        newer = await create_conversation(db_session, repository=repository, created_by=user)
        # Both share a created_at tick in fast test runs — bump `newer`
        # explicitly so the ordering assertion isn't a coin flip.
        from datetime import UTC, datetime, timedelta

        conversation_repository.touch(newer, at=datetime.now(UTC) + timedelta(seconds=10))
        conversation_repository.touch(older, at=datetime.now(UTC))
        await db_session.flush()

        conversations = await conversation_repository.list_for_repository(
            db_session, repository.id
        )

        assert [c.id for c in conversations] == [newer.id, older.id]

    async def test_list_for_repository_excludes_other_repositories_conversations(
        self, db_session: AsyncSession
    ) -> None:
        repo_a = await create_repository(db_session, full_name="acme/a")
        repo_b = await create_repository(db_session, full_name="acme/b")
        user = await create_user(db_session)
        conv_a = await create_conversation(db_session, repository=repo_a, created_by=user)
        await create_conversation(db_session, repository=repo_b, created_by=user)

        conversations = await conversation_repository.list_for_repository(db_session, repo_a.id)

        assert [c.id for c in conversations] == [conv_a.id]

    async def test_get_by_id_loads_messages_eagerly(self, db_session: AsyncSession) -> None:
        repository = await create_repository(db_session)
        user = await create_user(db_session)
        conversation = await create_conversation(db_session, repository=repository, created_by=user)

        found = await conversation_repository.get(db_session, conversation.id)

        assert found is not None
        assert found.messages == []  # accessing this without a lazy-load error proves eager load

    async def test_get_returns_none_for_an_unknown_id(self, db_session: AsyncSession) -> None:
        assert await conversation_repository.get(db_session, uuid.uuid4()) is None
