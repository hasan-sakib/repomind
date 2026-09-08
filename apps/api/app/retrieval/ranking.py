"""Context Ranking: merges candidates from every retrieval source, dedupes
them, and reranks by actual relevance to the query using a cross-encoder
(app/ai/reranker.py) rather than trusting each source's own notion of
"good" (pgvector's cosine distance and "this file imports X" aren't
comparable scores). Falls back to the candidates' original order if the
reranker call fails — a ranking hiccup should degrade context quality,
not break the whole query."""

import logging
from dataclasses import replace

from app.ai.reranker import Reranker
from app.retrieval.types import RetrievedChunk

logger = logging.getLogger("repomind.retrieval")


def _dedupe(candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
    seen: set[tuple[object, ...]] = set()
    deduped: list[RetrievedChunk] = []
    for candidate in candidates:
        key = (
            candidate.chunk_id,
            candidate.file_path,
            candidate.start_line,
            candidate.commit_sha,
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(candidate)
    return deduped


async def rank(
    query: str, candidates: list[RetrievedChunk], *, reranker: Reranker, top_k: int
) -> list[RetrievedChunk]:
    deduped = _dedupe(candidates)
    if not deduped:
        return []

    try:
        reranked = await reranker.rerank(
            query, [c.content for c in deduped], top_k=min(top_k, len(deduped))
        )
    except Exception:  # noqa: BLE001 — a ranking failure must not fail the whole query
        logger.exception("Reranking failed; falling back to source order")
        return deduped[:top_k]

    return [
        replace(deduped[r.index], score=r.relevance_score)
        for r in reranked
        if 0 <= r.index < len(deduped)
    ]
