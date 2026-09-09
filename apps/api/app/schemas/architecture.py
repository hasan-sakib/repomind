import uuid

from pydantic import BaseModel, ConfigDict

from app.architecture.classifier import NodeKind
from app.architecture.types import (
    DependencyRef,
    FileDetail,
    GraphEdge,
    GraphNode,
    GraphView,
    SearchResult,
    SymbolSummary,
)
from app.integrations.github.schemas import GitHubCommit


class GraphNodePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    node_type: str
    label: str
    kind: str
    path: str | None
    file_id: uuid.UUID | None
    language: str | None
    file_count: int | None
    symbol_count: int | None

    @classmethod
    def from_node(cls, node: GraphNode) -> "GraphNodePublic":
        return cls.model_validate(node)


class GraphEdgePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: str
    target: str
    weight: int

    @classmethod
    def from_edge(cls, edge: GraphEdge) -> "GraphEdgePublic":
        return cls.model_validate(edge)


class GraphViewPublic(BaseModel):
    nodes: list[GraphNodePublic]
    edges: list[GraphEdgePublic]

    @classmethod
    def from_view(cls, view: GraphView) -> "GraphViewPublic":
        return cls(
            nodes=[GraphNodePublic.from_node(n) for n in view.nodes],
            edges=[GraphEdgePublic.from_edge(e) for e in view.edges],
        )


class SymbolSummaryPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol_type: str
    name: str
    start_line: int
    end_line: int
    signature: str | None
    docstring: str | None

    @classmethod
    def from_summary(cls, summary: SymbolSummary) -> "SymbolSummaryPublic":
        return cls.model_validate(summary)


class DependencyRefPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: uuid.UUID
    path: str
    matched_name: str

    @classmethod
    def from_ref(cls, ref: DependencyRef) -> "DependencyRefPublic":
        return cls.model_validate(ref)


class FileDetailPublic(BaseModel):
    file_id: uuid.UUID
    path: str
    language: str | None
    kind: NodeKind
    commit_sha: str
    symbols: list[SymbolSummaryPublic]
    dependencies: list[DependencyRefPublic]
    dependents: list[DependencyRefPublic]

    @classmethod
    def from_detail(cls, detail: FileDetail) -> "FileDetailPublic":
        return cls(
            file_id=detail.file_id,
            path=detail.path,
            language=detail.language,
            kind=detail.kind,
            commit_sha=detail.commit_sha,
            symbols=[SymbolSummaryPublic.from_summary(s) for s in detail.symbols],
            dependencies=[DependencyRefPublic.from_ref(r) for r in detail.dependencies],
            dependents=[DependencyRefPublic.from_ref(r) for r in detail.dependents],
        )


class SearchResultPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: uuid.UUID
    path: str
    package: str
    matched_symbol_name: str | None

    @classmethod
    def from_result(cls, result: SearchResult) -> "SearchResultPublic":
        return cls.model_validate(result)


class RecentCommitPublic(BaseModel):
    sha: str
    message: str
    author_login: str | None
    author_name: str | None
    html_url: str
    authored_at: str

    @classmethod
    def from_commit(cls, commit: GitHubCommit) -> "RecentCommitPublic":
        return cls(
            sha=commit.sha,
            message=commit.message,
            author_login=commit.author_login,
            author_name=commit.author_name,
            html_url=commit.html_url,
            authored_at=commit.authored_at.isoformat(),
        )
