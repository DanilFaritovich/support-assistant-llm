import asyncio
import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from redis.asyncio import Redis

from app.connectors.redis_llm_quota_adapter import RedisLLMQuotaAdapter
from app.exceptions import LLMQuotaExceededError

TEST_REDIS_URL = os.getenv("TEST_REDIS_URL")


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


@pytest_asyncio.fixture
async def redis_client() -> AsyncIterator[Redis]:
    """Provide isolated real Redis state when integration Redis is configured."""
    if TEST_REDIS_URL is None:
        pytest.skip("TEST_REDIS_URL is required for Redis integration tests.")

    client = Redis.from_url(TEST_REDIS_URL, decode_responses=True)
    await client.flushdb()

    try:
        yield client
    finally:
        await client.flushdb()
        await client.aclose()


@pytest.mark.asyncio
async def test_enforces_rolling_minute_and_day_windows(
    redis_client: Redis,
) -> None:
    clock = FakeClock()
    quota = RedisLLMQuotaAdapter(redis_client, 10, 20, clock)

    for _ in range(10):
        await quota.consume("192.0.2.1")

    with pytest.raises(LLMQuotaExceededError) as minute_error:
        await quota.consume("192.0.2.1")
    assert minute_error.value.retry_after == 60

    clock.advance(60)
    for _ in range(10):
        await quota.consume("192.0.2.1")

    with pytest.raises(LLMQuotaExceededError) as day_error:
        await quota.consume("192.0.2.1")
    assert day_error.value.retry_after == 86_340

    clock.advance(86_340)
    await quota.consume("192.0.2.1")


@pytest.mark.asyncio
async def test_tracks_clients_independently(redis_client: Redis) -> None:
    quota = RedisLLMQuotaAdapter(redis_client, 1, 2, FakeClock())

    await quota.consume("192.0.2.1")
    with pytest.raises(LLMQuotaExceededError):
        await quota.consume("192.0.2.1")

    await quota.consume("198.51.100.2")


@pytest.mark.asyncio
async def test_atomic_consume_does_not_overshoot_limit(
    redis_client: Redis,
) -> None:
    quota = RedisLLMQuotaAdapter(redis_client, 10, 20, FakeClock())

    async def consume() -> Exception | None:
        try:
            await quota.consume("192.0.2.1")
        except LLMQuotaExceededError as exc:
            return exc
        return None

    results = await asyncio.gather(*(consume() for _ in range(11)))

    assert results.count(None) == 10
    errors = [result for result in results if result is not None]
    assert len(errors) == 1
    assert isinstance(errors[0], LLMQuotaExceededError)
    assert errors[0].retry_after == 60
