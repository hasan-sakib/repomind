import arq
from arq.connections import ArqRedis, RedisSettings

from app.core.config import get_settings


async def create_arq_pool() -> ArqRedis:
    """Called once from the FastAPI lifespan (app/main.py) and stored on
    app.state — not a module-level singleton, since arq.create_pool is
    async and needs a running event loop."""
    settings = get_settings()
    return await arq.create_pool(RedisSettings.from_dsn(settings.redis_url))
