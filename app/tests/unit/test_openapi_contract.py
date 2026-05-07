import app.main as main_module
from app.core.config import settings

HTTP_METHODS = {"get", "put", "post", "delete", "patch", "options", "head", "trace"}
REQUIRED_GLOBAL_RESPONSES = {"413", "500", "504"}
REQUIRED_PROTECTED_RESPONSES = {"401", "429"}


def _normalize_path(path: str) -> str:
    normalized = (path or "").strip()
    if not normalized:
        return "/"
    if not normalized.startswith("/"):
        normalized = f"/{normalized}"
    if normalized != "/":
        normalized = normalized.rstrip("/")
    return normalized or "/"


def test_openapi_includes_auth_security_schemes(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "init_connection_pool", lambda: None)
    monkeypatch.setattr(main_module, "close_connection_pool", lambda: None)
    schema = main_module.create_application().openapi()

    security_schemes = schema["components"]["securitySchemes"]
    assert "ApiTokenHeader" in security_schemes
    assert "ApiTokenBearer" in security_schemes


def test_openapi_declares_auth_and_common_error_responses(monkeypatch) -> None:
    monkeypatch.setattr(main_module, "init_connection_pool", lambda: None)
    monkeypatch.setattr(main_module, "close_connection_pool", lambda: None)
    schema = main_module.create_application().openapi()

    public_paths = {
        _normalize_path(settings.API_BASE_PATH),
        _normalize_path(f"{settings.API_BASE_PATH}/health"),
    }

    for path, path_item in schema["paths"].items():
        normalized_path = _normalize_path(path)
        for method, operation in path_item.items():
            if method not in HTTP_METHODS:
                continue

            responses = operation["responses"]
            missing_global = REQUIRED_GLOBAL_RESPONSES - set(responses)
            assert not missing_global, (
                f"{method.upper()} {path} missing global responses: "
                f"{sorted(missing_global)}"
            )

            if normalized_path in public_paths:
                continue

            security = operation.get("security", [])
            assert {"ApiTokenHeader": []} in security
            assert {"ApiTokenBearer": []} in security

            missing_protected = REQUIRED_PROTECTED_RESPONSES - set(responses)
            assert not missing_protected, (
                f"{method.upper()} {path} missing protected responses: "
                f"{sorted(missing_protected)}"
            )
