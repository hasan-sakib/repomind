import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.github.schemas import GitHubPullRequestFile
from app.pr_analysis.context import build_context
from app.repositories import (
    code_file_repository,
    code_symbol_repository,
    github_installation_repository,
    organization_repository,
    repository_repository,
)

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


async def _seed(db: AsyncSession, repository_id: uuid.UUID) -> None:
    service_file = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="app/services/auth_service.py",
        language="python",
        size_bytes=10,
        content_hash="a" * 64,
        commit_sha="f" * 40,
        imports=[],
        indexed_at=datetime.now(UTC),
    )
    route_file = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="app/api/routes/auth.py",
        language="python",
        size_bytes=10,
        content_hash="b" * 64,
        commit_sha="f" * 40,
        imports=[{"text": "from app.services.auth_service import AuthService", "line": 1}],
        indexed_at=datetime.now(UTC),
    )
    test_file = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="tests/test_auth_service.py",
        language="python",
        size_bytes=10,
        content_hash="c" * 64,
        commit_sha="f" * 40,
        imports=[{"text": "from app.services.auth_service import AuthService", "line": 1}],
        indexed_at=datetime.now(UTC),
    )
    await db.flush()

    code_symbol_repository.create(
        db,
        file_id=service_file.id,
        symbol_type="class",
        name="AuthService",
        start_line=1,
        end_line=30,
        signature="class AuthService:",
        docstring=None,
        parent_symbol_id=None,
    )
    code_symbol_repository.create(
        db,
        file_id=service_file.id,
        symbol_type="method",
        name="login",
        start_line=5,
        end_line=15,
        signature="def login(self, credentials):",
        docstring=None,
        parent_symbol_id=None,
    )
    code_symbol_repository.create(
        db,
        file_id=route_file.id,
        symbol_type="function",
        name="login_route",
        start_line=1,
        end_line=10,
        signature="def login_route():",
        docstring=None,
        parent_symbol_id=None,
    )
    _ = test_file
    await db.commit()


def _pr_file(
    filename: str, patch: str | None, *, status: str = "modified"
) -> GitHubPullRequestFile:
    return GitHubPullRequestFile(
        filename=filename, status=status, additions=5, deletions=1, changes=6, patch=patch
    )


async def test_changed_symbols_are_found_from_the_diffs_added_lines(
    db_session: AsyncSession,
) -> None:
    repository_id = await _create_repository(db_session)
    await _seed(db_session, repository_id)

    # The diff's added line lands inside `login` (lines 5-15), not the
    # class header — only `login` should show up as changed.
    patch = "@@ -8,0 +9,1 @@ class AuthService:\n+        validate_mfa(credentials)"
    files = [_pr_file("app/services/auth_service.py", patch)]

    context = await build_context(
        db_session, repository_id=repository_id, files=files, max_patch_chars=2000
    )

    assert len(context.changed_files) == 1
    changed = context.changed_files[0]
    assert changed.indexed is True
    # The added line falls inside both `login` and its enclosing
    # `AuthService` class — both legitimately overlap the diff.
    assert {s.name for s in changed.changed_symbols} == {"login", "AuthService"}


async def test_dependents_are_found_via_import_matching(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)
    await _seed(db_session, repository_id)

    patch = "@@ -8,0 +9,1 @@ class AuthService:\n+        validate_mfa(credentials)"
    files = [_pr_file("app/services/auth_service.py", patch)]

    context = await build_context(
        db_session, repository_id=repository_id, files=files, max_patch_chars=2000
    )

    dependent_paths = {d.path for d in context.changed_files[0].dependents}
    assert "app/api/routes/auth.py" in dependent_paths


async def test_related_existing_test_file_is_found(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)
    await _seed(db_session, repository_id)

    patch = "@@ -8,0 +9,1 @@ class AuthService:\n+        validate_mfa(credentials)"
    files = [_pr_file("app/services/auth_service.py", patch)]

    context = await build_context(
        db_session, repository_id=repository_id, files=files, max_patch_chars=2000
    )

    assert [t.path for t in context.related_tests] == ["tests/test_auth_service.py"]
    assert context.valid_file_paths() == {
        "app/services/auth_service.py",
        "tests/test_auth_service.py",
    }


async def test_unindexed_file_is_reported_but_not_crashed_on(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)
    await _seed(db_session, repository_id)

    files = [_pr_file("app/new_module_never_indexed.py", "@@ -0,0 +1,1 @@\n+x = 1", status="added")]

    context = await build_context(
        db_session, repository_id=repository_id, files=files, max_patch_chars=2000
    )

    assert context.changed_files[0].indexed is False
    assert context.changed_files[0].changed_symbols == []


async def test_patch_excerpt_is_truncated_to_the_configured_limit(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)
    await _seed(db_session, repository_id)

    long_patch = "@@ -1,1 +1,1 @@\n+" + ("x" * 5000)
    files = [_pr_file("app/services/auth_service.py", long_patch)]

    context = await build_context(
        db_session, repository_id=repository_id, files=files, max_patch_chars=100
    )

    assert len(context.changed_files[0].patch_excerpt) == 100
