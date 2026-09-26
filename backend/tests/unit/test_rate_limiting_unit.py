from unittest.mock import AsyncMock, MagicMock

import pytest
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.connectors.redis_llm_quota_adapter import RedisLLMQuotaAdapter
from app.exceptions import LLMQuotaExceededError, LLMQuotaUnavailableError


@pytest.fixture
def redis_client() -> MagicMock:
    """Provide a mocked Redis client at the adapter boundary."""
    client = MagicMock(spec=Redis)
    client.eval = AsyncMock(return_value=0)
    return client


@pytest.mark.asyncio
async def test_consumes_quota_without_storing_raw_client_id(
    redis_client: MagicMock,
) -> None:
    adapter = RedisLLMQuotaAdapter(
        redis_client=redis_client,
        per_minute=10,
        per_day=20,
        clock=lambda: 100.0,
    )

    await adapter.consume("192.0.2.1")

    redis_client.eval.assert_awaited_once()
    key = redis_client.eval.await_args.args[2]
    assert key.startswith("quota:llm:")
    assert "192.0.2.1" not in key


@pytest.mark.asyncio
async def test_raises_application_error_with_retry_after(
    redis_client: MagicMock,
) -> None:
    redis_client.eval.return_value = 42
    adapter = RedisLLMQuotaAdapter(redis_client, 10, 20)

    with pytest.raises(LLMQuotaExceededError) as error:
        await adapter.consume("192.0.2.1")

    assert error.value.retry_after == 42


@pytest.mark.asyncio
async def test_translates_redis_failure_to_application_error(
    redis_client: MagicMock,
) -> None:
    redis_client.eval.side_effect = RedisError("Redis unavailable")
    adapter = RedisLLMQuotaAdapter(redis_client, 10, 20)

    with pytest.raises(LLMQuotaUnavailableError):
        await adapter.consume("192.0.2.1")
