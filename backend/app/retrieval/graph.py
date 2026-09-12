"""The retrieval orchestration graph: analyze -> detect intent -> embed
the query once -> route to an intent-specific retrieval strategy -> rank.

Built with LangGraph specifically for the conditional routing at
`detect_intent` — four genuinely different retrieval strategies depending
on what kind of question was asked (a plain vector-search-with-if/else
would work too, but the graph keeps each strategy as an independently
testable node and the routing declarative rather than nested
conditionals). The final LLM generation call happens *outside* this graph
(app/services/chat_service.py) so it can stream tokens over SSE directly
through AIProvider.stream() — routing streaming through the graph itself
would add real complexity for no benefit here, since generation has
nothing left to branch on once ranking is done.
"""

import uuid
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.embedding_provider import EmbeddingProvider
from app.ai.reranker import Reranker
from app.core.config import Settings
from app.models.chat_status import QueryIntent
from app.retrieval import dependency_graph, git_history, intent, ranking, vector_search
from app.retrieval.types import RetrievedChunk


class RagState(TypedDict, total=False):
    repository_id: uuid.UUID
    query: str
    intent: QueryIntent
    symbol_name: str | None
    query_embedding: list[float]
    candidates: list[RetrievedChunk]
    ranked: list[RetrievedChunk]


def build_graph(
    db: AsyncSession,
    embedding_provider: EmbeddingProvider,
    reranker: Reranker,
    settings: Settings,
) -> CompiledStateGraph[RagState, None, RagState, RagState]:
    async def analyze(state: RagState) -> dict[str, object]:
        return {"query": state["query"].strip()}

    async def detect_intent_node(state: RagState) -> dict[str, object]:
        return {
            "intent": intent.detect_intent(state["query"]),
            "symbol_name": intent.extract_symbol_name(state["query"]),
        }

    async def embed_query(state: RagState) -> dict[str, object]:
        result = await embedding_provider.embed([state["query"]], input_type="query")
        return {"query_embedding": result.vectors[0]}

    def route_intent(state: RagState) -> str:
        return state["intent"].value

    async def _vector_candidates(state: RagState, *, limit: int) -> list[RetrievedChunk]:
        return await vector_search.search(
            db,
            repository_id=state["repository_id"],
            query_embedding=state["query_embedding"],
            limit=limit,
        )

    async def vector_retrieve(state: RagState) -> dict[str, object]:
        return {"candidates": await _vector_candidates(state, limit=settings.rag_vector_candidates)}

    async def locate_retrieve(state: RagState) -> dict[str, object]:
        candidates = await _vector_candidates(state, limit=settings.rag_vector_candidates)
        symbol = state.get("symbol_name")
        if symbol:
            definition = await dependency_graph.find_definition(
                db, repository_id=state["repository_id"], symbol_name=symbol
            )
            if definition:
                candidates = [definition, *candidates]
        return {"candidates": candidates}

    async def dependency_retrieve(state: RagState) -> dict[str, object]:
        candidates = await _vector_candidates(state, limit=settings.rag_vector_candidates // 2)
        symbol = state.get("symbol_name")
        if symbol:
            definition = await dependency_graph.find_definition(
                db, repository_id=state["repository_id"], symbol_name=symbol
            )
            dependents = await dependency_graph.find_dependents(
                db,
                repository_id=state["repository_id"],
                symbol_name=symbol,
                limit=settings.rag_dependency_limit,
            )
            candidates = [*([definition] if definition else []), *dependents, *candidates]
        return {"candidates": candidates}

    async def history_retrieve(state: RagState) -> dict[str, object]:
        candidates = await _vector_candidates(state, limit=settings.rag_vector_candidates // 2)
        commits = await git_history.search_commits(
            db,
            repository_id=state["repository_id"],
            query=state["query"],
            limit=settings.rag_git_history_limit,
        )
        return {"candidates": [*commits, *candidates]}

    async def rank_node(state: RagState) -> dict[str, object]:
        ranked = await ranking.rank(
            state["query"],
            state.get("candidates", []),
            reranker=reranker,
            top_k=settings.rag_context_chunks,
        )
        return {"ranked": ranked}

    graph: StateGraph[RagState, None, RagState, RagState] = StateGraph(RagState)
    graph.add_node("analyze", analyze)
    graph.add_node("detect_intent", detect_intent_node)
    graph.add_node("embed_query", embed_query)
    graph.add_node("vector_retrieve", vector_retrieve)
    graph.add_node("locate_retrieve", locate_retrieve)
    graph.add_node("dependency_retrieve", dependency_retrieve)
    graph.add_node("history_retrieve", history_retrieve)
    graph.add_node("rank", rank_node)

    graph.add_edge(START, "analyze")
    graph.add_edge("analyze", "detect_intent")
    graph.add_edge("detect_intent", "embed_query")
    graph.add_conditional_edges(
        "embed_query",
        route_intent,
        {
            QueryIntent.DEPENDENCY.value: "dependency_retrieve",
            QueryIntent.HISTORY.value: "history_retrieve",
            QueryIntent.LOCATE.value: "locate_retrieve",
            QueryIntent.EXPLAIN.value: "vector_retrieve",
            QueryIntent.GENERAL.value: "vector_retrieve",
        },
    )
    graph.add_edge("vector_retrieve", "rank")
    graph.add_edge("locate_retrieve", "rank")
    graph.add_edge("dependency_retrieve", "rank")
    graph.add_edge("history_retrieve", "rank")
    graph.add_edge("rank", END)

    return graph.compile()
