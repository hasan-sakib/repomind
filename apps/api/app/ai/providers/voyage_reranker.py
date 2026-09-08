from voyageai.client_async import AsyncClient

from app.ai.reranker import RerankedDocument, Reranker


class VoyageReranker(Reranker):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncClient(api_key=api_key)
        self._model = model

    async def rerank(
        self, query: str, documents: list[str], *, top_k: int
    ) -> list[RerankedDocument]:
        result = await self._client.rerank(
            query=query, documents=documents, model=self._model, top_k=top_k
        )
        return [
            RerankedDocument(index=r.index, relevance_score=r.relevance_score)
            for r in result.results
        ]
