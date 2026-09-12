import enum


class RepositoryStatus(enum.StrEnum):
    """Status of syncing GitHub metadata (branches/commits/PRs/issues) into
    our database — unrelated to the future AI code-indexing status, which
    will be a separate concept once repository ingestion for chat exists."""

    PENDING = "pending"
    SYNCING = "syncing"
    READY = "ready"
    ERROR = "error"
