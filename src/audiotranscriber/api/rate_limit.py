"""Rate limiting simples por IP."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

_SKIP_PATHS = ("/health", "/docs", "/openapi.json", "/redoc")


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int, window_seconds: int) -> None:
        super().__init__(app)
        self._max = max_requests
        self._window = window_seconds
        self._hits: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - self._window
        hits = [t for t in self._hits[client] if t > window_start]
        if len(hits) >= self._max:
            raise HTTPException(
                status_code=429,
                detail="Limite de requisições excedido. Tente novamente em breve.",
            )
        hits.append(now)
        self._hits[client] = hits
        return await call_next(request)
