from app.onboarding.setup import detect_setup_steps, find_shallowest


def test_find_shallowest_prefers_root_level_match() -> None:
    paths = {"apps/api/pyproject.toml", "pyproject.toml", "apps/web/pyproject.toml"}
    assert find_shallowest(paths, "pyproject.toml") == "pyproject.toml"


def test_find_shallowest_falls_back_to_nested_match() -> None:
    paths = {"apps/api/pyproject.toml", "apps/web/package.json"}
    assert find_shallowest(paths, "pyproject.toml") == "apps/api/pyproject.toml"


def test_find_shallowest_returns_none_when_absent() -> None:
    assert find_shallowest({"README.md"}, "go.mod") is None


def test_detect_setup_steps_always_includes_clone() -> None:
    steps = detect_setup_steps(set())
    assert steps[0].description == "Clone the repository"
    assert len(steps) == 1


def test_detect_python_uv_setup() -> None:
    steps = detect_setup_steps({"pyproject.toml", "uv.lock"})
    install = next(s for s in steps if "Python" in s.description)
    assert install.command == "uv sync"


def test_detect_python_pip_setup_without_uv_lock() -> None:
    steps = detect_setup_steps({"pyproject.toml"})
    install = next(s for s in steps if "Python" in s.description)
    assert install.command == "pip install -e ."


def test_detect_requirements_txt_setup() -> None:
    steps = detect_setup_steps({"requirements.txt"})
    install = next(s for s in steps if "Python" in s.description)
    assert install.command == "pip install -r requirements.txt"


def test_pyproject_takes_precedence_over_requirements_txt() -> None:
    steps = detect_setup_steps({"pyproject.toml", "uv.lock", "requirements.txt"})
    python_steps = [s for s in steps if "Python" in s.description]
    assert len(python_steps) == 1
    assert python_steps[0].command == "uv sync"


def test_detect_pnpm_setup() -> None:
    steps = detect_setup_steps({"package.json", "pnpm-lock.yaml"})
    install = next(s for s in steps if "JavaScript" in s.description)
    assert install.command == "pnpm install"


def test_detect_npm_setup_without_a_lockfile() -> None:
    steps = detect_setup_steps({"package.json"})
    install = next(s for s in steps if "JavaScript" in s.description)
    assert install.command == "npm install"


def test_detect_monorepo_nested_manifest_prefixes_cd() -> None:
    steps = detect_setup_steps({"apps/api/pyproject.toml", "apps/api/uv.lock"})
    install = next(s for s in steps if "Python" in s.description)
    assert install.command == "cd apps/api && uv sync"


def test_detect_env_example() -> None:
    steps = detect_setup_steps({".env.example"})
    env_step = next(s for s in steps if "environment" in s.description.lower())
    assert env_step.command == "cp .env.example .env"


def test_detect_docker_compose() -> None:
    steps = detect_setup_steps({"docker-compose.yml"})
    assert any(s.command == "docker compose up -d" for s in steps)


def test_detect_migrations_only_alongside_pyproject() -> None:
    # A migrations/ directory with no pyproject.toml has nothing to run
    # alembic *with* — no step should be invented.
    steps = detect_setup_steps({"migrations/0001_init.py"})
    assert not any("migration" in s.description.lower() for s in steps)


def test_detect_migrations_alongside_pyproject() -> None:
    steps = detect_setup_steps({"pyproject.toml", "migrations/0001_init.py"})
    assert any("migration" in s.description.lower() for s in steps)


def test_no_recognized_files_yields_only_clone_step() -> None:
    steps = detect_setup_steps({"README.md", "LICENSE"})
    assert len(steps) == 1


def test_steps_are_sequentially_ordered() -> None:
    steps = detect_setup_steps({"pyproject.toml", "uv.lock", "package.json", "docker-compose.yml"})
    assert [s.order for s in steps] == list(range(1, len(steps) + 1))
