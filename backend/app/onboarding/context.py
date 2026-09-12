"""Aggregates everything the onboarding guide needs — deterministic
sections computed directly from indexed data, plus the grounding data for
the AI-generated narrative sections (app/onboarding/prompt.py). One
GitHub round-trip per manifest/README file actually present in the
repository; nothing speculative is fetched."""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.architecture import graph_builder
from app.architecture.types import FileRanking
from app.integrations.github import rest_client
from app.models.code_file import CodeFile
from app.models.code_symbol import CodeSymbol
from app.onboarding import heuristics
from app.onboarding.heuristics import DatabaseStructureEntry, LearningPathStep
from app.onboarding.manifest import MANIFEST_FILENAMES, Dependency, parse_manifest
from app.onboarding.setup import SetupStep, detect_setup_steps, find_shallowest

_MAX_IMPORTANT_MODULES = 8
_MAX_RECOMMENDED_FILES = 10
_MAX_README_CHARS = 6_000


@dataclass(frozen=True, slots=True)
class ImportantModule:
    name: str
    path: str
    kind: str
    file_count: int


@dataclass(frozen=True, slots=True)
class ModuleEdge:
    source: str
    target: str


@dataclass(frozen=True, slots=True)
class OnboardingContext:
    important_modules: list[ImportantModule]
    module_edges: list[ModuleEdge]
    recommended_files: list[FileRanking]
    key_dependencies: list[Dependency]
    setup_steps: list[SetupStep]
    database_structure: list[DatabaseStructureEntry]
    learning_path: list[LearningPathStep]
    auth_files: list[CodeFile]
    readme_content: str | None
    route_files: list[FileRanking]
    service_files: list[FileRanking]

    def valid_file_paths(self) -> set[str]:
        """Every path the AI prompt actually shows the model — citations
        outside this set are dropped, not trusted (result_schema.py)."""
        paths = {m.path for m in self.recommended_files}
        paths.update(f.path for f in self.auth_files)
        paths.update(f.path for f in self.route_files)
        paths.update(f.path for f in self.service_files)
        paths.update(e.path for e in self.database_structure)
        paths.update(m.path for m in self.important_modules)
        return paths


async def _fetch_manifest_dependencies(
    file_paths: set[str], *, installation_token: str, full_name: str, ref: str
) -> list[Dependency]:
    deps: list[Dependency] = []
    for manifest_name in MANIFEST_FILENAMES:
        manifest_path = find_shallowest(file_paths, manifest_name)
        if manifest_path is None:
            continue
        content = await rest_client.get_file_content(
            installation_token, full_name, path=manifest_path, ref=ref
        )
        if content is None:
            continue
        deps.extend(parse_manifest(manifest_name, content))
    return deps


async def build_context(
    db: AsyncSession,
    *,
    repository_id: uuid.UUID,
    installation_token: str,
    full_name: str,
    commit_sha: str,
) -> OnboardingContext:
    files_result = await db.execute(select(CodeFile).where(CodeFile.repository_id == repository_id))
    files = list(files_result.scalars().all())

    symbols_result = await db.execute(
        select(CodeSymbol)
        .join(CodeFile, CodeSymbol.file_id == CodeFile.id)
        .where(CodeFile.repository_id == repository_id)
    )
    symbols_by_file: dict[uuid.UUID, list[CodeSymbol]] = {}
    for symbol in symbols_result.scalars():
        symbols_by_file.setdefault(symbol.file_id, []).append(symbol)

    package_graph = await graph_builder.build_package_graph(db, repository_id)
    important_modules = sorted(
        (
            ImportantModule(
                name=node.label,
                path=node.path or "",
                kind=node.kind,
                file_count=node.file_count or 0,
            )
            for node in package_graph.nodes
            if node.node_type == "package"
        ),
        key=lambda m: m.file_count,
        reverse=True,
    )[:_MAX_IMPORTANT_MODULES]
    important_paths = {m.path for m in important_modules}
    module_edges = [
        ModuleEdge(
            source=edge.source.removeprefix("package:"), target=edge.target.removeprefix("package:")
        )
        for edge in package_graph.edges
        if edge.source.removeprefix("package:") in important_paths
        or edge.target.removeprefix("package:") in important_paths
    ]

    file_rankings = await graph_builder.rank_files_by_dependents(db, repository_id, limit=100)
    recommended_files = file_rankings[:_MAX_RECOMMENDED_FILES]
    route_files = [r for r in file_rankings if r.kind == "route"][:5]
    service_files = [r for r in file_rankings if r.kind == "service"][:5]

    readme = heuristics.find_readme(files)
    readme_content: str | None = None
    if readme is not None:
        content = await rest_client.get_file_content(
            installation_token, full_name, path=readme.path, ref=commit_sha
        )
        readme_content = content[:_MAX_README_CHARS] if content else None

    entry_point = heuristics.find_entry_point(files)
    auth_files = heuristics.find_auth_files(files, symbols_by_file)
    database_structure = heuristics.find_database_structure(files, symbols_by_file)
    learning_path = heuristics.build_learning_path(
        readme=readme, entry_point=entry_point, auth_files=auth_files, file_rankings=file_rankings
    )

    file_paths = {f.path for f in files}
    setup_steps = detect_setup_steps(file_paths)
    key_dependencies = await _fetch_manifest_dependencies(
        file_paths, installation_token=installation_token, full_name=full_name, ref=commit_sha
    )

    return OnboardingContext(
        important_modules=important_modules,
        module_edges=module_edges,
        recommended_files=recommended_files,
        key_dependencies=key_dependencies,
        setup_steps=setup_steps,
        database_structure=database_structure,
        learning_path=learning_path,
        auth_files=auth_files,
        readme_content=readme_content,
        route_files=route_files,
        service_files=service_files,
    )


__all__ = ["ImportantModule", "OnboardingContext", "build_context"]
