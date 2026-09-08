from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RerankedDocument:
    index: int  # position in the original `documents` list passed to rerank()
    relevance_score: float


class Reranker(ABC):
    """Abstraction over a cross-encoder reranking model — the "Context
    Ranking" stage in the RAG pipeline (app/retrieval/ranking.py).
    Mirrors AIProvider/EmbeddingProvider: callers depend only on this
    interface so the reranking provider can be swapped independently of
    the embedding provider (some vendors offer one but not the other).
    """

    @abstractmethod
    async def rerank(
        self, query: str, documents: list[str], *, top_k: int
    ) -> list[RerankedDocument]: ...
