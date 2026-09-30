from __future__ import annotations

import threading
import time
from collections import deque

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from ..config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Sliding-window rate limit theo IP cho /api/*. 429 khi vượt ngưỡng."""

    def __init__(self, app, path_prefix: str = "/api") -> None:
        super().__init__(app)
        self.path_prefix = path_prefix
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allowed(self, ip: str, now: float, limit: int, window: float = 60.0) -> bool:
        """Logic thuần để dễ test: True nếu request được chấp nhận."""
        if limit <= 0:
            return True
        with self._lock:
            q = self._hits.setdefault(ip, deque())
            while q and now - q[0] >= window:
                q.popleft()
            if len(q) >= limit:
                return False
            q.append(now)
            return True

    async def dispatch(self, request, call_next):
        if request.url.path.startswith(self.path_prefix):
            ip = request.client.host if request.client else "unknown"
            if not self.allowed(ip, time.time(), settings.rate_limit_per_min):
                return JSONResponse(
                    {"detail": "Quá nhiều request, thử lại sau (rate limit)"},
                    status_code=429,
                )
        return await call_next(request)
