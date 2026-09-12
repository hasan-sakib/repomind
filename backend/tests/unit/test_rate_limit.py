import uuid
from collections.abc import AsyncGenerator

import pytest

from app.core.rate_limit import _increment_and_check, reset_all_rate_limits


@pytest.fixture(autouse=True)
async def _cleanup() -> AsyncGenerator[None]:
    yield
    await reset_all_rate_limits()


async def test_requests_within_the_limit_are_allowed() -> None:
    key = f"ratelimit:test:{uuid.uuid4()}"
    for _ in range(5):
        allowed = await _increment_and_check(key=key, max_requests=5, window_seconds=60)
        assert allowed is True


async def test_requests_over_the_limit_are_rejected() -> None:
    key = f"ratelimit:test:{uuid.uuid4()}"
    for _ in range(3):
        assert await _increment_and_check(key=key, max_requests=3, window_seconds=60) is True

    assert await _increment_and_check(key=key, max_requests=3, window_seconds=60) is False


async def test_separate_keys_have_independent_limits() -> None:
    key_a = f"ratelimit:test:{uuid.uuid4()}"
    key_b = f"ratelimit:test:{uuid.uuid4()}"
    for _ in range(3):
        assert await _increment_and_check(key=key_a, max_requests=3, window_seconds=60) is True

    # key_a is now exhausted, but key_b (a different bucket) is unaffected.
    assert await _increment_and_check(key=key_b, max_requests=3, window_seconds=60) is True
