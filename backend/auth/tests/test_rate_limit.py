"""Direct unit tests for the sliding-window-counter rate limiter against a
real Redis instance (DB index 1, to avoid colliding with anything on DB 0).

Skipped cleanly if no local Redis is reachable — these are the one place in
the test suite that needs real Redis; everything else (the HTTP-level 429
wiring tests in test_auth.py) mocks `rate_limit.is_allowed` directly and
never touches a socket.
"""

import asyncio
import time

import pytest
import pytest_asyncio
import redis as redis_sync

from auth import rate_limit

pytestmark = pytest.mark.asyncio

_TEST_REDIS_URL = "redis://localhost:6379/1"


def _redis_reachable() -> bool:
    client = None
    try:
        client = redis_sync.Redis.from_url(_TEST_REDIS_URL, socket_connect_timeout=0.5)
        return bool(client.ping())
    except redis_sync.RedisError:
        return False
    finally:
        if client is not None:
            client.close()


requires_redis = pytest.mark.skipif(
    not _redis_reachable(),
    reason="no local Redis reachable at redis://localhost:6379/1 — skipping direct rate_limit tests",
)


@pytest_asyncio.fixture
async def rl(monkeypatch):
    """Point the rate_limit module at a scratch Redis DB and flush it clean."""
    monkeypatch.setattr(rate_limit, "REDIS_URL", _TEST_REDIS_URL)
    rate_limit.init_client()
    await rate_limit._redis.flushdb()
    yield rate_limit
    await rate_limit._redis.flushdb()
    await rate_limit.close_client()


@requires_redis
class TestSlidingWindowRateLimit:
    async def test_requests_under_the_limit_are_allowed(self, rl):
        for _ in range(5):
            assert await rl.is_allowed("bucket", "under-limit", limit=5, window_seconds=10) is True

    async def test_requests_over_the_limit_in_same_window_are_rejected(self, rl):
        for _ in range(5):
            assert await rl.is_allowed("bucket", "over-limit", limit=5, window_seconds=10) is True
        assert await rl.is_allowed("bucket", "over-limit", limit=5, window_seconds=10) is False
        # still rejected, doesn't "unstick" on repeated calls in the same window
        assert await rl.is_allowed("bucket", "over-limit", limit=5, window_seconds=10) is False

    async def test_identifiers_are_isolated_from_each_other(self, rl):
        for _ in range(5):
            assert await rl.is_allowed("bucket", "isolated-a", limit=5, window_seconds=10) is True
        assert await rl.is_allowed("bucket", "isolated-a", limit=5, window_seconds=10) is False
        # a different identifier in the same bucket has its own, untouched budget
        assert await rl.is_allowed("bucket", "isolated-b", limit=5, window_seconds=10) is True

    async def test_buckets_are_isolated_from_each_other(self, rl):
        for _ in range(5):
            assert await rl.is_allowed("bucket-x", "shared-id", limit=5, window_seconds=10) is True
        assert await rl.is_allowed("bucket-x", "shared-id", limit=5, window_seconds=10) is False
        # same identifier, different bucket: independent budget
        assert await rl.is_allowed("bucket-y", "shared-id", limit=5, window_seconds=10) is True

    async def test_sliding_window_weights_previous_window_across_boundary(self, rl, monkeypatch):
        """The test that actually proves this is a sliding window, not a fixed
        one. A fixed-window counter resets to 0 the instant the window index
        changes, so a client could burst `limit` requests at the very end of
        window N and another full `limit` at the very start of window N+1 —
        2x the limit within a few milliseconds. The sliding window instead
        weights window N's count by how little time has elapsed into window
        N+1, so right at the boundary the old window's usage still counts
        almost fully against the new one.
        """
        window_seconds = 10
        limit = 10
        bucket = "boundary"
        identifier = "boundary-id"
        window_index = 1_000_000  # arbitrary fixed window index, deterministic

        # Fill window `window_index - 1` completely, at its midpoint.
        prev_window_time = (window_index - 1) * window_seconds + 5
        monkeypatch.setattr(time, "time", lambda: prev_window_time)
        for _ in range(limit):
            assert await rl.is_allowed(bucket, identifier, limit, window_seconds) is True
        assert await rl.is_allowed(bucket, identifier, limit, window_seconds) is False

        # Cross into window `window_index`, essentially right at the boundary
        # (elapsed_fraction ~ 0.001). A fixed window would allow a fresh burst
        # of up to `limit` requests here; the sliding window only allows ~1
        # before the weighted estimate (previous window counted almost fully)
        # crosses the limit again.
        boundary_time = window_index * window_seconds + 0.01
        monkeypatch.setattr(time, "time", lambda: boundary_time)
        assert await rl.is_allowed(bucket, identifier, limit, window_seconds) is True
        assert await rl.is_allowed(bucket, identifier, limit, window_seconds) is False

        # Deeper into the new window, the previous window's weight has mostly
        # decayed away and close to a fresh quota is available again — this
        # is the "sliding" part: the effective limit eases back up smoothly
        # rather than staying stuck at 0 for the rest of the window.
        late_time = window_index * window_seconds + (window_seconds - 0.1)
        monkeypatch.setattr(time, "time", lambda: late_time)
        allowed_count = sum(
            [await rl.is_allowed(bucket, identifier, limit, window_seconds) for _ in range(limit)]
        )
        assert allowed_count >= limit - 2

    async def test_atomic_script_enforces_exact_limit_under_concurrency(self, rl):
        """Regression guard for the exact race the Lua script exists to prevent.

        A naive "GET count, check < limit, then INCR" implementation does the
        read and the write as two separate round trips. Under concurrency,
        many requests can all execute their GET before any of them executes
        its INCR, so they all observe the same pre-increment count, all decide
        they're under the limit, and all get admitted — over-admitting past N.

        Because the read-weighted-estimate-and-conditionally-increment happens
        inside a single EVAL, Redis executes it as one atomic step per caller
        (Redis is single-threaded for command/script execution), so concurrent
        callers are serialized and the limit is enforced exactly rather than
        approximately.
        """
        limit = 5
        results = await asyncio.gather(
            *[rl.is_allowed("concurrent", "concurrent-id", limit, window_seconds=10) for _ in range(50)]
        )
        assert sum(1 for allowed in results if allowed) == limit

    async def test_fails_open_when_client_not_initialized(self, monkeypatch):
        """Sanity check for the fail-open contract used everywhere else in the
        test suite: if init_client() was never called (as in the rest of the
        HTTP-level tests, since lifespan doesn't run under ASGITransport),
        is_allowed() must return True unconditionally rather than raising."""
        monkeypatch.setattr(rate_limit, "_script", None)
        assert await rate_limit.is_allowed("bucket", "id", limit=0, window_seconds=10) is True

    async def test_fails_open_on_redis_error(self, rl, monkeypatch):
        async def _boom(*args, **kwargs):
            raise redis_sync.RedisError("simulated outage")

        monkeypatch.setattr(rate_limit, "_script", _boom)
        assert await rl.is_allowed("bucket", "id", limit=0, window_seconds=10) is True
