"""Deterministic, presence-based development-setup step detection — a
step is only ever included because a specific file was actually found in
the repository's indexed file list, never invented or assumed. No LLM
involved: "how do I install this project's dependencies" has a small,
well-known set of correct answers per detected tool, not something worth
asking a model to guess at."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class SetupStep:
    order: int
    description: str
    command: str | None
    detected_from: str


def find_shallowest(file_paths: set[str], name: str) -> str | None:
    """The shallowest path whose basename is `name` — handles a manifest
    that lives in a subdirectory (a monorepo's `apps/api/pyproject.toml`),
    not just a repository-root one."""
    matches = [p for p in file_paths if Path(p).name == name]
    return min(matches, key=lambda p: p.count("/")) if matches else None


def _cd_prefix(path: str) -> str:
    directory = str(Path(path).parent)
    return "" if directory in ("", ".") else f"cd {directory} && "


def detect_setup_steps(file_paths: set[str]) -> list[SetupStep]:
    steps: list[SetupStep] = [SetupStep(1, "Clone the repository", None, "—")]
    order = 2

    pyproject = find_shallowest(file_paths, "pyproject.toml")
    if pyproject is not None:
        cd = _cd_prefix(pyproject)
        if find_shallowest(file_paths, "uv.lock") is not None:
            command = f"{cd}uv sync"
        else:
            command = f"{cd}pip install -e ."
        steps.append(SetupStep(order, "Install Python dependencies", command, pyproject))
        order += 1
    else:
        requirements = find_shallowest(file_paths, "requirements.txt")
        if requirements is not None:
            cd = _cd_prefix(requirements)
            steps.append(
                SetupStep(
                    order,
                    "Install Python dependencies",
                    f"{cd}pip install -r requirements.txt",
                    requirements,
                )
            )
            order += 1

    package_json = find_shallowest(file_paths, "package.json")
    if package_json is not None:
        cd = _cd_prefix(package_json)
        if find_shallowest(file_paths, "pnpm-lock.yaml") is not None:
            command, detected = f"{cd}pnpm install", f"{package_json} + pnpm-lock.yaml"
        elif find_shallowest(file_paths, "yarn.lock") is not None:
            command, detected = f"{cd}yarn install", f"{package_json} + yarn.lock"
        else:
            command, detected = f"{cd}npm install", package_json
        steps.append(SetupStep(order, "Install JavaScript dependencies", command, detected))
        order += 1

    go_mod = find_shallowest(file_paths, "go.mod")
    if go_mod is not None:
        cd = _cd_prefix(go_mod)
        steps.append(SetupStep(order, "Install Go dependencies", f"{cd}go mod download", go_mod))
        order += 1

    env_example = find_shallowest(file_paths, ".env.example") or find_shallowest(
        file_paths, ".env.sample"
    )
    if env_example is not None:
        cd = _cd_prefix(env_example)
        target = Path(env_example).name.replace(".example", "").replace(".sample", "")
        steps.append(
            SetupStep(
                order,
                "Copy the environment template",
                f"{cd}cp {Path(env_example).name} {target}",
                env_example,
            )
        )
        order += 1

    compose_file = find_shallowest(file_paths, "docker-compose.yml") or find_shallowest(
        file_paths, "docker-compose.yaml"
    )
    if compose_file is not None:
        cd = _cd_prefix(compose_file)
        steps.append(
            SetupStep(
                order,
                "Start local services (database, cache, ...)",
                f"{cd}docker compose up -d",
                compose_file,
            )
        )
        order += 1

    migrations_dir = next(
        (p for p in file_paths if "/alembic/" in f"/{p}" or "/migrations/" in f"/{p}"), None
    )
    if migrations_dir is not None and pyproject is not None:
        cd = _cd_prefix(pyproject)
        steps.append(
            SetupStep(order, "Run database migrations", f"{cd}alembic upgrade head", migrations_dir)
        )
        order += 1

    makefile = find_shallowest(file_paths, "Makefile")
    if makefile is not None:
        cd = _cd_prefix(makefile)
        steps.append(
            SetupStep(
                order,
                "Check the Makefile for project-specific commands",
                f"{cd}make help",
                makefile,
            )
        )
        order += 1

    return steps
