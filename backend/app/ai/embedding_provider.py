from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal

EmbeddingInputType = Literal["document", "query"]


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    vectors: list[list[float]]
    model: str
    total_tokens: int


class EmbeddingProvider(ABC):
    """Abstraction over a text-embedding provider.

    Mirrors AIProvider (app/ai/provider.py): callers depend only on this
    interface so the underlying provider (Voyage, or another vendor later)
    can be swapped without touching indexing or search logic.
    """

    @abstractmethod
    async def embed(
        self, texts: list[str], *, input_type: EmbeddingInputType
    ) -> EmbeddingResult: ...
