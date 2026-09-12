"""File discovery: walks a checked-out repository, applies .gitignore-style
ignore rules plus a hardcoded denylist, and filters out binaries and
oversized files before anything reaches the parser."""

from dataclasses import dataclass
from pathlib import Path

import pathspec
from pathspec.pattern import Pattern

from app.indexing.languages import detect_language

# Directories that are never source-relevant regardless of .gitignore
# contents (a repo without a .gitignore would otherwise dump its entire
# dependency tree into the index).
_DENYLIST_DIRS = {
    ".git",
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".turbo",
    "coverage",
    "target",
}

_NULL_BYTE_SCAN_SIZE = 8192


@dataclass(frozen=True, slots=True)
class DiscoveredFile:
    path: str  # relative to repo root, forward-slash separated
    absolute_path: Path
    size_bytes: int
    language: str | None


def _load_ignore_spec(repo_root: Path) -> pathspec.PathSpec[Pattern]:
    gitignore = repo_root / ".gitignore"
    lines = gitignore.read_text(errors="ignore").splitlines() if gitignore.exists() else []
    return pathspec.PathSpec.from_lines("gitignore", lines)


def _looks_binary(path: Path) -> bool:
    try:
        with path.open("rb") as f:
            chunk = f.read(_NULL_BYTE_SCAN_SIZE)
    except OSError:
        return True
    return b"\x00" in chunk


def discover_files(
    repo_root: Path,
    *,
    max_file_size_bytes: int,
    max_files: int,
) -> list[DiscoveredFile]:
    """Walk `repo_root` and return every file worth indexing.

    Excludes: denylisted directories, gitignored paths, binaries, and files
    over `max_file_size_bytes`. Stops (without erroring) at `max_files` —
    callers surface how many were skipped via len(all candidates) - len(result)
    at the pipeline level.
    """
    ignore_spec = _load_ignore_spec(repo_root)
    discovered: list[DiscoveredFile] = []

    for candidate in sorted(repo_root.rglob("*")):
        if not candidate.is_file():
            continue
        relative = candidate.relative_to(repo_root)
        if _DENYLIST_DIRS & set(relative.parts[:-1]):
            continue
        relative_posix = relative.as_posix()
        if ignore_spec.match_file(relative_posix):
            continue
        try:
            size_bytes = candidate.stat().st_size
        except OSError:
            continue
        if size_bytes == 0 or size_bytes > max_file_size_bytes:
            continue
        if _looks_binary(candidate):
            continue
        discovered.append(
            DiscoveredFile(
                path=relative_posix,
                absolute_path=candidate,
                size_bytes=size_bytes,
                language=detect_language(relative_posix),
            )
        )
        if len(discovered) >= max_files:
            break

    return discovered
