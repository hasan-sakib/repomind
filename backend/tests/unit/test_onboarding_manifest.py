from app.onboarding.manifest import parse_manifest


def test_parses_package_json_dependencies() -> None:
    content = """{
      "name": "web",
      "dependencies": {"next": "^16.0.0", "react": "19.2.8"},
      "devDependencies": {"typescript": "^5.0.0"}
    }"""
    deps = parse_manifest("package.json", content)
    by_name = {d.name: d for d in deps}
    assert by_name["next"].version == "^16.0.0"
    assert by_name["next"].ecosystem == "npm"
    assert by_name["typescript"].ecosystem == "npm"


def test_malformed_package_json_yields_empty_list() -> None:
    assert parse_manifest("package.json", "{not valid json") == []


def test_parses_pep621_pyproject_dependencies() -> None:
    content = """
[project]
name = "api"
dependencies = ["fastapi>=0.115,<1.0", "pydantic[email]==2.5", "httpx"]
"""
    deps = parse_manifest("pyproject.toml", content)
    by_name = {d.name: d for d in deps}
    assert by_name["fastapi"].version == ">=0.115,<1.0"
    assert by_name["pydantic"].version == "==2.5"
    assert by_name["httpx"].version is None
    assert all(d.ecosystem == "python" for d in deps)


def test_parses_poetry_style_pyproject_dependencies() -> None:
    content = """
[tool.poetry.dependencies]
python = "^3.12"
requests = "^2.31"
sqlalchemy = {version = "^2.0", extras = ["asyncio"]}
"""
    deps = parse_manifest("pyproject.toml", content)
    by_name = {d.name: d for d in deps}
    assert "python" not in by_name  # the interpreter constraint, not a dependency
    assert by_name["requests"].version == "^2.31"
    assert by_name["sqlalchemy"].version == "^2.0"


def test_malformed_pyproject_toml_yields_empty_list() -> None:
    assert parse_manifest("pyproject.toml", "not = [valid toml") == []


def test_parses_requirements_txt() -> None:
    content = "fastapi>=0.115\n# a comment\n\nhttpx\n-e .\npydantic==2.5  # inline comment\n"
    deps = parse_manifest("requirements.txt", content)
    by_name = {d.name: d for d in deps}
    assert by_name["fastapi"].version == ">=0.115"
    assert by_name["httpx"].version is None
    assert by_name["pydantic"].version == "==2.5"
    assert len(deps) == 3


def test_parses_go_mod_require_block() -> None:
    content = """module example.com/widgets

go 1.22

require (
    github.com/gin-gonic/gin v1.9.1
    github.com/stretchr/testify v1.8.4 // indirect
)
"""
    deps = parse_manifest("go.mod", content)
    by_name = {d.name: d for d in deps}
    assert by_name["github.com/gin-gonic/gin"].version == "v1.9.1"
    assert by_name["github.com/stretchr/testify"].version == "v1.8.4"


def test_unrecognized_filename_yields_empty_list() -> None:
    assert parse_manifest("Cargo.toml", '[dependencies]\nserde = "1"') == []
