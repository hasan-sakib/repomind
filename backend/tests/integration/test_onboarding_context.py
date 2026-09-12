import base64
import re
import uuid
from datetime import UTC, datetime

import pytest
from pytest_httpx import HTTPXMock
from sqlalchemy.ext.asyncio import AsyncSession

from app.onboarding.context import build_context
from app.repositories import (
    code_file_repository,
    code_symbol_repository,
    github_installation_repository,
    organization_repository,
    repository_repository,
)

pytestmark = pytest.mark.asyncio

CONTENTS_URL = re.compile(r"^https://api\.github\.com/repos/acme/widgets/contents/(.*)\?ref=.*")


def _mock_contents(httpx_mock: HTTPXMock, path: str, content: str) -> None:
    httpx_mock.add_response(
        url=re.compile(
            rf"^https://api\.github\.com/repos/acme/widgets/contents/{re.escape(path)}\?ref=.*"
        ),
        json={
            "name": path.rsplit("/", 1)[-1],
            "path": path,
            "encoding": "base64",
            "content": base64.b64encode(content.encode()).decode(),
        },
    )


def _mock_missing(httpx_mock: HTTPXMock, path: str) -> None:
    httpx_mock.add_response(
        url=re.compile(
            rf"^https://api\.github\.com/repos/acme/widgets/contents/{re.escape(path)}\?ref=.*"
        ),
        status_code=404,
        json={"message": "Not Found"},
    )


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
    readme = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="README.md",
        language=None,
        size_bytes=10,
        content_hash="a" * 64,
        commit_sha="f" * 40,
        imports=[],
        indexed_at=datetime.now(UTC),
    )
    entry = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="app/main.py",
        language="python",
        size_bytes=10,
        content_hash="b" * 64,
        commit_sha="f" * 40,
        imports=[],
        indexed_at=datetime.now(UTC),
    )
    auth_service = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="app/services/auth_service.py",
        language="python",
        size_bytes=10,
        content_hash="c" * 64,
        commit_sha="f" * 40,
        imports=[],
        indexed_at=datetime.now(UTC),
    )
    auth_route = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="app/api/routes/auth.py",
        language="python",
        size_bytes=10,
        content_hash="d" * 64,
        commit_sha="f" * 40,
        imports=[{"text": "from app.services.auth_service import AuthService", "line": 1}],
        indexed_at=datetime.now(UTC),
    )
    manifest = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="pyproject.toml",
        language=None,
        size_bytes=10,
        content_hash="e" * 64,
        commit_sha="f" * 40,
        imports=[],
        indexed_at=datetime.now(UTC),
    )
    await db.flush()

    code_symbol_repository.create(
        db,
        file_id=auth_service.id,
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
        file_id=auth_route.id,
        symbol_type="class",
        name="AuthController",
        start_line=1,
        end_line=20,
        signature="class AuthController:",
        docstring=None,
        parent_symbol_id=None,
    )
    await db.commit()
    _ = readme, entry, manifest


async def test_build_context_gathers_everything(
    db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _create_repository(db_session)
    await _seed(db_session, repository_id)
    _mock_contents(httpx_mock, "README.md", "# Widgets\n\nA widget factory.")
    _mock_contents(httpx_mock, "pyproject.toml", '[project]\ndependencies = ["fastapi>=0.115"]\n')

    context = await build_context(
        db_session,
        repository_id=repository_id,
        installation_token="fake-token",
        full_name="acme/widgets",
        commit_sha="f" * 40,
    )

    assert context.readme_content == "# Widgets\n\nA widget factory."
    assert [d.name for d in context.key_dependencies] == ["fastapi"]
    assert any(f.path == "app/services/auth_service.py" for f in context.auth_files)
    assert any(m.path == "app/api/routes" for m in context.important_modules)
    assert context.learning_path[0].label == "README"


async def test_build_context_handles_a_missing_readme_gracefully(
    db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _create_repository(db_session)
    await _seed(db_session, repository_id)
    _mock_missing(httpx_mock, "README.md")
    _mock_missing(httpx_mock, "pyproject.toml")

    context = await build_context(
        db_session,
        repository_id=repository_id,
        installation_token="fake-token",
        full_name="acme/widgets",
        commit_sha="f" * 40,
    )

    assert context.readme_content is None
    assert context.key_dependencies == []
    # README.md is still indexed (find_readme resolves it from CodeFile
    # rows alone) — but GitHub 404s fetching its *content*, so the guide
    # just has no excerpt rather than crashing.
    assert context.learning_path[0].label == "README"


async def test_valid_file_paths_only_includes_shown_paths(
    db_session: AsyncSession, httpx_mock: HTTPXMock
) -> None:
    repository_id = await _create_repository(db_session)
    await _seed(db_session, repository_id)
    _mock_missing(httpx_mock, "README.md")
    _mock_missing(httpx_mock, "pyproject.toml")

    context = await build_context(
        db_session,
        repository_id=repository_id,
        installation_token="fake-token",
        full_name="acme/widgets",
        commit_sha="f" * 40,
    )

    valid = context.valid_file_paths()
    assert "app/services/auth_service.py" in valid
    assert "some/path/never/shown.py" not in valid
