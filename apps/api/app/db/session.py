from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings

settings = get_settings()

# NullPool under test: a real connection per checkout, none held across
# event loops. Every other test fixture in this codebase runs on one
# session-scoped loop, but code that (like this module's own
# async_session_factory, used directly by arq tasks and the WebSocket
# route) opens a session outside FastAPI's request-scoped dependency can
# still get exercised from a *different* loop — e.g. Starlette's
# WebSocketTestSession, which spins up its own loop per connection — and
# a pooled asyncpg connection is bound to the loop it was created on. See
# tests/conftest.py's `_engine` fixture for the same fix applied there.
_engine_kwargs: dict[str, object] = {"pool_pre_ping": True}
if settings.environment == "test":
    _engine_kwargs["poolclass"] = NullPool

engine = create_async_engine(settings.database_url, **_engine_kwargs)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding a request-scoped async session."""
    async with async_session_factory() as session:
        yield session
