"""Autenticação opcional por API key (header X-Api-Key)."""

from __future__ import annotations

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from audiotranscriber.config import get_app_config


class ApiKeyMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        cfg = get_app_config()
        if not cfg.api_key:
            return await call_next(request)

        if request.url.path in ("/health", "/docs", "/openapi.json", "/redoc"):
            return await call_next(request)

        provided = request.headers.get("X-Api-Key") or request.headers.get(
            "Authorization", ""
        ).removeprefix("Bearer ").strip()
        if provided != cfg.api_key:
            raise HTTPException(status_code=401, detail="API key inválida ou ausente.")
        return await call_next(request)
