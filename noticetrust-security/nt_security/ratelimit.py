"""Sliding-window rate limiter (in-memory, per process). See SECURITY.md for limits."""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


def client_ip(request: Request, trust_proxy: bool) -> str:
    if trust_proxy:
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[-1].strip()      # rightmost = added by our own proxy
    return request.client.host if request.client else "unknown"


class RateLimiter:
    def __init__(self, limit: int, window_s: int, trust_proxy: bool = False, max_keys: int = 50_000):
        self.limit, self.window, self.trust_proxy, self.max_keys = limit, window_s, trust_proxy, max_keys
        self.hits: dict[str, deque] = defaultdict(deque)

    def __call__(self, request: Request):
        now = time.monotonic()
        if len(self.hits) > self.max_keys:         # bound memory under many-IP floods
            self.hits.clear()
        q = self.hits[client_ip(request, self.trust_proxy)]
        while q and q[0] <= now - self.window:
            q.popleft()
        if len(q) >= self.limit:
            raise HTTPException(429, "Too many requests. Please slow down.",
                                headers={"Retry-After": str(self.window)})
        q.append(now)
