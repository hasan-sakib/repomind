"""Builds the architecture/dependency graph entirely from data the
indexing pipeline already stores (app/indexing/pipeline.py) — no new
tables, no separate analysis pass. See
docs/architecture/0006-architecture-dependency-graph.md for the full
algorithm description and its honestly-scoped limitations.

In short: two levels of aggregation over one underlying file-level import
graph.
  - "package" level: one node per directory, edges aggregated from every
    file-pair edge whose files live in different directories.
  - "module" level: one node per file within a single requested package,
    edges between them, plus collapsed single-node edges to/from every
    *other* package a file in this one touches.
A synthetic "database" node represents PostgreSQL: any file classified
as "repository" or "model" (app/architecture/classifier.py) gets an edge
to it, matching the brief's own example (UserRepository -> PostgreSQL).
"""

import re
import uuid
from collections import defaultdict
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.architecture.classifier import NodeKind, classify_path
from app.architecture.types import (
    DependencyRef,
    FileDetail,
    FileRanking,
    GraphEdge,
    GraphNode,
    GraphView,
    SearchResult,
    SymbolSummary,
)
from app.domain.code_file import CodeFile
from app.domain.code_symbol import CodeSymbol

DATABASE_NODE_ID = "database"

_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
# Language keywords that show up in import statements across the
# languages this pipeline indexes (app/indexing/languages.py) — stripped
# so they never get matched against a file/symbol name by coincidence.
_STOPWORDS = {
    "import",
    "from",
    "as",
    "export",
    "default",
    "const",
    "let",
    "var",
    "type",
    "interface",
    "package",
    "func",
    "require",
    "use",
    "pub",
    "mod",
    "static",
    "final",
}


def _package_of(path: str) -> str:
    return str(Path(path).parent) if "/" in path else ""


def _package_label(package: str) -> str:
    return package.rsplit("/", 1)[-1] if package else "(root)"


def _referenced_names(import_text: str) -> set[str]:
    return {token for token in _IDENTIFIER.findall(import_text) if token not in _STOPWORDS}


async def _load_files(db: AsyncSession, repository_id: uuid.UUID) -> list[CodeFile]:
    result = await db.execute(select(CodeFile).where(CodeFile.repository_id == repository_id))
    return list(result.scalars().all())


async def _load_symbols(db: AsyncSession, repository_id: uuid.UUID) -> list[CodeSymbol]:
    result = await db.execute(
        select(CodeSymbol)
        .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        .where(CodeFile.repository_id == repository_id)
    )
    return list(result.scalars().all())


def _build_name_index(
    files: list[CodeFile], symbols: list[CodeSymbol]
) -> dict[str, set[uuid.UUID]]:
    """Every name that could plausibly appear in an import statement and
    resolve to a file in this repository: each file's own module name
    (its filename without extension), and every symbol defined in it."""
    index: dict[str, set[uuid.UUID]] = defaultdict(set)
    for file in files:
        index[Path(file.path).stem].add(file.id)
    for symbol in symbols:
        index[symbol.name].add(symbol.file_id)
    return index


def _resolve_import_edges(
    files: list[CodeFile], name_index: dict[str, set[uuid.UUID]]
) -> list[tuple[uuid.UUID, uuid.UUID, str]]:
    """Every (source_file, target_file, matched_name) triple implied by
    source_file's recorded imports — not deduped or aggregated, so a
    caller can either count them (graph edge weight) or inspect which
    specific name explains one file's dependency on another (file detail)."""
    edges: list[tuple[uuid.UUID, uuid.UUID, str]] = []
    for file in files:
        for import_record in file.imports:
            for name in _referenced_names(import_record["text"]):
                for target_id in name_index.get(name, ()):
                    if target_id != file.id:
                        edges.append((file.id, target_id, name))
    return edges


def _dominant_label(path: str, symbols: list[CodeSymbol]) -> str:
    """ "AuthService", not "auth_service.py" — the brief's own example
    names a file by its dominant class, not its filename. Falls back to
    the filename for files with no class-like symbol (e.g. a route
    module that's just a handful of top-level functions)."""
    class_like = [s for s in symbols if s.symbol_type in ("class", "interface", "struct", "type")]
    if class_like:
        dominant = max(class_like, key=lambda s: s.end_line - s.start_line)
        return dominant.name
    return Path(path).stem


async def build_package_graph(db: AsyncSession, repository_id: uuid.UUID) -> GraphView:
    files = await _load_files(db, repository_id)
    symbols = await _load_symbols(db, repository_id)
    name_index = _build_name_index(files, symbols)
    raw_edges = _resolve_import_edges(files, name_index)

    package_of_file = {file.id: _package_of(file.path) for file in files}
    files_by_package: dict[str, list[CodeFile]] = defaultdict(list)
    for file in files:
        files_by_package[package_of_file[file.id]].append(file)

    package_edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    for src, dst, _name in raw_edges:
        src_pkg, dst_pkg = package_of_file[src], package_of_file[dst]
        if src_pkg != dst_pkg:
            package_edge_weights[(src_pkg, dst_pkg)] += 1

    database_edge_weights: dict[str, int] = defaultdict(int)
    for file in files:
        if classify_path(file.path) in ("repository", "model"):
            database_edge_weights[package_of_file[file.id]] += 1

    nodes = [
        GraphNode(
            id=f"package:{package}",
            node_type="package",
            label=_package_label(package),
            kind=classify_path(package),
            path=package,
            file_count=len(package_files),
        )
        for package, package_files in files_by_package.items()
    ]
    if database_edge_weights:
        nodes.append(
            GraphNode(id=DATABASE_NODE_ID, node_type="database", label="Database", kind="database")
        )

    edges = [
        GraphEdge(source=f"package:{src}", target=f"package:{dst}", weight=weight)
        for (src, dst), weight in package_edge_weights.items()
    ]
    edges += [
        GraphEdge(source=f"package:{package}", target=DATABASE_NODE_ID, weight=weight)
        for package, weight in database_edge_weights.items()
    ]
    return GraphView(nodes=nodes, edges=edges)


async def build_module_graph(db: AsyncSession, repository_id: uuid.UUID, package: str) -> GraphView:
    files = await _load_files(db, repository_id)
    symbols = await _load_symbols(db, repository_id)
    name_index = _build_name_index(files, symbols)
    raw_edges = _resolve_import_edges(files, name_index)

    package_of_file = {file.id: _package_of(file.path) for file in files}
    symbols_by_file: dict[uuid.UUID, list[CodeSymbol]] = defaultdict(list)
    for symbol in symbols:
        symbols_by_file[symbol.file_id].append(symbol)

    package_files = [f for f in files if package_of_file[f.id] == package]
    package_file_ids = {f.id for f in package_files}

    edge_weights: dict[tuple[str, str], int] = defaultdict(int)
    external_packages: set[str] = set()
    for src, dst, _name in raw_edges:
        src_in, dst_in = src in package_file_ids, dst in package_file_ids
        if src_in and dst_in:
            edge_weights[(f"file:{src}", f"file:{dst}")] += 1
        elif src_in:
            other = package_of_file[dst]
            external_packages.add(other)
            edge_weights[(f"file:{src}", f"package:{other}")] += 1
        elif dst_in:
            other = package_of_file[src]
            external_packages.add(other)
            edge_weights[(f"package:{other}", f"file:{dst}")] += 1

    database_referenced = False
    for file in package_files:
        if classify_path(file.path) in ("repository", "model"):
            edge_weights[(f"file:{file.id}", DATABASE_NODE_ID)] += 1
            database_referenced = True

    nodes = [
        GraphNode(
            id=f"file:{file.id}",
            node_type="file",
            label=_dominant_label(file.path, symbols_by_file.get(file.id, [])),
            kind=classify_path(file.path),
            path=file.path,
            file_id=file.id,
            language=file.language,
            symbol_count=len(symbols_by_file.get(file.id, [])),
        )
        for file in package_files
    ]
    nodes += [
        GraphNode(
            id=f"package:{other}",
            node_type="package",
            label=_package_label(other),
            kind=classify_path(other),
            path=other,
        )
        for other in external_packages
    ]
    if database_referenced:
        nodes.append(
            GraphNode(id=DATABASE_NODE_ID, node_type="database", label="Database", kind="database")
        )

    edges = [
        GraphEdge(source=src, target=dst, weight=weight)
        for (src, dst), weight in edge_weights.items()
    ]
    return GraphView(nodes=nodes, edges=edges)


async def get_file_detail(
    db: AsyncSession, repository_id: uuid.UUID, file_id: uuid.UUID
) -> FileDetail | None:
    files = await _load_files(db, repository_id)
    file_by_id = {file.id: file for file in files}
    target = file_by_id.get(file_id)
    if target is None:
        return None

    symbols = await _load_symbols(db, repository_id)
    symbols_by_file: dict[uuid.UUID, list[CodeSymbol]] = defaultdict(list)
    for symbol in symbols:
        symbols_by_file[symbol.file_id].append(symbol)

    name_index = _build_name_index(files, symbols)
    raw_edges = _resolve_import_edges(files, name_index)

    dependencies: dict[uuid.UUID, str] = {}
    dependents: dict[uuid.UUID, str] = {}
    for src, dst, name in raw_edges:
        if src == file_id and dst not in dependencies and dst in file_by_id:
            dependencies[dst] = name
        if dst == file_id and src not in dependents and src in file_by_id:
            dependents[src] = name

    return FileDetail(
        file_id=target.id,
        path=target.path,
        language=target.language,
        kind=classify_path(target.path),
        commit_sha=target.commit_sha,
        symbols=[
            SymbolSummary(
                id=s.id,
                symbol_type=s.symbol_type,
                name=s.name,
                start_line=s.start_line,
                end_line=s.end_line,
                signature=s.signature,
                docstring=s.docstring,
            )
            for s in sorted(symbols_by_file.get(file_id, []), key=lambda s: s.start_line)
        ],
        dependencies=[
            DependencyRef(file_id=fid, path=file_by_id[fid].path, matched_name=name)
            for fid, name in dependencies.items()
        ],
        dependents=[
            DependencyRef(file_id=fid, path=file_by_id[fid].path, matched_name=name)
            for fid, name in dependents.items()
        ],
    )


async def search_nodes(
    db: AsyncSession, repository_id: uuid.UUID, query: str, *, limit: int = 20
) -> list[SearchResult]:
    like = f"%{query}%"
    file_result = await db.execute(
        select(CodeFile)
        .where(CodeFile.repository_id == repository_id, CodeFile.path.ilike(like))
        .limit(limit)
    )
    matched_files = list(file_result.scalars().all())
    seen_file_ids = {f.id for f in matched_files}

    results = [
        SearchResult(
            file_id=f.id, path=f.path, package=_package_of(f.path), matched_symbol_name=None
        )
        for f in matched_files
    ]

    remaining = limit - len(results)
    if remaining > 0:
        symbol_result = await db.execute(
            select(CodeSymbol, CodeFile.path)
            .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
            .where(CodeFile.repository_id == repository_id, CodeSymbol.name.ilike(like))
            .limit(
                remaining * 2
            )  # a file can match on more than one symbol; over-fetch then dedupe
        )
        for symbol, path in symbol_result.all():
            if symbol.file_id in seen_file_ids:
                continue
            seen_file_ids.add(symbol.file_id)
            results.append(
                SearchResult(
                    file_id=symbol.file_id,
                    path=path,
                    package=_package_of(path),
                    matched_symbol_name=symbol.name,
                )
            )
            if len(results) >= limit:
                break

    return results[:limit]


async def rank_files_by_dependents(
    db: AsyncSession, repository_id: uuid.UUID, *, limit: int = 10
) -> list[FileRanking]:
    """The files with the most fan-in (other files depending on them) —
    the "important/central file" signal app/onboarding/ uses for
    "recommended files" and "important modules". Reuses the same
    file-level import graph as build_module_graph/get_file_detail rather
    than recomputing it a third way."""
    files = await _load_files(db, repository_id)
    symbols = await _load_symbols(db, repository_id)
    name_index = _build_name_index(files, symbols)
    raw_edges = _resolve_import_edges(files, name_index)

    symbols_by_file: dict[uuid.UUID, list[CodeSymbol]] = defaultdict(list)
    for symbol in symbols:
        symbols_by_file[symbol.file_id].append(symbol)

    dependents_count: dict[uuid.UUID, int] = defaultdict(int)
    dependent_sources: dict[uuid.UUID, set[uuid.UUID]] = defaultdict(set)
    for src, dst, _name in raw_edges:
        if src not in dependent_sources[dst]:
            dependent_sources[dst].add(src)
            dependents_count[dst] += 1

    rankings = [
        FileRanking(
            file_id=file.id,
            path=file.path,
            label=_dominant_label(file.path, symbols_by_file.get(file.id, [])),
            kind=classify_path(file.path),
            dependents_count=dependents_count.get(file.id, 0),
        )
        for file in files
    ]
    rankings.sort(key=lambda r: r.dependents_count, reverse=True)
    return [r for r in rankings if r.dependents_count > 0][:limit]


__all__ = [
    "DATABASE_NODE_ID",
    "NodeKind",
    "build_module_graph",
    "build_package_graph",
    "get_file_detail",
    "rank_files_by_dependents",
    "search_nodes",
]
