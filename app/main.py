from contextlib import asynccontextmanager
from copy import deepcopy

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.core.middleware import (
    AuthTokenMiddleware,
    RateLimitMiddleware,
    RequestSizeLimitMiddleware,
    RequestTimeoutMiddleware,
)
from app.routers import api
from app.services.data.supabase_client import (
    close_connection_pool,
    init_connection_pool,
)

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}

ERROR_DETAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "detail": {"type": "string"},
    },
    "required": ["detail"],
}

MIDDLEWARE_RESPONSES = {
    "413": {
        "description": "Request payload exceeds size limit.",
        "content": {
            "application/json": {
                "schema": ERROR_DETAIL_SCHEMA,
                "example": {"detail": "Request too large"},
            }
        },
    },
    "504": {
        "description": "Request processing exceeded timeout.",
        "content": {
            "application/json": {
                "schema": ERROR_DETAIL_SCHEMA,
                "example": {"detail": "Request timed out"},
            }
        },
    },
}

PROTECTED_RESPONSES = {
    "401": {
        "description": "Missing or invalid API token.",
        "content": {
            "application/json": {
                "schema": ERROR_DETAIL_SCHEMA,
                "example": {"detail": "Unauthorized"},
            }
        },
    },
    "429": {
        "description": "Rate limit exceeded.",
        "headers": {
            "Retry-After": {
                "description": "Seconds before the client should retry.",
                "schema": {"type": "integer", "minimum": 1},
            }
        },
        "content": {
            "application/json": {
                "schema": ERROR_DETAIL_SCHEMA,
                "example": {"detail": "Rate limit exceeded"},
            }
        },
    },
}

SERVER_ERROR_RESPONSE = {
    "500": {
        "description": "Unexpected server-side failure.",
        "content": {
            "application/json": {
                "schema": ERROR_DETAIL_SCHEMA,
                "example": {"detail": "Internal server error"},
            }
        },
    }
}


def _normalize_openapi_path(path: str) -> str:
    normalized = (path or "").strip()
    if not normalized:
        return "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized or "/"


def _customize_openapi_schema(
    application: FastAPI,
    public_paths: tuple[str, ...],
) -> dict:
    if application.openapi_schema:
        return application.openapi_schema

    openapi_schema = get_openapi(
        title=application.title,
        version=application.version,
        description=application.description,
        routes=application.routes,
    )

    components = openapi_schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes.setdefault(
        "ApiTokenHeader",
        {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Token",
            "description": "Set API token in the X-API-Token header.",
        },
    )
    security_schemes.setdefault(
        "ApiTokenBearer",
        {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API token",
            "description": "Send API token as Authorization: Bearer <token>.",
        },
    )

    normalized_public_paths = {_normalize_openapi_path(path) for path in public_paths}

    for path, path_item in openapi_schema.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue

        is_public_path = _normalize_openapi_path(path) in normalized_public_paths

        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                continue

            responses = operation.setdefault("responses", {})
            if not isinstance(responses, dict):
                continue

            for status_code, response_schema in MIDDLEWARE_RESPONSES.items():
                responses.setdefault(status_code, deepcopy(response_schema))
            for status_code, response_schema in SERVER_ERROR_RESPONSE.items():
                responses.setdefault(status_code, deepcopy(response_schema))

            if is_public_path:
                continue

            operation.setdefault(
                "security",
                [{"ApiTokenHeader": []}, {"ApiTokenBearer": []}],
            )
            for status_code, response_schema in PROTECTED_RESPONSES.items():
                responses.setdefault(status_code, deepcopy(response_schema))

    application.openapi_schema = openapi_schema
    return application.openapi_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load environment variables on startup
    load_dotenv()

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    logger.info(
        "Request protection: rate_limit_per_min=%s max_body_mb=%s timeout_s=%s",
        settings.RATE_LIMIT_PER_MINUTE,
        settings.MAX_REQUEST_SIZE_MB,
        settings.REQUEST_TIMEOUT_SECONDS,
    )
    if settings.API_AUTH_TOKEN:
        logger.info("API auth token: enabled")
    else:
        logger.warning("API auth token: disabled")

    # Initialize database connection pool
    init_connection_pool()

    yield

    # Cleanup on shutdown
    close_connection_pool()


def _public_paths(api_root_path: str) -> tuple[str, ...]:
    return (
        api_root_path,
        f"{api_root_path}/health",
    )


def create_application() -> FastAPI:
    api_root_path = settings.API_BASE_PATH
    public_paths = _public_paths(api_root_path)

    application = FastAPI(
        title=settings.PROJECT_NAME,
        description=settings.PROJECT_DESCRIPTION,
        version=settings.VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # Include routers
    application.include_router(api.router)

    def custom_openapi() -> dict:
        return _customize_openapi_schema(application, public_paths)

    application.openapi = custom_openapi

    # Middleware (added in order from innermost to outermost)
    application.add_middleware(
        RequestTimeoutMiddleware, timeout_seconds=settings.REQUEST_TIMEOUT_SECONDS
    )
    application.add_middleware(
        AuthTokenMiddleware,
        token=settings.API_AUTH_TOKEN,
        exempt_paths=public_paths,
    )
    application.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        exempt_paths=public_paths,
    )
    application.add_middleware(
        RequestSizeLimitMiddleware,
        max_body_size_bytes=settings.MAX_REQUEST_SIZE_MB * 1024 * 1024,
    )

    return application


app = create_application()
