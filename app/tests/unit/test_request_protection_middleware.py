import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.middleware import (
    AuthTokenMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    RequestTimeoutMiddleware,
)


def build_app(
    *,
    token: str = "",
    rate_limit: int = 100,
    max_body_bytes: int = 1024,
    timeout_seconds: float = 1.0,
) -> FastAPI:
    app = FastAPI()

    @app.get("/ok")
    async def ok() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/echo")
    async def echo() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/slow")
    async def slow() -> dict[str, bool]:
        await asyncio.sleep(0.2)
        return {"ok": True}

    app.add_middleware(RequestTimeoutMiddleware, timeout_seconds=timeout_seconds)
    app.add_middleware(AuthTokenMiddleware, token=token)
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=rate_limit,
    )
    app.add_middleware(RequestSizeLimitMiddleware, max_body_size_bytes=max_body_bytes)

    return app


def test_auth_token_required() -> None:
    client = TestClient(build_app(token="secret"))

    assert client.get("/ok").status_code == 401
    assert client.get("/ok", headers={"X-API-Token": "secret"}).status_code == 200


def test_rate_limit_applies_to_unauthorized_requests() -> None:
    client = TestClient(build_app(token="secret", rate_limit=1))

    first = client.get("/ok")
    second = client.get("/ok")

    assert first.status_code == 401
    assert second.status_code == 429


def test_request_size_limit_blocks_large_payloads() -> None:
    client = TestClient(build_app(max_body_bytes=4))

    response = client.post(
        "/echo",
        content=b"12345",
        headers={"Content-Type": "application/octet-stream"},
    )

    assert response.status_code == 413


def test_request_timeout_returns_504() -> None:
    client = TestClient(build_app(timeout_seconds=0.05))

    response = client.get("/slow")

    assert response.status_code == 504


def test_rate_limit_ignores_forwarded_for() -> None:
    client = TestClient(build_app(rate_limit=1))

    first = client.get("/ok", headers={"X-Forwarded-For": "1.1.1.1"})
    second = client.get("/ok", headers={"X-Forwarded-For": "2.2.2.2"})

    assert first.status_code == 200
    assert second.status_code == 429
