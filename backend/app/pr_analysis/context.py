"""Deterministic, non-LLM data gathering for one PR's analysis: resolves
each changed file against our indexed CodeFile/CodeSymbol rows, finds
which symbols the diff actually touches (via diff_parser), which other
files depend on those symbols (reusing app/retrieval/dependency_graph.py's
import-matching from ADR 0005), and which existing test files already
reference them.

The LLM (app/pr_analysis/prompt.py) only ever sees paths gathered here —
result_schema.py validates every citation in its output against
`PRAnalysisContext.valid_file_paths()`, dropping anything the model
invents. See docs/architecture/0007-ai-pull-request-intelligence.md.
"""

import re
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.architecture.classifier import NodeKind, classify_path
from app.domain.code_file import CodeFile
from app.domain.code_symbol import CodeSymbol
from app.integrations.github.schemas import GitHubPullRequestFile
from app.pr_analysis.diff_parser import parse_patch_added_lines
from app.retrieval.dependency_graph import find_dependents

_TEST_PATH_MARKERS = ("test_", "_test.", ".test.", ".spec.", "/tests/", "/test/")
_MAX_DEPENDENTS_PER_FILE = 8
_MAX_RELATED_TESTS = 10
_MAX_SEARCH_NAMES_PER_FILE = 5  # bounds dependency/test lookups for a huge diff


@dataclass(frozen=True, slots=True)
class ChangedSymbolRef:
    name: str
    symbol_type: str
    start_line: int
    end_line: int


@dataclass(frozen=True, slots=True)
class DependentRef:
    path: str
    matched_name: str


@dataclass(frozen=True, slots=True)
class ChangedFileContext:
    path: str
    status: str
    additions: int
    deletions: int
    kind: NodeKind
    indexed: bool
    patch_excerpt: str | None
    changed_symbols: list[ChangedSymbolRef]
    dependents: list[DependentRef]


@dataclass(frozen=True, slots=True)
class RelatedTestRef:
    path: str
    matched_path: str  # which changed file this test appears related to


@dataclass(frozen=True, slots=True)
class PRAnalysisContext:
    changed_files: list[ChangedFileContext]
    related_tests: list[RelatedTestRef]

    def valid_file_paths(self) -> set[str]:
        """Every path the LLM was actually shown — the only paths its
        output is allowed to cite (see result_schema.py)."""
        paths = {f.path for f in self.changed_files}
        paths.update(t.path for t in self.related_tests)
        return paths


def _is_test_path(path: str) -> bool:
    lowered = path.lower()
    return any(marker in lowered for marker in _TEST_PATH_MARKERS)


async def build_context(
    db: AsyncSession,
    *,
    repository_id: uuid.UUID,
    files: list[GitHubPullRequestFile],
    max_patch_chars: int,
) -> PRAnalysisContext:
    all_files = list(
        (
            await db.execute(select(CodeFile).where(CodeFile.repository_id == repository_id))
        ).scalars()
    )
    file_by_path = {f.path: f for f in all_files}
    test_files = [f for f in all_files if _is_test_path(f.path)]

    symbols_by_file_id: dict[uuid.UUID, list[CodeSymbol]] = {}
    symbol_rows = await db.execute(
        select(CodeSymbol)
        .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        .where(CodeFile.repository_id == repository_id)
    )
    for symbol in symbol_rows.scalars():
        symbols_by_file_id.setdefault(symbol.file_id, []).append(symbol)

    changed_contexts: list[ChangedFileContext] = []
    related_tests: dict[str, RelatedTestRef] = {}

    for gh_file in files:
        code_file = file_by_path.get(gh_file.filename)
        changed_symbols: list[ChangedSymbolRef] = []
        dependents: list[DependentRef] = []

        if code_file is not None:
            added_lines = parse_patch_added_lines(gh_file.patch)
            for symbol in symbols_by_file_id.get(code_file.id, []):
                if any(symbol.start_line <= line <= symbol.end_line for line in added_lines):
                    changed_symbols.append(
                        ChangedSymbolRef(
                            name=symbol.name,
                            symbol_type=symbol.symbol_type,
                            start_line=symbol.start_line,
                            end_line=symbol.end_line,
                        )
                    )

            search_names = list({s.name for s in changed_symbols})[:_MAX_SEARCH_NAMES_PER_FILE]
            if not search_names:
                search_names = [Path(gh_file.filename).stem]

            seen_dependent_paths: set[str] = set()
            for name in search_names:
                if len(dependents) >= _MAX_DEPENDENTS_PER_FILE:
                    break
                for chunk in await find_dependents(
                    db,
                    repository_id=repository_id,
                    symbol_name=name,
                    limit=_MAX_DEPENDENTS_PER_FILE,
                ):
                    if chunk.file_path is None or chunk.file_path == gh_file.filename:
                        continue
                    if chunk.file_path in seen_dependent_paths:
                        continue
                    seen_dependent_paths.add(chunk.file_path)
                    dependents.append(DependentRef(path=chunk.file_path, matched_name=name))

            for test_file in test_files:
                if len(related_tests) >= _MAX_RELATED_TESTS:
                    break
                if test_file.path in related_tests:
                    continue
                for record in test_file.imports:
                    if any(
                        re.search(rf"\b{re.escape(name)}\b", record["text"])
                        for name in search_names
                    ):
                        related_tests[test_file.path] = RelatedTestRef(
                            path=test_file.path, matched_path=gh_file.filename
                        )
                        break

        changed_contexts.append(
            ChangedFileContext(
                path=gh_file.filename,
                status=gh_file.status,
                additions=gh_file.additions,
                deletions=gh_file.deletions,
                kind=classify_path(gh_file.filename),
                indexed=code_file is not None,
                patch_excerpt=(gh_file.patch[:max_patch_chars] if gh_file.patch else None),
                changed_symbols=changed_symbols,
                dependents=dependents,
            )
        )

    return PRAnalysisContext(
        changed_files=changed_contexts, related_tests=list(related_tests.values())
    )
