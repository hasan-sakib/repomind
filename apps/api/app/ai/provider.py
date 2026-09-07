from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Literal

Role = Literal["user", "assistant"]


@dataclass(frozen=True, slots=True)
class ChatMessage:
    role: Role
    content: str


@dataclass(frozen=True, slots=True)
class CompletionResult:
    content: str
    input_tokens: int
    output_tokens: int
    model: str


class AIProvider(ABC):
    """Abstraction over a chat-completion LLM provider.

    Concrete implementations live in app/ai/providers/. Callers depend only on
    this interface so the underlying provider (Anthropic, or another vendor
    later) can be swapped without touching business logic.
    """

    @abstractmethod
    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> CompletionResult: ...

    @abstractmethod
    def stream(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        """Yield response text incrementally."""
        ...
