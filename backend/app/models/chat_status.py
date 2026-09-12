import enum


class MessageRole(enum.StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class MessageFeedback(enum.StrEnum):
    UP = "up"
    DOWN = "down"


class AiRunStatus(enum.StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class QueryIntent(enum.StrEnum):
    """Routes retrieval strategy — see app/retrieval/intent.py and
    app/retrieval/graph.py. Not an LLM-classified label: a deliberately
    simple, fast, deterministic rule-based classification (see
    docs/architecture/0005-ai-rag-engine.md for why)."""

    EXPLAIN = "explain"  # "explain the auth flow" — broad conceptual walkthrough
    LOCATE = "locate"  # "where is X implemented" — find + point at code
    DEPENDENCY = "dependency"  # "what depends on X" / "what does X depend on"
    HISTORY = "history"  # "when/why was X changed"
    GENERAL = "general"  # fallback — treated like EXPLAIN


class RetrievalSourceType(enum.StrEnum):
    VECTOR = "vector"
    DEPENDENCY = "dependency"
    GIT_HISTORY = "git_history"
