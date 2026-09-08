from collections.abc import AsyncIterator

from anthropic import AsyncAnthropic
from anthropic.types import MessageParam

from app.ai.provider import AIProvider, ChatMessage, CompletionResult


def _to_message_params(messages: list[ChatMessage]) -> list[MessageParam]:
    return [MessageParam(role=m.role, content=m.content) for m in messages]


class AnthropicProvider(AIProvider):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncAnthropic(api_key=api_key)
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    async def complete(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> CompletionResult:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=max_tokens,
            system=system or "",
            thinking={"type": "adaptive"},
            messages=_to_message_params(messages),
        )
        text = "".join(block.text for block in response.content if block.type == "text")
        return CompletionResult(
            content=text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=max_tokens,
            system=system or "",
            thinking={"type": "adaptive"},
            messages=_to_message_params(messages),
        ) as stream:
            async for text in stream.text_stream:
                yield text
