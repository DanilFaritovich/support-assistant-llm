import asyncio

import pytest

from app.api.rate_limiting import InMemoryLLMRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.current = 0.0

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


@pytest.mark.asyncio
async def test_allows_ten_requests_per_minute_and_then_recovers() -> None:
    clock = FakeClock()
    limiter = InMemoryLLMRateLimiter(10, 20, clock)

    results = [await limiter.check_and_record("192.0.2.1") for _ in range(10)]

    assert results == [None] * 10
    assert await limiter.check_and_record("192.0.2.1") == 60

    clock.advance(60)

    assert await limiter.check_and_record("192.0.2.1") is None


@pytest.mark.asyncio
async def test_allows_twenty_requests_per_day_and_then_recovers() -> None:
    clock = FakeClock()
    limiter = InMemoryLLMRateLimiter(10, 20, clock)

    first_window = [await limiter.check_and_record("192.0.2.1") for _ in range(10)]
    clock.advance(60)
    second_window = [await limiter.check_and_record("192.0.2.1") for _ in range(10)]

    assert first_window == [None] * 10
    assert second_window == [None] * 10
    assert await limiter.check_and_record("192.0.2.1") == 86_340

    clock.advance(86_340)

    assert await limiter.check_and_record("192.0.2.1") is None


@pytest.mark.asyncio
async def test_tracks_different_client_ips_independently() -> None:
    clock = FakeClock()
    limiter = InMemoryLLMRateLimiter(1, 2, clock)

    assert await limiter.check_and_record("192.0.2.1") is None
    assert await limiter.check_and_record("192.0.2.1") == 60
    assert await limiter.check_and_record("198.51.100.2") is None


@pytest.mark.asyncio
async def test_serializes_concurrent_limit_checks() -> None:
    clock = FakeClock()
    limiter = InMemoryLLMRateLimiter(10, 20, clock)

    results = await asyncio.gather(
        *(limiter.check_and_record("192.0.2.1") for _ in range(11))
    )

    assert results.count(None) == 10
    assert results.count(60) == 1
