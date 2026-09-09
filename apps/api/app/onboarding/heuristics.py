"""Deterministic repository-understanding heuristics that don't belong in
app/architecture/graph_builder.py (which owns the dependency graph itself)
but build on its output: entry-point detection, auth-file detection,
database-structure listing, and the learning-path ordering. All by
filename/path/symbol-name convention — the same class of heuristic as
app/architecture/classifier.py, with the same honestly-scoped limitation:
a repository that doesn't follow common conventions won't be recognized.
"""

import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from app.architecture.classifier import classify_path
from app.architecture.types import FileRanking
from app.domain.code_file import CodeFile
from app.domain.code_symbol import CodeSymbol

_ENTRY_POINT_CANDIDATES = (
    "main.py",
    "app.py",
    "manage.py",
    "__main__.py",
    "asgi.py",
    "wsgi.py",
    "index.ts",
    "index.js",
    "server.ts",
    "server.js",
    "main.go",
)

_AUTH_MARKERS = ("auth", "login", "session", "token", "oauth", "jwt")

_DATABASE_KINDS = ("model", "repository")

_README_NAMES = ("README.md", "README.rst", "README.txt", "README")


@dataclass(frozen=True, slots=True)
class DatabaseStructureEntry:
    path: str
    class_name: str
    symbol_type: str


@dataclass(frozen=True, slots=True)
class LearningPathStep:
    step: int
    label: str
    path: str | None
    reason: str


def find_readme(files: list[CodeFile]) -> CodeFile | None:
    by_name = {Path(f.path).name: f for f in files if "/" not in f.path}
    for name in _README_NAMES:
        if name in by_name:
            return by_name[name]
    # Fall back to a case-insensitive, any-depth match — READMEs sometimes
    # live in a docs/ or repo-root variant this indexer still picked up.
    for f in files:
        if Path(f.path).name.lower().startswith("readme"):
            return f
    return None


def find_entry_point(files: list[CodeFile]) -> CodeFile | None:
    by_name: dict[str, list[CodeFile]] = defaultdict(list)
    for f in files:
        by_name[Path(f.path).name].append(f)
    for candidate in _ENTRY_POINT_CANDIDATES:
        matches = by_name.get(candidate)
        if matches:
            return min(matches, key=lambda f: f.path.count("/"))
    return None


def find_auth_files(
    files: list[CodeFile], symbols_by_file: dict[uuid.UUID, list[CodeSymbol]]
) -> list[CodeFile]:
    matches: list[CodeFile] = []
    for f in files:
        path_lower = f.path.lower()
        if any(marker in path_lower for marker in _AUTH_MARKERS):
            matches.append(f)
            continue
        if any(
            marker in symbol.name.lower()
            for symbol in symbols_by_file.get(f.id, [])
            for marker in _AUTH_MARKERS
        ):
            matches.append(f)
    matches.sort(key=lambda f: f.path)
    return matches


def find_database_structure(
    files: list[CodeFile], symbols_by_file: dict[uuid.UUID, list[CodeSymbol]]
) -> list[DatabaseStructureEntry]:
    entries: list[DatabaseStructureEntry] = []
    for f in files:
        if classify_path(f.path) not in _DATABASE_KINDS:
            continue
        for symbol in symbols_by_file.get(f.id, []):
            if symbol.symbol_type in ("class", "interface", "struct", "type"):
                entries.append(
                    DatabaseStructureEntry(
                        path=f.path, class_name=symbol.name, symbol_type=symbol.symbol_type
                    )
                )
    return entries


def build_learning_path(
    *,
    readme: CodeFile | None,
    entry_point: CodeFile | None,
    auth_files: list[CodeFile],
    file_rankings: list[FileRanking],
) -> list[LearningPathStep]:
    """Fixed, framework-agnostic categories (matching the brief's own
    "START HERE" example), each populated with whichever real file in
    *this* repository best matches — and skipped entirely when no such
    file exists, rather than filled in with a guess."""
    steps: list[LearningPathStep] = []
    used_paths: set[str] = set()

    def add(label: str, path: str | None, reason: str) -> None:
        if path is not None:
            if path in used_paths:
                return
            used_paths.add(path)
        steps.append(LearningPathStep(step=len(steps) + 1, label=label, path=path, reason=reason))

    if readme is not None:
        add("README", readme.path, "Start with the project's own description of itself.")
    if entry_point is not None:
        add(
            "Application entry point",
            entry_point.path,
            "Where the application boots up and wires its pieces together.",
        )
    if auth_files:
        add(
            "Authentication module",
            auth_files[0].path,
            "How users are identified and requests are authorized.",
        )

    by_kind: dict[str, list[FileRanking]] = defaultdict(list)
    for ranking in file_rankings:
        by_kind[ranking.kind].append(ranking)

    database_candidates = by_kind.get("repository") or by_kind.get("model") or []
    if database_candidates:
        top = database_candidates[0]
        add("Database layer", top.path, f"The most-depended-on data-access file ({top.label}).")

    route_candidates = by_kind.get("route") or []
    if route_candidates:
        top = route_candidates[0]
        add("API routing", top.path, f"The most-depended-on route module ({top.label}).")

    # One more real, central "service" file beyond what's already listed —
    # the brief's own example ends on "Payment service": whatever this
    # repository's own most-depended-on service module actually is.
    service_candidates = [r for r in by_kind.get("service") or [] if r.path not in used_paths]
    if service_candidates:
        top = service_candidates[0]
        add(
            f"{top.label}",
            top.path,
            f"The most-depended-on service module in this repository ({top.dependents_count} "
            "files depend on it).",
        )

    return steps
