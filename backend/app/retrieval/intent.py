"""Rule-based query intent classification — deliberately not an LLM call.
An extra model round-trip to classify intent would add real latency and
cost to every single query for a 4-way classification a handful of
keyword patterns handle reliably; see
docs/architecture/0005-ai-rag-engine.md for the tradeoff. Swapping this
for an LLM-based classifier later is a contained change — app/retrieval/
graph.py only depends on this module's two function signatures.
"""

import re

from app.models.chat_status import QueryIntent

_DEPENDENCY_PATTERNS = (
    r"\bdepend(s|ency|encies)?\b",
    r"\bwho (calls|uses|imports)\b",
    r"\bwhat (calls|uses|imports)\b",
    r"\bused by\b",
    r"\brelies on\b",
)
_HISTORY_PATTERNS = (
    r"\bwhen (was|did|were)\b",
    r"\bwhy (was|did|were)\b",
    r"\bhistory\b",
    r"\bchanged?\b",
    r"\bcommit(s|ted)?\b",
)
_LOCATE_PATTERNS = (
    r"\bwhere (is|are)\b",
    r"\bwhich file(s)?\b",
    r"\bwhich (module|package|folder|directory)\b",
    r"\blocated?\b",
    r"\bfind\b",
    r"\bshow me\b",
)

_SYMBOL_TOKEN = re.compile(r"\b([A-Z][a-zA-Z0-9]*(?:[A-Z][a-zA-Z0-9]*)*)\b")
_STOPWORD_SYMBOLS = {"I", "The", "A", "An", "Show", "Which", "What", "Where", "When", "Why", "How"}


def detect_intent(query: str) -> QueryIntent:
    lowered = query.lower()
    if any(re.search(p, lowered) for p in _DEPENDENCY_PATTERNS):
        return QueryIntent.DEPENDENCY
    if any(re.search(p, lowered) for p in _HISTORY_PATTERNS):
        return QueryIntent.HISTORY
    if any(re.search(p, lowered) for p in _LOCATE_PATTERNS):
        return QueryIntent.LOCATE
    if lowered.strip().startswith(("explain", "how does", "how do", "walk me through")):
        return QueryIntent.EXPLAIN
    return QueryIntent.GENERAL


def extract_symbol_name(query: str) -> str | None:
    """Best-effort: the longest PascalCase-looking identifier in the
    query, since that's how classes/services are named in every language
    this pipeline indexes (see app/indexing/languages.py). Returns None
    if nothing looks like a symbol — callers fall back to vector search."""
    candidates: list[str] = [m for m in _SYMBOL_TOKEN.findall(query) if m not in _STOPWORD_SYMBOLS]
    if not candidates:
        return None
    return max(candidates, key=len)
