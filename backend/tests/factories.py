"""Shared test data factories — small async builder functions that create
and flush a fully-shaped row with sane defaults, overridable per call.
Used instead of every test file hand-rolling its own `_create_repository`-
style helper (several already did, independently, before this file
existed): a test that only cares about a repository's `language` shouldn't
have to also restate its organization, installation, and every other
required field, and when a model gains a required column, only this file
needs to change.

Every function flushes (never commits) so the caller gets a real
generated id/timestamps back immediately, while still controlling its own
transaction boundary — matches the pattern already used throughout
tests/integration/."""

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation import Conversation
from app.models.organization import Organization
from app.models.organization_member import OrganizationMember
from app.models.pull_request import PullRequest
from app.models.repository import Repository
from app.models.repository_membership import RepositoryMembership
from app.models.role import Role
from app.models.user import User
from app.repositories import (
    conversation_repository,
    github_installation_repository,
    organization_member_repository,
    organization_repository,
    pull_request_repository,
    repository_membership_repository,
    repository_repository,
    user_repository,
)


def _unique(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"


async def create_user(
    db: AsyncSession,
    *,
    email: str | None = None,
    full_name: str = "Test User",
    password_hash: str | None = None,
) -> User:
    user = user_repository.create(
        db,
        email=email or f"{_unique('user')}@example.com",
        full_name=full_name,
        password_hash=password_hash,
    )
    await db.flush()
    return user


async def create_organization(
    db: AsyncSession, *, name: str = "Acme Inc", slug: str | None = None
) -> Organization:
    organization = organization_repository.create(db, name=name, slug=slug or _unique("acme"))
    await db.flush()
    return organization


async def create_organization_member(
    db: AsyncSession,
    *,
    organization: Organization | None = None,
    user: User | None = None,
    role: Role = Role.OWNER,
) -> OrganizationMember:
    organization = organization or await create_organization(db)
    user = user or await create_user(db)
    member = organization_member_repository.create(
        db, organization_id=organization.id, user_id=user.id, role=role
    )
    await db.flush()
    return member


async def create_repository(
    db: AsyncSession,
    *,
    organization: Organization | None = None,
    full_name: str = "acme/widgets",
    name: str = "widgets",
    language: str | None = "Python",
    private: bool = False,
) -> Repository:
    organization = organization or await create_organization(db)
    installation = github_installation_repository.create(
        db,
        organization_id=organization.id,
        github_installation_id=uuid.uuid4().int % 1_000_000_000,
        account_login=organization.slug,
        account_type="Organization",
    )
    await db.flush()
    repository = repository_repository.create(
        db,
        organization_id=organization.id,
        installation_id=installation.id,
        github_repo_id=uuid.uuid4().int % 1_000_000_000,
        full_name=full_name,
        name=name,
        description=None,
        language=language,
        stargazers_count=0,
        forks_count=0,
        default_branch="main",
        private=private,
        html_url=f"https://github.com/{full_name}",
    )
    await db.flush()
    return repository


async def create_repository_membership(
    db: AsyncSession, *, repository: Repository, user: User
) -> RepositoryMembership:
    membership = repository_membership_repository.create(
        db, repository_id=repository.id, user_id=user.id
    )
    await db.flush()
    return membership


async def create_pull_request(
    db: AsyncSession,
    *,
    repository: Repository,
    number: int = 1,
    title: str = "Add a feature",
    state: str = "open",
    author_login: str | None = "octocat",
    head_sha: str | None = None,
    merged_at: datetime | None = None,
    closed_at: datetime | None = None,
) -> PullRequest:
    now = datetime.now(UTC)
    pr = pull_request_repository.create(
        db,
        repository_id=repository.id,
        number=number,
        title=title,
        state=state,
        author_login=author_login,
        html_url=f"{repository.html_url}/pull/{number}",
        head_sha=head_sha or ("a" * 40),
        github_created_at=now,
        github_updated_at=now,
        closed_at=closed_at,
        merged_at=merged_at,
        synced_at=now,
    )
    await db.flush()
    return pr


async def create_conversation(
    db: AsyncSession, *, repository: Repository, created_by: User
) -> Conversation:
    conversation = conversation_repository.create(
        db, repository_id=repository.id, created_by_user_id=created_by.id
    )
    await db.flush()
    return conversation
