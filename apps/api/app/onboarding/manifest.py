"""Best-effort dependency-manifest parsing for the four ecosystems the
indexing pipeline already understands (Python, JavaScript/TypeScript, Go —
app/indexing/languages.py, ADR 0004). Deliberately not exhaustive: no
Cargo.toml/Gemfile/composer.json, since this indexer has no tree-sitter
grammar for Rust/Ruby/PHP either. Each parser is defensive about
malformed input — a manifest that fails to parse yields an empty list,
never an exception that would fail the whole onboarding guide over one
bad file.
"""

import json
import re
import tomllib
from dataclasses import dataclass

MANIFEST_FILENAMES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
)


@dataclass(frozen=True, slots=True)
class Dependency:
    name: str
    version: str | None
    ecosystem: str  # "npm" | "python" | "go"


def parse_manifest(filename: str, content: str) -> list[Dependency]:
    parsers = {
        "package.json": _parse_package_json,
        "pyproject.toml": _parse_pyproject_toml,
        "requirements.txt": _parse_requirements_txt,
        "go.mod": _parse_go_mod,
    }
    parser = parsers.get(filename)
    if parser is None:
        return []
    try:
        return parser(content)
    except (json.JSONDecodeError, tomllib.TOMLDecodeError, KeyError, TypeError, ValueError):
        return []


def _parse_package_json(content: str) -> list[Dependency]:
    data = json.loads(content)
    deps: list[Dependency] = []
    for section in ("dependencies", "devDependencies"):
        for name, version in (data.get(section) or {}).items():
            deps.append(Dependency(name=name, version=str(version), ecosystem="npm"))
    return deps


def _parse_pyproject_toml(content: str) -> list[Dependency]:
    data = tomllib.loads(content)
    deps: list[Dependency] = []

    # PEP 621 (`[project] dependencies = [...]`) — used by uv, and most
    # modern Python tooling this indexer would encounter.
    for entry in (data.get("project") or {}).get("dependencies") or []:
        name, version = _split_pep508(entry)
        deps.append(Dependency(name=name, version=version, ecosystem="python"))

    # Poetry (`[tool.poetry.dependencies]`) predates PEP 621 adoption and
    # is still common enough to be worth a second, narrower pass.
    poetry_deps = ((data.get("tool") or {}).get("poetry") or {}).get("dependencies") or {}
    for name, spec in poetry_deps.items():
        if name.lower() == "python":
            continue
        version = (
            spec
            if isinstance(spec, str)
            else spec.get("version")
            if isinstance(spec, dict)
            else None
        )
        deps.append(Dependency(name=name, version=version, ecosystem="python"))

    return deps


_PEP508_NAME = re.compile(r"^([A-Za-z0-9_.-]+)")


def _split_pep508(entry: str) -> tuple[str, str | None]:
    """`"fastapi>=0.115,<1.0"` -> ("fastapi", ">=0.115,<1.0"); a bare
    `"fastapi"` -> ("fastapi", None); `"pydantic[email]==2.5"` -> the
    `[email]` extras marker is stripped before the version spec."""
    entry = entry.strip()
    match = _PEP508_NAME.match(entry)
    if not match:
        return entry, None
    name = match.group(1)
    rest = entry[match.end() :]
    if rest.startswith("["):
        closing = rest.find("]")
        rest = rest[closing + 1 :] if closing != -1 else ""
    version_spec = rest.split(";", 1)[0].strip()
    return name, version_spec or None


def _parse_requirements_txt(content: str) -> list[Dependency]:
    deps: list[Dependency] = []
    for raw_line in content.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or line.startswith(("-r ", "-e ", "--")):
            continue
        name, version = _split_pep508(line)
        if name:
            deps.append(Dependency(name=name, version=version, ecosystem="python"))
    return deps


_GO_REQUIRE_LINE = re.compile(r"^\s*([^\s]+)\s+(v[\w.\-+]+)")


def _parse_go_mod(content: str) -> list[Dependency]:
    deps: list[Dependency] = []
    in_require_block = False
    for raw_line in content.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        if line.startswith("require ("):
            in_require_block = True
            continue
        if in_require_block and line == ")":
            in_require_block = False
            continue
        if in_require_block:
            match = _GO_REQUIRE_LINE.match(line)
            if match:
                deps.append(Dependency(name=match.group(1), version=match.group(2), ecosystem="go"))
        elif line.startswith("require "):
            match = _GO_REQUIRE_LINE.match(line.removeprefix("require ").strip())
            if match:
                deps.append(Dependency(name=match.group(1), version=match.group(2), ecosystem="go"))
    return deps
