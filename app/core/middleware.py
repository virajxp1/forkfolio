from __future__ import annotations

import asyncio
import time
from collections.abc import Iterable
from collections import deque
from typing import Deque
from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette import status
from starlette.status import (
    HTTP_401_UNAUTHORIZED,
    HTTP_429_TOO_MANY_REQUESTS,
    HTTP_504_GATEWAY_TIMEOUT,
)

from app.core.tracing import (
    bind_trace_context,
    create_request_trace_id,
    reset_trace_context,
)

HTTP_413_REQUEST_TOO_LARGE = getattr(
    status, "HTTP_413_CONTENT_TOO_LARGE", status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
)


class TraceContextMiddleware:
    def __init__(self, app, api_base_path: str = "/api/v1") -> None:
        self.app = app
        normalized_base_path = _normalize_path(api_base_path)
        self._experiment_thread_prefix = f"{normalized_base_path}/experiments/threads/"

    def _resolve_trace(self, request_path: str) -> tuple[str, str]:
        thread_trace_id = self._extract_experiment_thread_id(request_path)
        if thread_trace_id:
            return thread_trace_id, "thread"
        return create_request_trace_id(), "request"

    def _extract_experiment_thread_id(self, request_path: str) -> str | None:
        if not request_path.startswith(self._experiment_thread_prefix):
            return None

        suffix = request_path[len(self._experiment_thread_prefix) :]
        candidate = suffix.split("/", maxsplit=1)[0].strip()
        if not candidate:
            return None

        try:
            return str(UUID(candidate))
        except ValueError:
            return None

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_path = str(scope.get("path") or "/")
        request_method = str(scope.get("method") or "GET").upper()
        trace_id, trace_source = self._resolve_trace(request_path)

        tokens = bind_trace_context(
            trace_id=trace_id,
            source=trace_source,
            request_method=request_method,
            request_path=request_path,
        )
        try:
            await self.app(scope, receive, send)
        finally:
            reset_trace_context(tokens)


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
        exempt_paths: Iterable[str] = (),
    ) -> None:
        super().__init__(app)
        self._limit = max(1, requests_per_minute)
        self._window_seconds = 60.0
        self._exempt_paths = {_normalize_path(path) for path in exempt_paths}
        self._buckets: dict[str, Deque[float]] = {}
        self._lock = asyncio.Lock()

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if _normalize_path(request.url.path) in self._exempt_paths:
            return await call_next(request)

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
            # Delegate to the original receive channel after the buffered request body
            # is consumed so downstream middleware can observe disconnect messages.
            return await receive()

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
