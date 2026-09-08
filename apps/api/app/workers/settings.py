"""arq worker entry point: `uv run arq app.workers.settings.WorkerSettings`"""

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.domain import models  # noqa: F401 — registers every mapped class before first use.
from app.workers.tasks import index_repository, sync_repository

settings = get_settings()


class WorkerSettings:
    functions = [index_repository, sync_repository]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    # A full clone + parse + chunk + embed run over indexing_max_files_per_repository
    # files comfortably needs more than arq's 300s default.
    job_timeout = 1800

    @staticmethod
    async def on_startup(ctx: dict[str, object]) -> None:
        configure_logging()
