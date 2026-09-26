import asyncio
import math
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request, status

MINUTE_SECONDS = 60.0
DAY_SECONDS = 24 * 60 * 60.0


class InMemoryLLMRateLimiter:
    """Limit LLM operations per client within one backend process."""

    def __init__(
        self,
        per_minute: int,
        per_day: int,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._per_minute = per_minute
        self._per_day = per_day
        self._clock = clock
        self._requests: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup = clock()

    async def check_and_record(self, client_ip: str) -> int | None:
        """Record an allowed operation or return its Retry-After value."""
        now = self._clock()

        async with self._lock:
            self._remove_expired_requests(now)

            requests = self._requests.setdefault(client_ip, deque())
            day_cutoff = now - DAY_SECONDS
            while requests and requests[0] <= day_cutoff:
                requests.popleft()

            minute_cutoff = now - MINUTE_SECONDS
            minute_requests = [
                timestamp for timestamp in requests if timestamp > minute_cutoff
            ]

            retry_after = 0.0

            if len(minute_requests) >= self._per_minute:
                blocking_timestamp = minute_requests[-self._per_minute]
                retry_after = max(
                    retry_after,
                    blocking_timestamp + MINUTE_SECONDS - now,
                )

            if len(requests) >= self._per_day:
                blocking_timestamp = requests[-self._per_day]
                retry_after = max(
                    retry_after,
                    blocking_timestamp + DAY_SECONDS - now,
                )

            if retry_after > 0:
                return max(1, math.ceil(retry_after))

            requests.append(now)
            return None

    def _remove_expired_requests(self, now: float) -> None:
        if now - self._last_cleanup < MINUTE_SECONDS:
            return

        day_cutoff = now - DAY_SECONDS

        for client_ip, requests in list(self._requests.items()):
            while requests and requests[0] <= day_cutoff:
                requests.popleft()

            if not requests:
                del self._requests[client_ip]

        self._last_cleanup = now


async def enforce_llm_rate_limit(
    request: Request,
    limiter: InMemoryLLMRateLimiter,
) -> None:
    """Reject an LLM operation when the client IP has exhausted its quota."""
    client_ip = request.client.host if request.client is not None else "unknown"
    retry_after = await limiter.check_and_record(client_ip)

    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many LLM requests. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )
