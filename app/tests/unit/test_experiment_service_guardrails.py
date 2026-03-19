from __future__ import annotations

from datetime import UTC, datetime

from app.core.prompts import EXPERIMENT_AGENT_SCOPE_REFUSAL
from app.services.experiment_service import ExperimentService


class FakeRecipeManager:
    def get_full_recipe(self, recipe_id: str):
        del recipe_id
        return None

    def find_recipes_by_title_query(self, query: str, limit: int = 1):
        del query, limit
        return []


class FakeExperimentManager:
    def __init__(self) -> None:
        now = datetime.now(UTC).isoformat()
        self.thread = {
            "id": "thread-1",
            "mode": "invent_new",
            "title": None,
            "metadata": {"orchestration": "langgraph-ready"},
            "context_recipe_ids": [],
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        self.messages: list[dict] = []
        self._sequence = 0

    def get_thread(self, thread_id: str, message_limit: int = 100) -> dict | None:
        if thread_id != self.thread["id"]:
            return None
        payload = dict(self.thread)
        payload["context_recipe_ids"] = list(self.thread["context_recipe_ids"])
        payload["messages"] = self.list_messages(thread_id, limit=message_limit)
        return payload

    def set_context_recipe_ids(
        self, thread_id: str, context_recipe_ids: list[str]
    ) -> None:
        if thread_id == self.thread["id"]:
            self.thread["context_recipe_ids"] = list(context_recipe_ids)

    def create_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        tool_name=None,
        tool_call=None,
    ) -> dict | None:
        del tool_name, tool_call
        if thread_id != self.thread["id"]:
            return None
        self._sequence += 1
        message = {
            "id": f"msg-{self._sequence}",
            "thread_id": thread_id,
            "sequence_no": self._sequence,
            "role": role,
            "content": content,
            "tool_name": None,
            "tool_call": None,
            "created_at": datetime.now(UTC).isoformat(),
        }
        self.messages.append(message)
        return message

    def set_thread_title_if_empty(self, thread_id: str, title: str) -> bool:
        if thread_id != self.thread["id"]:
            return False
        if not self.thread["title"]:
            self.thread["title"] = title
        return True

    def list_messages(self, thread_id: str, limit: int = 100) -> list[dict]:
        if thread_id != self.thread["id"]:
            return []
        return list(self.messages[-max(1, limit) :])

    def get_context_recipe_ids(self, thread_id: str) -> list[str]:
        if thread_id != self.thread["id"]:
            return []
        return list(self.thread["context_recipe_ids"])

    def list_threads(self, limit: int = 20, include_test: bool = False) -> list[dict]:
        del include_test
        del limit
        return [dict(self.thread)]


def test_send_user_message_blocks_non_recipe_prompt_without_llm_call() -> None:
    text_call_count = 0

    def _text_generation(_: str, __: str) -> str:
        nonlocal text_call_count
        text_call_count += 1
        return "should not be used"

    service = ExperimentService(
        experiment_manager=FakeExperimentManager(),
        recipe_manager=FakeRecipeManager(),
        text_generation_fn=_text_generation,
        stream_generation_fn=lambda _user_prompt, _system_prompt: iter(()),
    )

    response = service.send_user_message(
        thread_id="thread-1",
        content="Write python code to invert a linked list.",
    )

    assert response["assistant_message"]["content"] == EXPERIMENT_AGENT_SCOPE_REFUSAL
    assert text_call_count == 0


def test_stream_user_message_blocks_non_recipe_prompt_without_stream_call() -> None:
    stream_call_count = 0

    def _stream_generation(_user_prompt: str, _system_prompt: str):
        nonlocal stream_call_count
        stream_call_count += 1
        yield "should not be used"

    service = ExperimentService(
        experiment_manager=FakeExperimentManager(),
        recipe_manager=FakeRecipeManager(),
        text_generation_fn=lambda _user_prompt, _system_prompt: "unused",
        stream_generation_fn=_stream_generation,
    )

    events = list(
        service.stream_user_message(
            thread_id="thread-1",
            content="Implement a binary tree in Java.",
        )
    )

    event_names = [event["event"] for event in events]
    assert "status" in event_names
    assert "delta" in event_names
    assert "final" in event_names
    final_event = next(event for event in events if event["event"] == "final")
    final_message = final_event["data"]["assistant_message"]["content"]
    assert final_message == EXPERIMENT_AGENT_SCOPE_REFUSAL
    assert stream_call_count == 0
