from contextlib import contextmanager
from types import SimpleNamespace
from uuid import uuid4

from app.core.cache import TTLCache
from app.services import llm_generation_service


class _FakeCompletions:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=""))]
        )


class _FakeEmbeddings:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **_kwargs):
        self.calls += 1
        return SimpleNamespace(
            data=[SimpleNamespace(embedding=[0.12, 0.34, 0.56])],
            usage=None,
        )


def test_make_llm_call_text_generation_caches_empty_string(monkeypatch) -> None:
    fake_completions = _FakeCompletions()
    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=fake_completions))
    cache = TTLCache[str](ttl_seconds=60, max_items=10)

    monkeypatch.setattr(llm_generation_service, "_get_chat_model_name", lambda: "test")
    monkeypatch.setattr(
        llm_generation_service, "_get_openai_client", lambda: fake_client
    )
    monkeypatch.setattr(llm_generation_service, "llm_text_cache", cache)

    suffix = uuid4().hex
    user_prompt = f"user-prompt-{suffix}"
    system_prompt = f"system-prompt-{suffix}"

    first = llm_generation_service.make_llm_call_text_generation(
        user_prompt=user_prompt, system_prompt=system_prompt
    )
    second = llm_generation_service.make_llm_call_text_generation(
        user_prompt=user_prompt, system_prompt=system_prompt
    )

    assert first == ""
    assert second == ""
    assert fake_completions.calls == 1


def test_stream_llm_call_text_generation_logs_output_on_completion(
    monkeypatch,
) -> None:
    class _FakeCompletionsStream:
        def create(self, **_kwargs):
            return iter(
                [
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(delta=SimpleNamespace(content="hello "))
                        ]
                    ),
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(delta=SimpleNamespace(content="world"))
                        ]
                    ),
                ]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=_FakeCompletionsStream())
    )
    cache = TTLCache[str](ttl_seconds=60, max_items=10)
    captured_logs: list[dict] = []

    @contextmanager
    def _fake_span(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(llm_generation_service, "_get_chat_model_name", lambda: "test")
    monkeypatch.setattr(
        llm_generation_service, "_get_openai_client", lambda: fake_client
    )
    monkeypatch.setattr(llm_generation_service, "llm_text_cache", cache)
    monkeypatch.setattr(llm_generation_service, "start_trace_span", _fake_span)
    monkeypatch.setattr(
        llm_generation_service,
        "log_span",
        lambda _span, **event: captured_logs.append(event),
    )

    chunks = list(
        llm_generation_service.stream_llm_call_text_generation(
            user_prompt="u", system_prompt="s"
        )
    )

    assert chunks == ["hello ", "world"]
    assert captured_logs
    final_log = captured_logs[-1]
    assert final_log["output"]["content"] == "hello world"
    assert final_log["output"]["messages"][0]["role"] == "assistant"
    assert final_log["output"]["messages"][0]["content"] == "hello world"
    assert final_log["metadata"]["stream_completed"] is True
    assert "stream_interrupted" not in final_log["metadata"]


def test_stream_llm_call_text_generation_logs_output_when_closed_early(
    monkeypatch,
) -> None:
    class _FakeCompletionsStream:
        def create(self, **_kwargs):
            return iter(
                [
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(delta=SimpleNamespace(content="hello "))
                        ]
                    ),
                    SimpleNamespace(
                        choices=[
                            SimpleNamespace(delta=SimpleNamespace(content="world"))
                        ]
                    ),
                ]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=_FakeCompletionsStream())
    )
    cache = TTLCache[str](ttl_seconds=60, max_items=10)
    captured_logs: list[dict] = []

    @contextmanager
    def _fake_span(*_args, **_kwargs):
        yield object()

    monkeypatch.setattr(llm_generation_service, "_get_chat_model_name", lambda: "test")
    monkeypatch.setattr(
        llm_generation_service, "_get_openai_client", lambda: fake_client
    )
    monkeypatch.setattr(llm_generation_service, "llm_text_cache", cache)
    monkeypatch.setattr(llm_generation_service, "start_trace_span", _fake_span)
    monkeypatch.setattr(
        llm_generation_service,
        "log_span",
        lambda _span, **event: captured_logs.append(event),
    )

    stream = llm_generation_service.stream_llm_call_text_generation(
        user_prompt="u",
        system_prompt="s",
    )
    assert next(stream) == "hello "
    stream.close()

    assert captured_logs
    final_log = captured_logs[-1]
    assert final_log["output"]["content"] == "hello "
    assert final_log["output"]["messages"][0]["role"] == "assistant"
    assert final_log["output"]["messages"][0]["content"] == "hello "
    assert final_log["metadata"]["stream_completed"] is False
    assert final_log["metadata"]["stream_interrupted"] is True


def test_make_embedding_uses_cache_and_returns_copy(monkeypatch) -> None:
    fake_embeddings = _FakeEmbeddings()
    fake_client = SimpleNamespace(embeddings=fake_embeddings)
    cache = TTLCache[list[float]](ttl_seconds=60, max_items=10)

    monkeypatch.setattr(
        llm_generation_service, "_get_embeddings_model_name", lambda: "test-embedding"
    )
    monkeypatch.setattr(
        llm_generation_service, "_get_openai_client", lambda: fake_client
    )
    monkeypatch.setattr(llm_generation_service, "embedding_cache", cache)

    first = llm_generation_service.make_embedding("cache me")
    first[0] = 9.99
    second = llm_generation_service.make_embedding("cache me")

    assert second == [0.12, 0.34, 0.56]
    assert fake_embeddings.calls == 1
