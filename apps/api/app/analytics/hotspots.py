"""File-change-frequency and architecture hotspots, aggregated from a
bounded sample of recent commits' own file diffs (fetched live from
GitHub — Commit rows have no per-commit changed-file list to query
locally, the same gap ADR 0006 hit for "recent changes"). Reuses
app/architecture/classifier.py and graph_builder.package_of so a
hotspot's package/kind matches the architecture explorer's own
vocabulary exactly — a hotspot and its architecture-graph package are
the same identifier."""

from collections import defaultdict

from app.architecture.classifier import classify_path
from app.architecture.graph_builder import package_of
from app.domain.analytics_snapshot import ArchitectureHotspotRecord, FileHotspotRecord
from app.integrations.github.schemas import GitHubPullRequestFile


def aggregate_hotspots(
    commit_files: list[list[GitHubPullRequestFile]],
    *,
    dependents_by_path: dict[str, int],
    limit: int,
) -> tuple[list[FileHotspotRecord], list[ArchitectureHotspotRecord]]:
    """Both return values are derived from the same full (untruncated)
    per-file change-count map — the architecture rollup is computed
    before either list is cut down to `limit`, so it reflects every
    changed file, not just the top files individually."""
    change_counts: dict[str, int] = defaultdict(int)
    for files in commit_files:
        for file in files:
            change_counts[file.filename] += 1

    file_hotspots = sorted(
        (
            FileHotspotRecord(
                path=path,
                kind=classify_path(path),
                change_count=count,
                dependents_count=dependents_by_path.get(path, 0),
            )
            for path, count in change_counts.items()
        ),
        key=lambda h: h["change_count"],
        reverse=True,
    )[:limit]

    package_counts: dict[str, int] = defaultdict(int)
    package_files: dict[str, set[str]] = defaultdict(set)
    for path, count in change_counts.items():
        package = package_of(path)
        package_counts[package] += count
        package_files[package].add(path)

    architecture_hotspots = sorted(
        (
            ArchitectureHotspotRecord(
                package_path=package,
                kind=classify_path(package),
                change_count=count,
                file_count=len(package_files[package]),
            )
            for package, count in package_counts.items()
        ),
        key=lambda r: r["change_count"],
        reverse=True,
    )[:limit]

    return file_hotspots, architecture_hotspots
