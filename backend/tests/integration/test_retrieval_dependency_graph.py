import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import (
    code_file_repository,
    code_symbol_repository,
    github_installation_repository,
    organization_repository,
    repository_repository,
)
from app.retrieval import dependency_graph

pytestmark = pytest.mark.asyncio


async def _create_repository(db: AsyncSession) -> uuid.UUID:
    organization = organization_repository.create(
        db, name="Acme", slug=f"acme-{uuid.uuid4().hex[:8]}"
    )
    await db.flush()
    installation = github_installation_repository.create(
        db,
        organization_id=organization.id,
        github_installation_id=uuid.uuid4().int % 1_000_000_000,
        account_login="acme",
        account_type="Organization",
    )
    await db.flush()
    repository = repository_repository.create(
        db,
        organization_id=organization.id,
        installation_id=installation.id,
        github_repo_id=1,
        full_name="acme/widgets",
        name="widgets",
        description=None,
        language="Python",
        stargazers_count=0,
        forks_count=0,
        default_branch="main",
        private=False,
        html_url="https://github.com/acme/widgets",
    )
    await db.commit()
    return repository.id


async def test_find_definition_prefers_class_over_method(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)
    code_file = code_file_repository.create(
        db_session,
        repository_id=repository_id,
        path="app/services/user_service.py",
        language="python",
        size_bytes=100,
        content_hash="a" * 64,
        commit_sha="b" * 40,
        imports=[],
        indexed_at=datetime.now(UTC),
    )
    await db_session.flush()
    code_symbol_repository.create(
        db_session,
        file_id=code_file.id,
        symbol_type="method",
        name="UserService",  # a decoy method sharing the class's name
        start_line=50,
        end_line=55,
        signature="def UserService(self):",
        docstring=None,
        parent_symbol_id=None,
    )
    code_symbol_repository.create(
        db_session,
        file_id=code_file.id,
        symbol_type="class",
        name="UserService",
        start_line=1,
        end_line=60,
        signature="class UserService:",
        docstring="Handles user accounts.",
        parent_symbol_id=None,
    )
    await db_session.commit()

    definition = await dependency_graph.find_definition(
        db_session, repository_id=repository_id, symbol_name="UserService"
    )

    assert definition is not None
    assert definition.file_path == "app/services/user_service.py"
    assert definition.start_line == 1
    assert "Handles user accounts." in definition.content


async def test_find_definition_returns_none_when_symbol_unknown(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)

    definition = await dependency_graph.find_definition(
        db_session, repository_id=repository_id, symbol_name="DoesNotExist"
    )

    assert definition is None


async def test_find_dependents_matches_files_that_import_the_symbol(
    db_session: AsyncSession,
) -> None:
    repository_id = await _create_repository(db_session)
    code_file_repository.create(
        db_session,
        repository_id=repository_id,
        path="app/api/routes/auth.py",
        language="python",
        size_bytes=100,
        content_hash="a" * 64,
        commit_sha="b" * 40,
        imports=[{"text": "from app.services.user_service import UserService", "line": 3}],
        indexed_at=datetime.now(UTC),
    )
    code_file_repository.create(
        db_session,
        repository_id=repository_id,
        path="app/api/routes/billing.py",
        language="python",
        size_bytes=100,
        content_hash="c" * 64,
        commit_sha="b" * 40,
        imports=[{"text": "from app.services.billing_service import BillingService", "line": 2}],
        indexed_at=datetime.now(UTC),
    )
    await db_session.commit()

    dependents = await dependency_graph.find_dependents(
        db_session, repository_id=repository_id, symbol_name="UserService", limit=10
    )

    assert len(dependents) == 1
    assert dependents[0].file_path == "app/api/routes/auth.py"
    assert dependents[0].start_line == 3


async def test_find_dependents_does_not_match_substring_of_a_longer_name(
    db_session: AsyncSession,
) -> None:
    """A file importing UserServiceV2 should not count as depending on
    UserService — dependency_graph.py matches on word boundaries."""
    repository_id = await _create_repository(db_session)
    code_file_repository.create(
        db_session,
        repository_id=repository_id,
        path="app/api/routes/legacy.py",
        language="python",
        size_bytes=100,
        content_hash="a" * 64,
        commit_sha="b" * 40,
        imports=[{"text": "from app.services import UserServiceV2", "line": 1}],
        indexed_at=datetime.now(UTC),
    )
    await db_session.commit()

    dependents = await dependency_graph.find_dependents(
        db_session, repository_id=repository_id, symbol_name="UserService", limit=10
    )

    assert dependents == []
