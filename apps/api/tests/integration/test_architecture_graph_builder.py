import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.architecture import graph_builder
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


async def _seed_layered_architecture(
    db: AsyncSession, repository_id: uuid.UUID
) -> dict[str, uuid.UUID]:
    """API route -> AuthService -> UserRepository -> (database) — the
    brief's own example, used as the reference fixture throughout."""
    route_file = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="app/api/routes/auth.py",
        language="python",
        size_bytes=10,
        content_hash="a" * 64,
        commit_sha="f" * 40,
        imports=[{"text": "from app.services.auth_service import AuthService", "line": 1}],
        indexed_at=datetime.now(UTC),
    )
    service_file = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="app/services/auth_service.py",
        language="python",
        size_bytes=10,
        content_hash="b" * 64,
        commit_sha="f" * 40,
        imports=[
            {"text": "from app.repositories.user_repository import UserRepository", "line": 1}
        ],
        indexed_at=datetime.now(UTC),
    )
    repo_file = code_file_repository.create(
        db,
        repository_id=repository_id,
        path="app/repositories/user_repository.py",
        language="python",
        size_bytes=10,
        content_hash="c" * 64,
        commit_sha="f" * 40,
        imports=[],
        indexed_at=datetime.now(UTC),
    )
    await db.flush()

    code_symbol_repository.create(
        db,
        file_id=service_file.id,
        symbol_type="class",
        name="AuthService",
        start_line=1,
        end_line=20,
        signature="class AuthService:",
        docstring="Handles auth.",
        parent_symbol_id=None,
    )
    code_symbol_repository.create(
        db,
        file_id=service_file.id,
        symbol_type="method",
        name="login",
        start_line=5,
        end_line=10,
        signature="def login(self, credentials):",
        docstring=None,
        parent_symbol_id=None,
    )
    code_symbol_repository.create(
        db,
        file_id=repo_file.id,
        symbol_type="class",
        name="UserRepository",
        start_line=1,
        end_line=15,
        signature="class UserRepository:",
        docstring=None,
        parent_symbol_id=None,
    )
    await db.commit()
    return {"route": route_file.id, "service": service_file.id, "repository": repo_file.id}


async def test_package_graph_reproduces_the_layered_example(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)
    await _seed_layered_architecture(db_session, repository_id)

    view = await graph_builder.build_package_graph(db_session, repository_id)

    node_ids = {n.id for n in view.nodes}
    assert node_ids == {
        "package:app/api/routes",
        "package:app/services",
        "package:app/repositories",
        graph_builder.DATABASE_NODE_ID,
    }
    edge_pairs = {(e.source, e.target) for e in view.edges}
    assert ("package:app/api/routes", "package:app/services") in edge_pairs
    assert ("package:app/services", "package:app/repositories") in edge_pairs
    assert ("package:app/repositories", graph_builder.DATABASE_NODE_ID) in edge_pairs

    services_node = next(n for n in view.nodes if n.id == "package:app/services")
    assert services_node.kind == "service"
    assert services_node.file_count == 1


async def test_module_graph_shows_files_and_collapsed_external_packages(
    db_session: AsyncSession,
) -> None:
    repository_id = await _create_repository(db_session)
    file_ids = await _seed_layered_architecture(db_session, repository_id)

    view = await graph_builder.build_module_graph(db_session, repository_id, "app/services")

    file_node = next(n for n in view.nodes if n.file_id == file_ids["service"])
    assert file_node.label == "AuthService"  # dominant class name, not "auth_service.py"
    assert file_node.symbol_count == 2  # the class + its method

    package_node_ids = {n.id for n in view.nodes if n.node_type == "package"}
    assert package_node_ids == {"package:app/api/routes", "package:app/repositories"}

    edge_pairs = {(e.source, e.target) for e in view.edges}
    assert ("package:app/api/routes", f"file:{file_ids['service']}") in edge_pairs
    assert (f"file:{file_ids['service']}", "package:app/repositories") in edge_pairs


async def test_module_graph_for_unknown_package_is_empty(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)
    await _seed_layered_architecture(db_session, repository_id)

    view = await graph_builder.build_module_graph(db_session, repository_id, "does/not/exist")

    assert view.nodes == []
    assert view.edges == []


async def test_file_detail_shows_symbols_dependencies_and_dependents(
    db_session: AsyncSession,
) -> None:
    repository_id = await _create_repository(db_session)
    file_ids = await _seed_layered_architecture(db_session, repository_id)

    detail = await graph_builder.get_file_detail(db_session, repository_id, file_ids["service"])

    assert detail is not None
    assert detail.path == "app/services/auth_service.py"
    assert detail.kind == "service"
    assert {s.name for s in detail.symbols} == {"AuthService", "login"}
    assert [d.path for d in detail.dependencies] == ["app/repositories/user_repository.py"]
    assert [d.path for d in detail.dependents] == ["app/api/routes/auth.py"]


async def test_file_detail_returns_none_for_unknown_file(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)

    detail = await graph_builder.get_file_detail(db_session, repository_id, uuid.uuid4())

    assert detail is None


async def test_search_matches_by_path_and_by_symbol_name(db_session: AsyncSession) -> None:
    repository_id = await _create_repository(db_session)
    await _seed_layered_architecture(db_session, repository_id)

    by_path = await graph_builder.search_nodes(db_session, repository_id, "auth")
    assert {r.path for r in by_path} == {
        "app/api/routes/auth.py",
        "app/services/auth_service.py",
    }

    by_symbol = await graph_builder.search_nodes(db_session, repository_id, "UserRepository")
    assert len(by_symbol) == 1
    assert by_symbol[0].path == "app/repositories/user_repository.py"
    assert by_symbol[0].matched_symbol_name == "UserRepository"


async def test_dependency_graph_never_creates_a_self_edge(db_session: AsyncSession) -> None:
    """A file that imports its own module name (e.g. a re-export, or a
    relative self-reference some tooling produces) must not depend on
    itself in the graph."""
    repository_id = await _create_repository(db_session)
    code_file_repository.create(
        db_session,
        repository_id=repository_id,
        path="app/services/auth_service.py",
        language="python",
        size_bytes=10,
        content_hash="a" * 64,
        commit_sha="f" * 40,
        imports=[{"text": "from app.services import auth_service", "line": 1}],
        indexed_at=datetime.now(UTC),
    )
    await db_session.commit()

    view = await graph_builder.build_package_graph(db_session, repository_id)

    assert view.edges == []
