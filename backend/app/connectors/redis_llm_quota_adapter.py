import hashlib
import logging
import time
import uuid
from collections.abc import Callable

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.exceptions import LLMQuotaExceededError, LLMQuotaUnavailableError

logger = logging.getLogger(__name__)

MINUTE_SECONDS = 60
DAY_SECONDS = 24 * 60 * 60

_CONSUME_QUOTA_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local minute_window = tonumber(ARGV[2])
local day_window = tonumber(ARGV[3])
local minute_limit = tonumber(ARGV[4])
local day_limit = tonumber(ARGV[5])
local member = ARGV[6]

local minute_cutoff = now - minute_window
local day_cutoff = now - day_window

redis.call("ZREMRANGEBYSCORE", key, "-inf", day_cutoff)

local minute_count = redis.call("ZCOUNT", key, "(" .. minute_cutoff, "+inf")
local day_count = redis.call("ZCARD", key)
local retry_after_ms = 0

if minute_count >= minute_limit then
    local oldest = redis.call(
        "ZRANGEBYSCORE",
        key,
        "(" .. minute_cutoff,
        "+inf",
        "WITHSCORES",
        "LIMIT",
        0,
        1
    )
    retry_after_ms = math.max(
        retry_after_ms,
        tonumber(oldest[2]) + minute_window - now
    )
end

if day_count >= day_limit then
    local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
    retry_after_ms = math.max(
        retry_after_ms,
        tonumber(oldest[2]) + day_window - now
    )
end

if retry_after_ms > 0 then
    return math.max(1, math.ceil(retry_after_ms / 1000))
end

redis.call("ZADD", key, now, member)
redis.call("PEXPIRE", key, day_window)
return 0
"""


class RedisLLMQuotaAdapter:
    """Enforce shared rolling LLM quotas atomically in Redis."""

    def __init__(
        self,
        redis_client: Redis,
        per_minute: int,
        per_day: int,
        clock: Callable[[], float] = time.time,
        minute_seconds: int = MINUTE_SECONDS,
        day_seconds: int = DAY_SECONDS,
    ) -> None:
        self._redis = redis_client
        self._per_minute = per_minute
        self._per_day = per_day
        self._clock = clock
        self._minute_ms = minute_seconds * 1000
        self._day_ms = day_seconds * 1000

    async def consume(self, client_id: str) -> None:
        """Consume one shared quota unit or raise an application exception."""
        client_digest = hashlib.sha256(client_id.encode("utf-8")).hexdigest()
        key = f"quota:llm:{client_digest}"
        now_ms = int(self._clock() * 1000)

        try:
            retry_after = await self._redis.eval(
                _CONSUME_QUOTA_SCRIPT,
                1,
                key,
                now_ms,
                self._minute_ms,
                self._day_ms,
                self._per_minute,
                self._per_day,
                uuid.uuid4().hex,
            )
        except RedisError as exc:
            logger.exception(
                "Shared LLM quota storage is unavailable.",
                extra={"event": "llm_quota_store_error"},
            )
            raise LLMQuotaUnavailableError(
                "Shared LLM quota storage is unavailable."
            ) from exc

        retry_after_seconds = int(retry_after)
        if retry_after_seconds > 0:
            raise LLMQuotaExceededError(retry_after=retry_after_seconds)
