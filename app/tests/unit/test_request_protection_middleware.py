import asyncio
from collections.abc import Sequence

from fastapi import FastAPI
from fastapi.testclient import TestClient

import app.main as main_module
from app.core.config import settings
from app.core.middleware import (
    AuthTokenMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    RequestTimeoutMiddleware,
)


def build_app(
    *,
    token: str = "",
    exempt_paths: Sequence[str] = (),
    rate_limit: int = 100,
    rate_limit_exempt_paths: Sequence[str] = (),
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
    app.add_middleware(
        AuthTokenMiddleware,
        token=token,
        exempt_paths=exempt_paths,
    )
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=rate_limit,
        exempt_paths=rate_limit_exempt_paths,
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


def test_auth_token_exempt_path_allowed_without_token() -> None:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(AuthTokenMiddleware, token="secret", exempt_paths=("/health",))
    client = TestClient(app)

    assert client.get("/health").status_code == 200


def test_rate_limit_exempt_path_does_not_consume_bucket() -> None:
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/protected")
    async def protected() -> dict[str, bool]:
        return {"ok": True}

    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=1,
        exempt_paths=("/health",),
    )
    client = TestClient(app)

    assert client.get("/health").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.get("/protected").status_code == 200
    assert client.get("/protected").status_code == 429


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


def test_create_application_health_is_public_and_other_paths_require_token(
    monkeypatch,
) -> None:
    monkeypatch.setattr(main_module, "init_connection_pool", lambda: None)
    monkeypatch.setattr(main_module, "close_connection_pool", lambda: None)
    monkeypatch.setattr(settings, "API_AUTH_TOKEN", "secret-token")

    health_path = f"{settings.API_BASE_PATH}/health"
    protected_probe_path = f"{settings.API_BASE_PATH}/_protected_probe"

    with TestClient(main_module.create_application()) as client:
        health_response = client.get(health_path)
        protected_response = client.get(protected_probe_path)
        authed_response = client.get(
            protected_probe_path,
            headers={"X-API-Token": "secret-token"},
        )

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert protected_response.status_code == 401
    assert authed_response.status_code == 404
