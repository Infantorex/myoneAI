"""Lightweight in-memory rate limiter for resource-intensive web endpoints (Phase 11).

Protects against request flooding and accidental loops without heavy dependencies like Redis.
"""

import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, Request, status


class RateLimiter:
    """Sliding-window in-memory rate limiter by client IP."""

    def __init__(self, max_requests: int = 30, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def check(self, request: Request) -> bool:
        """Verify if current client request exceeds allowed threshold.

        Raises:
            HTTPException: 429 Too Many Requests if rate limit is exceeded.
        """
        client_ip = "127.0.0.1"
        if request.client and request.client.host:
            client_ip = request.client.host

        now = time.time()
        window_start = now - self.window_seconds

        # Evict timestamps outside current sliding window
        valid_timestamps = [t for t in self._requests[client_ip] if t > window_start]
        valid_timestamps.append(now)
        self._requests[client_ip] = valid_timestamps

        if len(valid_timestamps) > self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "success": False,
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Too many requests. Limit is {self.max_requests} per {self.window_seconds} seconds.",
                    },
                },
            )
        return True


# Global rate limiter instances
chat_limiter = RateLimiter(max_requests=30, window_seconds=60)
control_limiter = RateLimiter(max_requests=20, window_seconds=60)
