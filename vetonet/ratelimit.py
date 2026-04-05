"""Rate limiting backends for VetoNet."""

import logging
import os
import threading
import time
from collections import OrderedDict
from typing import NamedTuple

logger = logging.getLogger(__name__)

MAX_TRACKED_KEYS = int(os.environ.get("RATE_LIMIT_MAX_KEYS", "10000"))


class RateLimitCheck(NamedTuple):
    allowed: bool
    remaining: int
    reset_at: int


class InMemoryBackend:
    """Thread-safe LRU-bounded sliding window rate limiter."""

    def __init__(self, max_keys: int = MAX_TRACKED_KEYS):
        self._data: OrderedDict[str, list[float]] = OrderedDict()
        self._lock = threading.Lock()
        self._max_keys = max_keys

    def check(self, key: str, limit: int, window: int) -> RateLimitCheck:
        now = time.time()
        window_start = now - window

        with self._lock:
            if key in self._data:
                self._data.move_to_end(key)
                self._data[key] = [t for t in self._data[key] if t > window_start]
            else:
                if len(self._data) >= self._max_keys:
                    self._data.popitem(last=False)
                self._data[key] = []

            current = len(self._data[key])
            reset_at = int(now + window)

            if current >= limit:
                return RateLimitCheck(False, 0, reset_at)

            self._data[key].append(now)
            return RateLimitCheck(True, limit - current - 1, reset_at)


class RedisBackend:
    """Redis-backed sliding window rate limiter using sorted sets + Lua."""

    LUA_SCRIPT = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
    local count = redis.call('ZCARD', key)
    if count >= limit then
        return {0, 0}
    end
    redis.call('ZADD', key, now, now .. ':' .. math.random(1000000))
    redis.call('EXPIRE', key, window + 10)
    return {1, limit - count - 1}
    """

    def __init__(self, redis_url: str):
        import redis as redis_lib

        self._redis = redis_lib.from_url(redis_url, socket_timeout=0.1, socket_connect_timeout=0.5)
        self._script = self._redis.register_script(self.LUA_SCRIPT)

    def check(self, key: str, limit: int, window: int) -> RateLimitCheck:
        now = time.time()
        reset_at = int(now + window)
        try:
            result = self._script(keys=[key], args=[now, window, limit])
            return RateLimitCheck(bool(result[0]), int(result[1]), reset_at)
        except Exception as e:
            logger.warning("Redis rate limit error: %s — falling back", e)
            return RateLimitCheck(True, limit, reset_at)  # fail-open on redis error only


class RateLimiter:
    """Unified rate limiter with optional Redis backend."""

    def __init__(self):
        self._memory = InMemoryBackend()
        self._redis: RedisBackend | None = None
        redis_url = os.environ.get("REDIS_URL")
        if redis_url:
            try:
                self._redis = RedisBackend(redis_url)
                self._redis._redis.ping()
                logger.info("Redis rate limiter connected")
            except Exception as e:
                logger.warning("Redis unavailable (%s), using in-memory rate limiting", e)
                self._redis = None

    def check(self, key: str, limit: int, window: int) -> RateLimitCheck:
        # Always update in-memory (maintains approximate state for fallback)
        mem_result = self._memory.check(key, limit, window)
        if self._redis:
            return self._redis.check(key, limit, window)
        return mem_result


_limiter: RateLimiter | None = None
_limiter_lock = threading.Lock()


def get_limiter() -> RateLimiter:
    global _limiter
    if _limiter is None:
        with _limiter_lock:
            if _limiter is None:
                _limiter = RateLimiter()
    return _limiter
