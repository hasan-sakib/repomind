import enum


class IndexingJobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    PARTIAL = "partial"  # completed, but one or more files errored


class IndexingTrigger(enum.StrEnum):
    INITIAL = "initial"
    MANUAL = "manual"
    WEBHOOK = "webhook"


class IndexingStage(enum.StrEnum):
    FETCHING = "fetching"
    DISCOVERING = "discovering"
    FILTERING = "filtering"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    DONE = "done"
