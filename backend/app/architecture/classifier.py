"""Classifies a file (or package/directory) path into an architectural
"kind" — route, service, repository, model, schema, or other — purely by
directory-naming convention. This is a heuristic, not a semantic analysis:
it does not look at decorators, base classes, or imports, so a file that
doesn't follow one of these conventions is classified "other" rather than
guessed at. See docs/architecture/0006-architecture-dependency-graph.md
for the scope decision and why a decorator- or inheritance-based
classifier (e.g. "is this class a `Base` subclass") was left for later.
"""

from typing import Literal

NodeKind = Literal["route", "service", "repository", "model", "schema", "other"]

# Checked in order — the first pattern whose directory segment appears
# anywhere in the path wins. "routes"/"api" before "schema" matters for a
# layout like app/api/v1/routes/ vs app/schemas/ living under the same
# api/ tree in some projects.
_PATTERNS: tuple[tuple[str, NodeKind], ...] = (
    ("routes", "route"),
    ("controllers", "route"),
    ("endpoints", "route"),
    ("views", "route"),
    ("services", "service"),
    ("usecases", "service"),
    ("repositories", "repository"),
    ("repository", "repository"),
    ("dao", "repository"),
    ("domain", "model"),
    ("models", "model"),
    ("entities", "model"),
    ("schemas", "schema"),
    ("dto", "schema"),
    ("serializers", "schema"),
)


def classify_path(path: str) -> NodeKind:
    segments = {segment.lower() for segment in path.replace("\\", "/").split("/")}
    for pattern, kind in _PATTERNS:
        if pattern in segments:
            return kind
    return "other"
