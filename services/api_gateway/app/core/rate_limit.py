"""Redis-backed rate limiting.

A sliding-window-log limiter implemented as a single atomic Lua script, so the
read-count-and-increment happens in one Redis round trip with no race between
replicas. Keys are scoped per-route and per-identity (authenticated user when a
valid token is present, otherwise client IP), which is what lets this scale to
many API replicas behind a load balancer: every replica shares the same counters.
"""

import math
import uuid

import redis.asyncio as aioredis
from fastapi import HTTPException, Request, status
from jose import JWTError, jwt

from app.config import settings

# KEYS[1] = bucket key
# ARGV[1] = limit (max requests per window)
# ARGV[2] = window size in milliseconds
# ARGV[3] = unique member id for this request
#
# Returns {allowed (1/0), remaining, retry_after_ms}. The current time is read
# from Redis (`TIME`) rather than the app server so counters are immune to clock
# skew across replicas.
_SLIDING_WINDOW_LUA = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window = tonumber(ARGV[2])
local member = ARGV[3]

local t = redis.call('TIME')
local now = tonumber(t[1]) * 1000 + math.floor(tonumber(t[2]) / 1000)

redis.call('ZREMRANGEBYSCORE', key, 0, now - window)
local count = redis.call('ZCARD', key)

if count < limit then
  redis.call('ZADD', key, now, member)
  redis.call('PEXPIRE', key, window)
  return {1, limit - count - 1, 0}
end

local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
local retry = window
if oldest[2] then
  retry = (tonumber(oldest[2]) + window) - now
end
if retry < 0 then retry = 0 end
return {0, 0, retry}
"""

_redis: aioredis.Redis | None = None
_script = None


def init_rate_limiter() -> None:
    """Create the shared Redis client and register the Lua script. Call once on startup."""
    global _redis, _script
    if not settings.REDIS_URL:
        # No Redis configured -> limiter is disabled (fail open). Loud on purpose.
        print("WARNING: REDIS_URL not set; rate limiting is DISABLED")
        return
    _redis = aioredis.from_url(
        settings.REDIS_URL, encoding="utf-8", decode_responses=True
    )
    _script = _redis.register_script(_SLIDING_WINDOW_LUA)


async def close_rate_limiter() -> None:
    """Close the shared Redis client. Call once on shutdown."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


def _identity(request: Request) -> str:
    """Per-user key when a valid bearer token is present, else per-IP.

    The token signature is verified so a caller can't dodge their own quota by
    forging a different `sub`. IP keying assumes a trusted proxy sets
    X-Forwarded-For (true behind the k8s ingress); the first hop is the client.
    """
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            payload = jwt.decode(
                auth[7:], settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            sub = payload.get("sub")
            if sub:
                return f"user:{sub}"
        except JWTError:
            pass

    xff = request.headers.get("x-forwarded-for")
    if xff:
        return f"ip:{xff.split(',')[0].strip()}"
    client = request.client
    return f"ip:{client.host if client else 'unknown'}"


class RateLimiter:
    """FastAPI dependency enforcing `times` requests per `seconds` for a scope.

    Usage:
        @router.post("/login", dependencies=[Depends(RateLimiter(10, 60, "auth:login"))])
    """

    def __init__(self, times: int, seconds: int, scope: str | None = None):
        self.times = times
        self.window_ms = seconds * 1000
        self.scope = scope

    async def __call__(self, request: Request) -> None:
        if _script is None:
            # Limiter not initialised (no Redis) -> allow the request.
            return

        scope = self.scope or request.url.path
        key = f"rl:{scope}:{_identity(request)}"

        try:
            allowed, _remaining, retry_ms = await _script(
                keys=[key], args=[self.times, self.window_ms, uuid.uuid4().hex]
            )
        except Exception as exc:
            # Fail open: a Redis blip must not take down the API. Worth alerting on.
            print(f"WARNING: rate limiter unavailable, allowing request: {exc}")
            return

        if not allowed:
            retry_after = max(1, math.ceil(retry_ms / 1000))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Try again later.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(self.times),
                    "X-RateLimit-Remaining": "0",
                },
            )
