import os
from collections.abc import AsyncGenerator

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET", "test-secret-at-least-32-bytes-long-for-hs256")
os.environ.setdefault(
    "DATABASE_URL", "postgresql+asyncpg://repomind:repomind@localhost:5432/repomind_test"
)
os.environ.setdefault("GITHUB_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("GITHUB_APP_ID", "123456")
os.environ.setdefault("GITHUB_APP_SLUG", "repomind-test-app")

# A throwaway RSA keypair, generated fresh per test run — the GitHub App
# JWT signing path needs *a* valid private key, never a real one in tests.
_TEST_RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
os.environ.setdefault(
    "GITHUB_APP_PRIVATE_KEY",
    _TEST_RSA_KEY.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8"),
)

TEST_RSA_PUBLIC_KEY_PEM = (
    _TEST_RSA_KEY.public_key()
    .public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    .decode("utf-8")
)

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app import models  # noqa: F401  (populates Base.metadata)
from app.api.deps import get_arq_pool
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import get_db_session
from app.main import app
from app.workers import tasks as worker_tasks

settings = get_settings()


@pytest_asyncio.fixture(scope="session")
async def _engine() -> AsyncGenerator[AsyncEngine]:
    # NullPool: a real network connection per checkout, none held/reused
    # across event loops — the pooled default caused
    # "cannot perform operation: another operation is in progress" once
    # pytest-asyncio's per-test event loop no longer matched the loop the
    # pooled asyncpg connection was created on.
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """A plain session per test. Isolation between tests comes from
    truncating every table afterward (see below), not from a rolled-back
    transaction — binding a session to a manually-managed
    connection/savepoint raced with asyncpg's single-operation-per-connection
    constraint under FastAPI's concurrent dependency resolution."""
    session_factory = async_sessionmaker(bind=_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with _engine.begin() as conn:
        table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
        await conn.exec_driver_sql(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")


class FakeArqPool:
    """Runs an enqueued job inline, synchronously, instead of pushing it
    onto Redis for a real worker to pick up — mirrors how FastAPI
    BackgroundTasks used to execute inline under ASGITransport before
    sync/indexing moved onto the arq queue. Tests that need to assert
    something was (or wasn't) queued can inspect `.enqueued`."""

    def __init__(self) -> None:
        self.enqueued: list[tuple[str, tuple[object, ...], dict[str, object]]] = []

    async def enqueue_job(self, function: str, *args: object, **kwargs: object) -> None:
        self.enqueued.append((function, args, kwargs))
        task_fn = getattr(worker_tasks, function)
        await task_fn({}, *args, **kwargs)


@pytest.fixture
def fake_arq_pool() -> FakeArqPool:
    return FakeArqPool()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, fake_arq_pool: FakeArqPool
) -> AsyncGenerator[AsyncClient]:
    async def override_get_db_session() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_arq_pool] = lambda: fake_arq_pool
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-Requested-With": "RepoMind"}
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


async def _extra_client() -> AsyncGenerator[AsyncClient]:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://test", headers={"X-Requested-With": "RepoMind"}
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def second_client(client: AsyncClient) -> AsyncGenerator[AsyncClient]:
    """A second logged-in-as-someone-else client sharing the same
    transaction/dependency override as `client` — for tests that need two
    distinct users interacting with one organization."""
    async for ac in _extra_client():
        yield ac


@pytest_asyncio.fixture
async def third_client(client: AsyncClient) -> AsyncGenerator[AsyncClient]:
    """A third independently-logged-in client, same transaction as `client`."""
    async for ac in _extra_client():
        yield ac


@pytest.fixture
def captured_emails(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, str]]:
    """Intercepts outbound email instead of letting ConsoleEmailSender just
    log it, so password-reset/verification tests can read the token out of
    the "sent" email body."""
    sent: list[dict[str, str]] = []

    class FakeEmailSender:
        async def send(self, *, to: str, subject: str, body: str) -> None:
            sent.append({"to": to, "subject": subject, "body": body})

    fake = FakeEmailSender()
    monkeypatch.setattr("app.services.auth_service.get_email_sender", lambda: fake)
    return sent
