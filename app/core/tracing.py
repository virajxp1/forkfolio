from __future__ import annotations

import logging
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from braintrust import flush as _braintrust_flush
    from braintrust import init_logger as _braintrust_init_logger
    from braintrust import start_span as _braintrust_start_span
except ImportError:
    _braintrust_flush = None
    _braintrust_init_logger = None
    _braintrust_start_span = None

_TRACE_ID: ContextVar[str | None] = ContextVar("forkfolio_trace_id", default=None)
_TRACE_SOURCE: ContextVar[str] = ContextVar("forkfolio_trace_source", default="request")
_REQUEST_METHOD: ContextVar[str | None] = ContextVar(
    "forkfolio_trace_request_method", default=None
)
_REQUEST_PATH: ContextVar[str | None] = ContextVar(
    "forkfolio_trace_request_path", default=None
)
_SPAN_DEPTH: ContextVar[int] = ContextVar("forkfolio_trace_span_depth", default=0)
_ACTIVE_PARENT_EXPORT: ContextVar[str | None] = ContextVar(
    "forkfolio_trace_active_parent_export", default=None
)

_BRAINTRUST_ENABLED = False
_BRAINTRUST_INITIALIZED = False


@dataclass(frozen=True)
class TraceContextTokens:
    trace_id_token: Token[str | None]
    trace_source_token: Token[str]
    request_method_token: Token[str | None]
    request_path_token: Token[str | None]


def _safe_reset(var: ContextVar[Any], token: Token[Any], fallback: Any) -> None:
    try:
        var.reset(token)
    except ValueError:
        var.set(fallback)


def create_request_trace_id() -> str:
    return str(uuid4())


def bind_trace_context(
    trace_id: str,
    source: str,
    request_method: str,
    request_path: str,
) -> TraceContextTokens:
    return TraceContextTokens(
        trace_id_token=_TRACE_ID.set(trace_id),
        trace_source_token=_TRACE_SOURCE.set(source),
        request_method_token=_REQUEST_METHOD.set(request_method),
        request_path_token=_REQUEST_PATH.set(request_path),
    )


def reset_trace_context(tokens: TraceContextTokens) -> None:
    _safe_reset(_TRACE_ID, tokens.trace_id_token, None)
    _safe_reset(_TRACE_SOURCE, tokens.trace_source_token, "request")
    _safe_reset(_REQUEST_METHOD, tokens.request_method_token, None)
    _safe_reset(_REQUEST_PATH, tokens.request_path_token, None)
    _SPAN_DEPTH.set(0)
    _ACTIVE_PARENT_EXPORT.set(None)


def current_trace_id() -> str | None:
    return _TRACE_ID.get()


def current_trace_source() -> str:
    return _TRACE_SOURCE.get()


def current_request_method() -> str | None:
    return _REQUEST_METHOD.get()


def current_request_path() -> str | None:
    return _REQUEST_PATH.get()


def setup_braintrust() -> None:
    global _BRAINTRUST_ENABLED, _BRAINTRUST_INITIALIZED

    if _BRAINTRUST_INITIALIZED:
        return
    _BRAINTRUST_INITIALIZED = True

    if not settings.BRAINTRUST_TRACING_ENABLED:
        logger.info("Braintrust tracing: disabled")
        return

    if _braintrust_init_logger is None:
        logger.warning(
            "Braintrust tracing enabled but `braintrust` package is unavailable."
        )
        return

    project_id = settings.BRAINTRUST_PROJECT_ID.strip()
    if not project_id:
        logger.warning("Braintrust tracing enabled but no project ID is configured.")
        return

    api_key = settings.BRAINTRUST_API_KEY.strip()
    if not api_key:
        logger.warning(
            "Braintrust tracing enabled but BRAINTRUST_API_KEY is missing. "
            "Tracing will remain disabled."
        )
        return

    init_kwargs: dict[str, Any] = {
        "project_id": project_id,
        "set_current": True,
        "api_key": api_key,
    }
    if settings.BRAINTRUST_APP_URL:
        init_kwargs["app_url"] = settings.BRAINTRUST_APP_URL

    try:
        _braintrust_init_logger(**init_kwargs)
    except Exception as exc:
        logger.exception("Braintrust tracing initialization failed: %s", exc)
        _BRAINTRUST_ENABLED = False
        return

    _BRAINTRUST_ENABLED = True
    logger.info("Braintrust tracing: enabled (project_id=%s)", project_id)


def flush_braintrust() -> None:
    if not _BRAINTRUST_ENABLED or _braintrust_flush is None:
        return

    try:
        _braintrust_flush()
    except Exception as exc:
        logger.exception("Braintrust tracing flush failed: %s", exc)


@contextmanager
def start_trace_span(
    name: str,
    *,
    span_type: str | None = None,
    input_data: Any | None = None,
    output_data: Any | None = None,
    metadata: dict[str, Any] | None = None,
    metrics: dict[str, float | int] | None = None,
    root_trace_id: str | None = None,
):
    if not _BRAINTRUST_ENABLED or _braintrust_start_span is None:
        yield None
        return

    span_kwargs: dict[str, Any] = {"name": name}
    if span_type:
        span_kwargs["type"] = span_type

    span_depth = _SPAN_DEPTH.get()
    parent_export = _ACTIVE_PARENT_EXPORT.get()
    if parent_export:
        span_kwargs["parent"] = parent_export
    elif root_trace_id and span_depth == 0:
        span_kwargs["root_span_id"] = root_trace_id

    event_kwargs: dict[str, Any] = {}
    if input_data is not None:
        event_kwargs["input"] = input_data
    if output_data is not None:
        event_kwargs["output"] = output_data

    resolved_metadata = dict(metadata or {})
    trace_id = current_trace_id()
    if trace_id:
        resolved_metadata.setdefault("request_trace_id", trace_id)
    request_method = current_request_method()
    if request_method:
        resolved_metadata.setdefault("request_method", request_method)
    request_path = current_request_path()
    if request_path:
        resolved_metadata.setdefault("request_path", request_path)
    trace_source = current_trace_source()
    if trace_source:
        resolved_metadata.setdefault("trace_source", trace_source)
    if resolved_metadata:
        event_kwargs["metadata"] = resolved_metadata

    if metrics:
        event_kwargs["metrics"] = metrics

    with _braintrust_start_span(**span_kwargs, **event_kwargs) as span:
        span_depth_token = _SPAN_DEPTH.set(span_depth + 1)
        parent_export_token: Token[str | None] | None = None
        try:
            export_fn = getattr(span, "export", None)
            if callable(export_fn):
                exported = export_fn()
                if isinstance(exported, str) and exported:
                    parent_export_token = _ACTIVE_PARENT_EXPORT.set(exported)
        except Exception as exc:
            logger.debug("Braintrust span export failed: %s", exc)

        try:
            yield span
        finally:
            if parent_export_token is not None:
                _safe_reset(_ACTIVE_PARENT_EXPORT, parent_export_token, None)
            _safe_reset(_SPAN_DEPTH, span_depth_token, max(0, span_depth))


def log_span(span: Any, **event: Any) -> None:
    if span is None:
        return
    if not event:
        return

    try:
        span.log(**event)
    except Exception as exc:
        logger.debug("Braintrust span logging failed: %s", exc)
