"""Redis-backed sliding-window-counter rate limiting.

Implements the "sliding window counter" algorithm (as popularized by
Cloudflare): O(1) memory, two fixed counters (current window + previous
window) weighted by how far into the current window we are — this avoids
the burst problem of naive fixed-window counting at window boundaries
without the O(N) memory cost of a true sliding log.

The read-weighted-estimate + conditional-increment is done in a single Lua
script executed atomically via EVAL/EVALSHA, so concurrent requests can't
race between reading the count and incrementing it (which a separate
GET-then-INCR from Python could).
"""

import os
import time

import redis.asyncio as redis
from fastapi import HTTPException, Request, status

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# KEYS[1] = current window key, KEYS[2] = previous window key
# ARGV[1] = limit, ARGV[2] = elapsed_fraction (0..1 as string), ARGV[3] = key TTL seconds
#
# GET on a key that doesn't exist returns Lua `false` (redis nil -> false),
# and `false or '0'` evaluates to '0' in Lua, so tonumber(...) always gets a
# numeric string. EXPIRE uses NX so a key's TTL is only set once, on the
# request that creates it — later requests in the same window bump the
# counter without repeatedly pushing the expiry further into the future.
_SLIDING_WINDOW_LUA = """
local current = tonumber(redis.call('GET', KEYS[1]) or '0')
local previous = tonumber(redis.call('GET', KEYS[2]) or '0')
local limit = tonumber(ARGV[1])
local elapsed_fraction = tonumber(ARGV[2])
local estimated = previous * (1 - elapsed_fraction) + current
if estimated >= limit then
    return {0, estimated}
end
current = redis.call('INCR', KEYS[1])
redis.call('EXPIRE', KEYS[1], ARGV[3], 'NX')
return {1, estimated + 1}
"""

_redis: redis.Redis | None = None
_script = None


def init_client() -> None:
    """Create the shared Redis client and register the Lua script. Call once on app startup."""
    global _redis, _script
    _redis = redis.from_url(REDIS_URL, decode_responses=True)
    _script = _redis.register_script(_SLIDING_WINDOW_LUA)


async def close_client() -> None:
    """Release the Redis connection. Call once on app shutdown."""
    global _redis, _script
    if _redis is not None:
        await _redis.aclose()
        _redis = None
        _script = None


async def is_allowed(bucket: str, identifier: str, limit: int, window_seconds: int) -> bool:
    """True if under the limit (and this call counts toward it), False if rate-limited.

    Fails OPEN (allows the request) if Redis is unreachable or not initialized
    (e.g. during tests, where app lifespan never runs) — availability over
    strictness for this use case.
    """
    if _script is None:
        return True
    now = time.time()
    window_index = int(now // window_seconds)
    elapsed_fraction = (now % window_seconds) / window_seconds
    current_key = f"ratelimit:{bucket}:{identifier}:{window_index}"
    previous_key = f"ratelimit:{bucket}:{identifier}:{window_index - 1}"
    try:
        allowed, _estimated = await _script(
            keys=[current_key, previous_key],
            args=[limit, elapsed_fraction, window_seconds * 2],
        )
        return bool(allowed)
    except redis.RedisError:
        return True


def rate_limit_dependency(bucket: str, limit: int, window_seconds: int):
    """FastAPI dependency factory. identifier = client IP (request.client.host)."""

    async def _dependency(request: Request) -> None:
        identifier = request.client.host if request.client else "unknown"
        if not await is_allowed(bucket, identifier, limit, window_seconds):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate limit exceeded, try again shortly",
                headers={"Retry-After": str(window_seconds)},
            )

    return _dependency
