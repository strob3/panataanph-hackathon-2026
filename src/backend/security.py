"""Rate limiting and request security primitives.

Uses stdlib collections.deque for in-memory sliding-window rate limiting.
Zero external dependencies.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Sliding-window in-memory rate limiter using stdlib collections.deque."""

    def __init__(self, max_requests: int, window_seconds: float) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: dict[str, deque[float]] = defaultdict(deque)

    def is_allowed(self, client_key: str) -> bool:
        now = time.monotonic()
        q = self._timestamps[client_key]
        # Purge older timestamps outside the window
        while q and now - q[0] > self.window_seconds:
            q.popleft()
        if len(q) >= self.max_requests:
            return False
        q.append(now)
        return True

    def reset(self) -> None:
        self._timestamps.clear()


RATE_LIMIT_ENABLED = os.getenv("PANATAANPH_RATE_LIMIT", "true").lower() in ("true", "1", "yes")

# Rate limiters for sensitive endpoints
login_limiter = InMemoryRateLimiter(max_requests=10, window_seconds=60.0)      # 10 / min
register_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60.0)    # 5 / min
submit_limiter = InMemoryRateLimiter(max_requests=20, window_seconds=60.0)     # 20 / min


def get_client_ip(request: Request) -> str:
    """Resolve client IP from direct socket or forwarded header."""
    if request.client and request.client.host:
        return request.client.host
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return "127.0.0.1"


def require_rate_limit(limiter: InMemoryRateLimiter, action: str) -> Callable[[Request], None]:
    """FastAPI dependency to enforce rate limiting on a specific action."""
    def dependency(request: Request) -> None:
        # Bypass during pytest test runs unless explicitly tested
        if not RATE_LIMIT_ENABLED or os.getenv("PYTEST_CURRENT_TEST"):
            return
        client_key = f"{action}:{get_client_ip(request)}"
        if not limiter.is_allowed(client_key):
            raise HTTPException(
                status_code=429,
                detail=f"Too many {action} requests. Please wait a moment.",
                headers={"Retry-After": str(int(limiter.window_seconds))},
            )
    return dependency
