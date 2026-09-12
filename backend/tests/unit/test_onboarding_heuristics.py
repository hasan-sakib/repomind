import uuid
from datetime import UTC, datetime

from app.architecture.types import FileRanking
from app.models.code_file import CodeFile
from app.models.code_symbol import CodeSymbol
from app.onboarding import heuristics


def _file(path: str) -> CodeFile:
    return CodeFile(
        id=uuid.uuid4(),
        repository_id=uuid.uuid4(),
        path=path,
        language="python",
        size_bytes=10,
        content_hash="a" * 64,
        commit_sha="f" * 40,
        imports=[],
        indexed_at=datetime.now(UTC),
    )


def _symbol(file_id: uuid.UUID, name: str, symbol_type: str = "class") -> CodeSymbol:
    return CodeSymbol(
        id=uuid.uuid4(),
        file_id=file_id,
        symbol_type=symbol_type,
        name=name,
        start_line=1,
        end_line=10,
        signature=None,
        docstring=None,
        parent_symbol_id=None,
    )


def test_find_readme_prefers_root_level_readme_md() -> None:
    files = [_file("docs/readme.txt"), _file("README.md"), _file("app/main.py")]
    assert heuristics.find_readme(files).path == "README.md"


def test_find_readme_falls_back_to_any_readme_like_name() -> None:
    files = [_file("docs/README.rst")]
    assert heuristics.find_readme(files).path == "docs/README.rst"


def test_find_readme_returns_none_when_absent() -> None:
    assert heuristics.find_readme([_file("app/main.py")]) is None


def test_find_entry_point_matches_known_candidate_filenames() -> None:
    files = [_file("app/utils.py"), _file("app/main.py")]
    assert heuristics.find_entry_point(files).path == "app/main.py"


def test_find_entry_point_prefers_shallowest_match() -> None:
    files = [_file("scripts/tools/main.py"), _file("main.py")]
    assert heuristics.find_entry_point(files).path == "main.py"


def test_find_entry_point_returns_none_when_no_candidate_matches() -> None:
    assert heuristics.find_entry_point([_file("app/utils.py")]) is None


def test_find_auth_files_matches_by_path() -> None:
    files = [_file("app/services/auth_service.py"), _file("app/services/billing.py")]
    matches = heuristics.find_auth_files(files, {})
    assert [f.path for f in matches] == ["app/services/auth_service.py"]


def test_find_auth_files_matches_by_symbol_name() -> None:
    billing_file = _file("app/services/billing.py")
    login_symbol = _symbol(billing_file.id, "handle_login")
    matches = heuristics.find_auth_files([billing_file], {billing_file.id: [login_symbol]})
    assert [f.path for f in matches] == ["app/services/billing.py"]


def test_find_auth_files_returns_empty_when_nothing_matches() -> None:
    files = [_file("app/services/billing.py")]
    assert heuristics.find_auth_files(files, {}) == []


def test_find_database_structure_lists_model_and_repository_classes() -> None:
    model_file = _file("app/models/user.py")
    repo_file = _file("app/repositories/user_repository.py")
    route_file = _file("app/api/routes/auth.py")
    user_class = _symbol(model_file.id, "User")
    repo_class = _symbol(repo_file.id, "UserRepository")
    route_class = _symbol(route_file.id, "AuthController")
    symbols_by_file = {
        model_file.id: [user_class],
        repo_file.id: [repo_class],
        route_file.id: [route_class],
    }
    entries = heuristics.find_database_structure(
        [model_file, repo_file, route_file], symbols_by_file
    )
    assert {(e.path, e.class_name) for e in entries} == {
        ("app/models/user.py", "User"),
        ("app/repositories/user_repository.py", "UserRepository"),
    }


def test_find_database_structure_skips_non_class_symbols() -> None:
    model_file = _file("app/models/user.py")
    method_symbol = _symbol(model_file.id, "validate", symbol_type="method")
    entries = heuristics.find_database_structure([model_file], {model_file.id: [method_symbol]})
    assert entries == []


def test_build_learning_path_includes_only_whats_found() -> None:
    path = heuristics.build_learning_path(
        readme=None, entry_point=None, auth_files=[], file_rankings=[]
    )
    assert path == []


def test_build_learning_path_matches_the_briefs_example_shape() -> None:
    readme = _file("README.md")
    entry_point = _file("app/main.py")
    auth_file = _file("app/services/auth_service.py")
    rankings = [
        FileRanking(
            file_id=uuid.uuid4(),
            path="app/repositories/user_repository.py",
            label="UserRepository",
            kind="repository",
            dependents_count=5,
        ),
        FileRanking(
            file_id=uuid.uuid4(),
            path="app/api/routes/auth.py",
            label="AuthController",
            kind="route",
            dependents_count=3,
        ),
        FileRanking(
            file_id=uuid.uuid4(),
            path="app/services/payment_service.py",
            label="PaymentService",
            kind="service",
            dependents_count=8,
        ),
    ]

    path = heuristics.build_learning_path(
        readme=readme, entry_point=entry_point, auth_files=[auth_file], file_rankings=rankings
    )

    labels = [step.label for step in path]
    assert labels == [
        "README",
        "Application entry point",
        "Authentication module",
        "Database layer",
        "API routing",
        "PaymentService",
    ]
    assert [step.step for step in path] == list(range(1, len(path) + 1))


def test_build_learning_path_never_repeats_the_same_path() -> None:
    # The auth file IS this repository's most-central "service" file too —
    # it must appear once, not twice.
    auth_file = _file("app/services/auth_service.py")
    rankings = [
        FileRanking(
            file_id=uuid.uuid4(),
            path="app/services/auth_service.py",
            label="AuthService",
            kind="service",
            dependents_count=10,
        )
    ]
    path = heuristics.build_learning_path(
        readme=None, entry_point=None, auth_files=[auth_file], file_rankings=rankings
    )
    paths = [step.path for step in path]
    assert paths.count("app/services/auth_service.py") == 1
