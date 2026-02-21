from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from collections import deque
from typing import Deque

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette import status
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_504_GATEWAY_TIMEOUT,
)

HTTP_413_REQUEST_TOO_LARGE = getattr(
    status, "HTTP_413_CONTENT_TOO_LARGE", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
)


class AuthTokenMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, token: str, exempt_paths: Iterable[str] = ()) -> None:
        super().__init__(app)
        self._token = token.strip()
        self._exempt_paths = {_normalize_path(path) for path in exempt_paths}

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self._token:
            return await call_next(request)
        if _normalize_path(request.url.path) in self._exempt_paths:
            return await call_next(request)

        header_token = request.headers.get("x-api-token")
        bearer = request.headers.get("authorization", "")
        if bearer.lower().startswith("bearer "):
            bearer = bearer.split(" ", 1)[1].strip()
        else:
            bearer = ""

        if header_token != self._token and bearer != self._token:
            return JSONResponse(
                {"detail": "Unauthorized"},
                status_code=HTTP_401_UNAUTHORIZED,
            )

        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        requests_per_minute: int,
    ) -> None:
        super().__init__(app)
        self._limit = max(1, requests_per_minute)
        self._window_seconds = 60.0
        self._buckets: dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        client_ip = _get_client_ip(request)
        now = time.monotonic()

        async with self._lock:
            bucket = self._buckets.get(client_ip)
            if bucket is None:
                bucket = deque()
                self._buckets[client_ip] = bucket

            while bucket and now - bucket[0] > self._window_seconds:
                bucket.popleft()

            if len(bucket) >= self._limit:
                retry_after = int(self._window_seconds - (now - bucket[0]))
                retry_after = max(1, retry_after)
                return JSONResponse(
                    {"detail": "Rate limit exceeded"},
                    status_code=HTTP_429_TOO_MANY_REQUESTS,
                    headers={"Retry-After": str(retry_after)},
                )

            bucket.append(now)

        return await call_next(request)


class RequestTimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, timeout_seconds: float) -> None:
        super().__init__(app)
        self._timeout_seconds = max(0.1, timeout_seconds)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        try:
            return await asyncio.wait_for(
                call_next(request), timeout=self._timeout_seconds
            )
        except asyncio.TimeoutError:
            return JSONResponse(
                {"detail": "Request timed out"},
                status_code=HTTP_504_GATEWAY_TIMEOUT,
            )


class RequestSizeLimitMiddleware:
    def __init__(self, app, max_body_size_bytes: int) -> None:
        self.app = app
        self._max_body_size = max(1, max_body_size_bytes)

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        content_length = headers.get("content-length")
        if content_length and content_length.isdigit():
            if int(content_length) > self._max_body_size:
                await _send_size_limit_response(scope, receive, send)
                return

        buffered_messages = []
        received = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                continue
            body = message.get("body", b"")
            received += len(body)
            if received > self._max_body_size:
                await _send_size_limit_response(scope, receive, send)
                return
            buffered_messages.append(message)
            if not message.get("more_body", False):
                break

        async def receive_wrapper():
            if buffered_messages:
                return buffered_messages.pop(0)
            return {"type": "http.request", "body": b"", "more_body": False}

        await self.app(scope, receive_wrapper, send)


def _get_client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


def _normalize_path(path: str) -> str:
    normalized = path.strip() or "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized


async def _send_size_limit_response(scope, receive, send) -> None:
    response = JSONResponse(
        {"detail": "Request too large"},
        status_code=HTTP_413_REQUEST_TOO_LARGE,
    )
    await response(scope=scope, receive=receive, send=send)
