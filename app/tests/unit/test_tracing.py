from contextlib import contextmanager

from app.core import tracing


def test_nested_trace_spans_use_parent_export_without_synthetic_root(
    monkeypatch,
) -> None:
    span_calls: list[dict] = []

    class _FakeSpan:
        def __init__(self, name: str) -> None:
            self._name = name

        def export(self) -> str:
            return f"export:{self._name}"

    @contextmanager
    def _fake_start_span(**kwargs):
        span_calls.append(kwargs)
        yield _FakeSpan(str(kwargs.get("name", "")))

    monkeypatch.setattr(tracing, "_BRAINTRUST_ENABLED", True)
    monkeypatch.setattr(tracing, "_braintrust_start_span", _fake_start_span)

    tokens = tracing.bind_trace_context(
        trace_id="trace-123",
        source="request",
        request_method="GET",
        request_path="/api/v1/test",
    )
    try:
        with tracing.start_trace_span(name="root-span", span_type="task"):
            with tracing.start_trace_span(name="child-span", span_type="llm"):
                pass
    finally:
        tracing.reset_trace_context(tokens)

    assert len(span_calls) == 2
    assert "root_span_id" not in span_calls[0]
    assert "root_span_id" not in span_calls[1]
    assert span_calls[1]["parent"] == "export:root-span"
    assert span_calls[0]["metadata"]["request_trace_id"] == "trace-123"
    assert span_calls[0]["metadata"]["request_method"] == "GET"
    assert span_calls[0]["metadata"]["request_path"] == "/api/v1/test"
    assert span_calls[0]["metadata"]["trace_source"] == "request"


def test_top_level_span_can_set_explicit_root_trace_id(monkeypatch) -> None:
    span_calls: list[dict] = []

    class _FakeSpan:
        def __init__(self, name: str) -> None:
            self._name = name

        def export(self) -> str:
            return f"export:{self._name}"

    @contextmanager
    def _fake_start_span(**kwargs):
        span_calls.append(kwargs)
        yield _FakeSpan(str(kwargs.get("name", "")))

    monkeypatch.setattr(tracing, "_BRAINTRUST_ENABLED", True)
    monkeypatch.setattr(tracing, "_braintrust_start_span", _fake_start_span)

    tokens = tracing.bind_trace_context(
        trace_id="trace-123",
        source="request",
        request_method="POST",
        request_path="/api/v1/recipes",
    )
    try:
        with tracing.start_trace_span(
            name="top-level",
            span_type="llm",
            root_trace_id="explicit-root",
        ):
            with tracing.start_trace_span(name="child", span_type="task"):
                pass
    finally:
        tracing.reset_trace_context(tokens)

    assert len(span_calls) == 2
    assert span_calls[0]["root_span_id"] == "explicit-root"
    assert "root_span_id" not in span_calls[1]
    assert span_calls[1]["parent"] == "export:top-level"


def test_setup_braintrust_requires_api_key(monkeypatch) -> None:
    init_calls: list[dict] = []

    def _fake_init_logger(**kwargs) -> None:
        init_calls.append(kwargs)

    monkeypatch.setattr(tracing, "_braintrust_init_logger", _fake_init_logger)
    monkeypatch.setattr(tracing, "_BRAINTRUST_ENABLED", False)
    monkeypatch.setattr(tracing, "_BRAINTRUST_INITIALIZED", False)
    monkeypatch.setattr(tracing.settings, "BRAINTRUST_TRACING_ENABLED", True)
    monkeypatch.setattr(tracing.settings, "BRAINTRUST_PROJECT_ID", "project-123")
    monkeypatch.setattr(
        tracing.settings,
        "BRAINTRUST_APP_URL",
        "https://www.braintrust.dev",
    )
    monkeypatch.setattr(tracing.settings, "BRAINTRUST_API_KEY", "")

    tracing.setup_braintrust()

    assert tracing._BRAINTRUST_INITIALIZED is True
    assert tracing._BRAINTRUST_ENABLED is False
    assert not init_calls
