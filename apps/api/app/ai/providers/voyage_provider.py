from voyageai.client_async import AsyncClient

from app.ai.embedding_provider import EmbeddingInputType, EmbeddingProvider, EmbeddingResult


class VoyageEmbeddingProvider(EmbeddingProvider):
    def __init__(self, api_key: str, model: str, output_dimension: int) -> None:
        self._client = AsyncClient(api_key=api_key)
        self._model = model
        self._output_dimension = output_dimension

    async def embed(
        self, texts: list[str], *, input_type: EmbeddingInputType
    ) -> EmbeddingResult:
        response = await self._client.embed(
            texts=texts,
            model=self._model,
            input_type=input_type,
            output_dimension=self._output_dimension,
        )
        # voyage-code-3 with output_dtype left at its "float" default always
        # returns list[list[float]]; the int/uint8 variants in the SDK's
        # return type only apply to output_dtype values this provider never
        # passes.
        vectors: list[list[float]] = response.embeddings  # type: ignore[assignment]
        return EmbeddingResult(
            vectors=vectors,
            model=self._model,
            total_tokens=response.total_tokens,
        )
