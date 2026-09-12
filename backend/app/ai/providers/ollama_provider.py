from collections.abc import AsyncIterator

from ollama import AsyncClient

from app.ai.provider import AIProvider, ChatMessage, CompletionResult


def _to_ollama_messages(messages: list[ChatMessage], system: str | None) -> list[dict[str, str]]:
    ollama_messages = [{"role": "system", "content": system}] if system else []
    ollama_messages += [{"role": m.role, "content": m.content} for m in messages]
    return ollama_messages


class OllamaProvider(AIProvider):
    """Local, free chat completion via Ollama (Qwen/Llama/Gemma, or
    anything else pulled locally) — no API key, no per-token cost. `host`
    points at a running `ollama serve` instance, `http://localhost:11434`
    by default. Reasoning models (e.g. qwen3) stream their thinking as
    empty `message.content` chunks separate from the answer text — see
    docs/architecture/0005-ai-rag-engine.md for why that's left as-is
    rather than surfaced or suppressed."""

    def __init__(self, host: str, model: str) -> None:
        self._client = AsyncClient(host=host)
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
        response = await self._client.chat(
            model=self._model,
            messages=_to_ollama_messages(messages, system),
            options={"num_predict": max_tokens},
        )
        return CompletionResult(
            content=response.message.content or "",
            input_tokens=response.prompt_eval_count or 0,
            output_tokens=response.eval_count or 0,
            model=response.model or self._model,
        )

    async def stream(
        self,
        messages: list[ChatMessage],
        *,
        system: str | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        stream = await self._client.chat(
            model=self._model,
            messages=_to_ollama_messages(messages, system),
            options={"num_predict": max_tokens},
            stream=True,
        )
        async for chunk in stream:
            if chunk.message.content:
                yield chunk.message.content
