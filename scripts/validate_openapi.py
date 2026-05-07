#!/usr/bin/env python3
from __future__ import annotations

from collections.abc import Iterator

from openapi_spec_validator import validate_spec

import app.main as main_module
from app.core.config import settings

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}
REQUIRED_GLOBAL_RESPONSES = {"413", "500", "504"}
REQUIRED_PROTECTED_RESPONSES = {"401", "429"}
REQUIRED_SECURITY_SCHEMES = {"ApiTokenHeader", "ApiTokenBearer"}


def _normalize_path(path: str) -> str:
    normalized = (path or "").strip()
    if not normalized:
        return "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized or "/"


def _iter_operations(spec: dict) -> Iterator[tuple[str, str, dict]]:
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() not in HTTP_METHODS:
                continue
            if not isinstance(operation, dict):
                continue
            yield method.upper(), path, operation


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def main() -> None:
    # Avoid opening DB pools while building OpenAPI for contract validation.
    main_module.init_connection_pool = lambda: None
    main_module.close_connection_pool = lambda: None

    app = main_module.create_application()
    schema = app.openapi()
    validate_spec(schema)

    components = schema.get("components", {})
    security_schemes = components.get("securitySchemes", {})
    _expect(
        REQUIRED_SECURITY_SCHEMES.issubset(set(security_schemes)),
        "OpenAPI is missing one or more required security schemes.",
    )

    public_paths = {
        _normalize_path(settings.API_BASE_PATH),
        _normalize_path(f"{settings.API_BASE_PATH}/health"),
    }

    operations = list(_iter_operations(schema))
    _expect(bool(operations), "OpenAPI has no operations.")

    for method, path, operation in operations:
        path_normalized = _normalize_path(path)
        responses = operation.get("responses", {})
        _expect(
            isinstance(responses, dict),
            f"{method} {path} has malformed responses in OpenAPI.",
        )

        missing_global = REQUIRED_GLOBAL_RESPONSES - set(responses)
        _expect(
            not missing_global,
            f"{method} {path} is missing global responses: {sorted(missing_global)}",
        )

        if path_normalized in public_paths:
            continue

        security = operation.get("security", [])
        _expect(
            isinstance(security, list)
            and {"ApiTokenHeader": []} in security
            and {"ApiTokenBearer": []} in security,
            f"{method} {path} is missing required security declarations.",
        )

        missing_protected = REQUIRED_PROTECTED_RESPONSES - set(responses)
        _expect(
            not missing_protected,
            f"{method} {path} is missing protected responses: {sorted(missing_protected)}",
        )

    print(
        f"OpenAPI validation passed for {len(operations)} operations with required auth and error contracts."
    )


if __name__ == "__main__":
    main()
