from types import SimpleNamespace
from uuid import uuid4

from pydantic import BaseModel

from app.core.cache import TTLCache
from app.services import llm_generation_service


class _FakeStructuredCompletions:
    def __init__(
        self,
        *,
        content,
        finish_reason: str = "stop",
        refusal: str | None = None,
        tool_calls=None,
    ) -> None:
        self.calls = 0
        self._content = content
        self._finish_reason = finish_reason
        self._refusal = refusal
        self._tool_calls = tool_calls

    def create(self, **_kwargs):
        self.calls += 1
        message = SimpleNamespace(content=self._content)
        if self._refusal is not None:
            message.refusal = self._refusal
        if self._tool_calls is not None:
            message.tool_calls = self._tool_calls
        choice = SimpleNamespace(message=message, finish_reason=self._finish_reason)
        return SimpleNamespace(choices=[choice])


class _SequenceStructuredCompletions:
    def __init__(self, responses: list[dict]) -> None:
        self.calls = 0
        self.kwargs_history: list[dict] = []
        self._responses = responses

    def create(self, **kwargs):
        self.calls += 1
        self.kwargs_history.append(kwargs)
        index = min(self.calls - 1, len(self._responses) - 1)
        response = self._responses[index]

        message = SimpleNamespace(content=response.get("content"))
        refusal = response.get("refusal")
        if refusal is not None:
            message.refusal = refusal

        tool_calls = response.get("tool_calls")
        if tool_calls is not None:
            message.tool_calls = tool_calls

        finish_reason = response.get("finish_reason", "stop")
        choice = SimpleNamespace(message=message, finish_reason=finish_reason)
        return SimpleNamespace(choices=[choice])


class _StructuredResponseModel(BaseModel):
    ingredients: list[str]


def test_structured_output_handles_missing_content(monkeypatch) -> None:
    fake_completions = _FakeStructuredCompletions(content=None, refusal="safety")
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=fake_completions))
    cache = TTLCache[dict](ttl_seconds=60, max_items=10)

    monkeypatch.setattr(llm_generation_service, "_get_chat_model_name", lambda: "test")
    monkeypatch.setattr(
        llm_generation_service, "_get_openai_client", lambda: fake_client
    )
    monkeypatch.setattr(llm_generation_service, "llm_structured_cache", cache)

    suffix = uuid4().hex
    result, error = llm_generation_service.make_llm_call_structured_output_generic(
        user_prompt=f"user-prompt-{suffix}",
        system_prompt=f"system-prompt-{suffix}",
        model_class=_StructuredResponseModel,
        schema_name="structured_output_missing_content_test",
    )

    assert result is None
    assert error is not None
    assert "Model returned no JSON content." in error
    assert "Refusal: safety" in error
    assert "finish_reason=stop" in error
    assert fake_completions.calls == 1


def test_structured_output_retries_truncated_json_then_succeeds(monkeypatch) -> None:
    fake_completions = _SequenceStructuredCompletions(
        responses=[
            {
                "content": '{"ingredients":["1 tomato"',
                "finish_reason": "length",
            },
            {
                "content": '{"ingredients":["1 tomato"]}',
                "finish_reason": "stop",
            },
        ]
    )
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=fake_completions))
    cache = TTLCache[dict](ttl_seconds=60, max_items=10)

    monkeypatch.setattr(llm_generation_service, "_get_chat_model_name", lambda: "test")
    monkeypatch.setattr(
        llm_generation_service, "_get_openai_client", lambda: fake_client
    )
    monkeypatch.setattr(llm_generation_service, "llm_structured_cache", cache)
    monkeypatch.setattr(
        llm_generation_service.settings,
        "LLM_STRUCTURED_OUTPUT_MAX_ATTEMPTS",
        2,
    )
    monkeypatch.setattr(
        llm_generation_service.settings, "LLM_STRUCTURED_MAX_TOKENS", 250
    )

    suffix = uuid4().hex
    result, error = llm_generation_service.make_llm_call_structured_output_generic(
        user_prompt=f"user-prompt-{suffix}",
        system_prompt=f"system-prompt-{suffix}",
        model_class=_StructuredResponseModel,
        schema_name="structured_output_retry_success_test",
    )

    assert error is None
    assert result is not None
    assert result.ingredients == ["1 tomato"]
    assert fake_completions.calls == 2
    assert [kwargs["max_tokens"] for kwargs in fake_completions.kwargs_history] == [
        250,
        500,
    ]


def test_structured_output_returns_error_after_retry_exhaustion(monkeypatch) -> None:
    fake_completions = _SequenceStructuredCompletions(
        responses=[
            {
                "content": '{"ingredients":["1 tomato"',
                "finish_reason": "length",
            },
        ]
    )
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=fake_completions))
    cache = TTLCache[dict](ttl_seconds=60, max_items=10)

    monkeypatch.setattr(llm_generation_service, "_get_chat_model_name", lambda: "test")
    monkeypatch.setattr(
        llm_generation_service, "_get_openai_client", lambda: fake_client
    )
    monkeypatch.setattr(llm_generation_service, "llm_structured_cache", cache)
    monkeypatch.setattr(
        llm_generation_service.settings,
        "LLM_STRUCTURED_OUTPUT_MAX_ATTEMPTS",
        2,
    )
    monkeypatch.setattr(
        llm_generation_service.settings, "LLM_STRUCTURED_MAX_TOKENS", 250
    )

    suffix = uuid4().hex
    result, error = llm_generation_service.make_llm_call_structured_output_generic(
        user_prompt=f"user-prompt-{suffix}",
        system_prompt=f"system-prompt-{suffix}",
        model_class=_StructuredResponseModel,
        schema_name="structured_output_retry_exhaustion_test",
    )

    assert result is None
    assert error is not None
    assert "Failed to parse JSON response" in error
    assert fake_completions.calls == 2
