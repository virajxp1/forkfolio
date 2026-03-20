from contextlib import contextmanager

from app.core import tracing


def test_nested_trace_spans_do_not_reapply_root_span_id(monkeypatch) -> None:
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
    assert span_calls[0]["root_span_id"] == "trace-123"
    assert "root_span_id" not in span_calls[1]
    assert span_calls[1]["parent"] == "export:root-span"
