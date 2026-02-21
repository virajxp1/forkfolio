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
