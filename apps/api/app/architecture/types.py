import uuid
from dataclasses import dataclass, field
from typing import Literal

from app.architecture.classifier import NodeKind

NodeType = Literal["package", "file", "database"]


@dataclass(frozen=True, slots=True)
class GraphNode:
    id: str  # "package:<path>" | "file:<uuid>" | "database"
    node_type: NodeType
    label: str
    kind: NodeKind | Literal["database"]
    path: str | None = None
    file_id: uuid.UUID | None = None
    language: str | None = None
    file_count: int | None = None  # package nodes only
    symbol_count: int | None = None  # file nodes only


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source: str
    target: str
    weight: int


@dataclass(frozen=True, slots=True)
class GraphView:
    nodes: list[GraphNode]
    edges: list[GraphEdge]


@dataclass(frozen=True, slots=True)
class SymbolSummary:
    id: uuid.UUID
    symbol_type: str
    name: str
    start_line: int
    end_line: int
    signature: str | None
    docstring: str | None


@dataclass(frozen=True, slots=True)
class DependencyRef:
    file_id: uuid.UUID
    path: str
    matched_name: str


@dataclass(frozen=True, slots=True)
class FileDetail:
    file_id: uuid.UUID
    path: str
    language: str | None
    kind: NodeKind
    commit_sha: str
    symbols: list[SymbolSummary] = field(default_factory=list)
    dependencies: list[DependencyRef] = field(default_factory=list)
    dependents: list[DependencyRef] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class SearchResult:
    file_id: uuid.UUID
    path: str
    package: str
    matched_symbol_name: str | None
