"""Live E2E coverage for experiment thread/message flows."""

import json
import uuid
from typing import Any

from app.tests.clients.api_client import APIClient
from app.tests.utils.constants import HTTP_OK
from app.tests.utils.helpers import maybe_throttle

EXPERIMENT_SCOPE_REFUSAL_SUBSTRING = "recipe ideation and recipe modifications only"


def _build_recipe_input(title: str, run_id: str, variant: str) -> str:
    return (
        f"{title}\n\n"
        "Servings: 2\n"
        "Total time: 25 minutes\n\n"
        "Ingredients:\n"
        f"- 200g tofu ({variant})\n"
        "- 1 tbsp olive oil\n"
        f"- 1 tsp test-spice-{run_id}-{variant}\n\n"
        "Instructions:\n"
        "1. Heat oil.\n"
        f"2. Cook tofu ({variant}) until browned.\n"
        "3. Season and serve.\n"
    )


def _create_recipe(api_client: APIClient, title: str, run_id: str, variant: str) -> str:
    maybe_throttle()
    create_response = api_client.recipes.process_and_store_recipe(
        _build_recipe_input(title, run_id, variant),
        enforce_deduplication=False,
    )
    assert create_response["status_code"] == HTTP_OK
    create_data = create_response["data"]
    assert create_data.get("success") is True
    recipe_id = create_data.get("recipe_id")
    assert recipe_id
    return recipe_id


def _parse_sse_events(stream_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    current_event = "message"
    data_lines: list[str] = []

    def flush() -> None:
        nonlocal current_event
        if not data_lines:
            return
        payload_text = "\n".join(data_lines)
        try:
            payload: Any = json.loads(payload_text)
        except json.JSONDecodeError:
            payload = payload_text
        events.append({"event": current_event, "data": payload})
        current_event = "message"
        data_lines.clear()

    for line in stream_text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if not line:
            flush()
            continue
        if line.startswith("event:"):
            current_event = line.partition(":")[2].strip() or "message"
        elif line.startswith("data:"):
            data_lines.append(line.partition(":")[2].strip())

    flush()
    return events


def test_experiment_thread_crud_lifecycle(api_client: APIClient) -> None:
    run_id = uuid.uuid4().hex[:8]
    context_recipe_id = None

    try:
        context_recipe_id = _create_recipe(
            api_client,
            title=f"E2E Context Bowl {run_id}",
            run_id=run_id,
            variant="context",
        )

        create_thread_response = api_client.experiments.create_thread(
            mode="modify_existing",
            title=f"Experiment E2E {run_id}",
            context_recipe_ids=[context_recipe_id],
        )
        assert create_thread_response["status_code"] == HTTP_OK
        create_thread_data = create_thread_response["data"]
        assert create_thread_data.get("success") is True
        thread = create_thread_data.get("thread", {})
        thread_id = thread.get("id")
        assert thread_id
        assert context_recipe_id in (thread.get("context_recipe_ids") or [])

        list_threads_response = api_client.experiments.list_threads(
            limit=50,
            include_test=True,
        )
        assert list_threads_response["status_code"] == HTTP_OK
        list_data = list_threads_response["data"]
        assert list_data.get("success") is True
        listed_ids = [item.get("id") for item in list_data.get("threads", [])]
        assert thread_id in listed_ids

        get_thread_response = api_client.experiments.get_thread(thread_id)
        assert get_thread_response["status_code"] == HTTP_OK
        get_thread_data = get_thread_response["data"]
        assert get_thread_data.get("success") is True
        assert get_thread_data.get("thread", {}).get("id") == thread_id

        maybe_throttle()
        create_message_response = api_client.experiments.create_message(
            thread_id=thread_id,
            content="Make this fully vegan and weeknight-friendly.",
        )
        assert create_message_response["status_code"] == HTTP_OK
        message_data = create_message_response["data"]
        assert message_data.get("success") is True
        assert message_data.get("assistant_message", {}).get("role") == "assistant"

        get_after_message = api_client.experiments.get_thread(
            thread_id, message_limit=200
        )
        assert get_after_message["status_code"] == HTTP_OK
        messages = get_after_message["data"].get("thread", {}).get("messages", [])
        roles = [message.get("role") for message in messages]
        assert "user" in roles
        assert "assistant" in roles
    finally:
        if context_recipe_id:
            api_client.recipes.delete_recipe(context_recipe_id)


def test_experiment_stream_emits_events_and_persists(api_client: APIClient) -> None:
    run_id = uuid.uuid4().hex[:8]
    create_thread_response = api_client.experiments.create_thread(
        mode="invent_new",
        title=f"Stream E2E {run_id}",
    )
    assert create_thread_response["status_code"] == HTTP_OK
    thread_id = create_thread_response["data"].get("thread", {}).get("id")
    assert thread_id

    maybe_throttle()
    stream_response = api_client.experiments.stream_message(
        thread_id=thread_id,
        content="Invent a high-protein vegetarian dinner.",
    )
    assert stream_response["status_code"] == HTTP_OK
    content_type = stream_response["headers"].get("content-type", "")
    assert content_type.startswith("text/event-stream")

    events = _parse_sse_events(stream_response["text"])
    event_names = [event["event"] for event in events]
    assert "status" in event_names
    assert "delta" in event_names
    assert "final" in event_names

    final_event = next(event for event in events if event["event"] == "final")
    final_data = final_event["data"]
    assert isinstance(final_data, dict)
    assert final_data.get("thread_id") == thread_id
    assistant_message = final_data.get("assistant_message", {})
    assistant_id = assistant_message.get("id")
    assert assistant_id
    assistant_content = str(assistant_message.get("content") or "").strip()
    assert assistant_content

    get_thread_response = api_client.experiments.get_thread(
        thread_id, message_limit=200
    )
    assert get_thread_response["status_code"] == HTTP_OK
    thread_messages = get_thread_response["data"].get("thread", {}).get("messages", [])
    message_ids = [message.get("id") for message in thread_messages]
    assert assistant_id in message_ids


def test_experiment_attach_ids_uses_exact_recipe(api_client: APIClient) -> None:
    run_id = uuid.uuid4().hex[:8]
    shared_title = f"Collision Curry {run_id}"
    recipe_id_a = None
    recipe_id_b = None

    try:
        recipe_id_a = _create_recipe(
            api_client,
            title=shared_title,
            run_id=run_id,
            variant="alpha",
        )
        recipe_id_b = _create_recipe(
            api_client,
            title=shared_title,
            run_id=run_id,
            variant="beta",
        )
        assert recipe_id_a != recipe_id_b

        create_thread_response = api_client.experiments.create_thread(
            mode="modify_existing",
            title=f"Attach E2E {run_id}",
        )
        assert create_thread_response["status_code"] == HTTP_OK
        thread_id = create_thread_response["data"].get("thread", {}).get("id")
        assert thread_id

        maybe_throttle()
        create_message_response = api_client.experiments.create_message(
            thread_id=thread_id,
            content="Attach the selected collision recipe.",
            attach_recipe_ids=[recipe_id_b],
        )
        assert create_message_response["status_code"] == HTTP_OK
        message_data = create_message_response["data"]
        assert message_data.get("success") is True

        attached_ids = [
            recipe.get("id") for recipe in message_data.get("attached_recipes", [])
        ]
        assert recipe_id_b in attached_ids
        assert recipe_id_a not in attached_ids

        get_thread_response = api_client.experiments.get_thread(
            thread_id, message_limit=200
        )
        assert get_thread_response["status_code"] == HTTP_OK
        context_ids = (
            get_thread_response["data"].get("thread", {}).get("context_recipe_ids", [])
        )
        assert recipe_id_b in context_ids
        assert recipe_id_a not in context_ids
    finally:
        if recipe_id_a:
            api_client.recipes.delete_recipe(recipe_id_a)
        if recipe_id_b:
            api_client.recipes.delete_recipe(recipe_id_b)


def test_experiment_blocks_non_recipe_prompt(api_client: APIClient) -> None:
    run_id = uuid.uuid4().hex[:8]
    create_thread_response = api_client.experiments.create_thread(
        mode="invent_new",
        title=f"Guardrail E2E {run_id}",
    )
    assert create_thread_response["status_code"] == HTTP_OK
    thread_id = create_thread_response["data"].get("thread", {}).get("id")
    assert thread_id

    create_message_response = api_client.experiments.create_message(
        thread_id=thread_id,
        content="Write python code to invert a linked list.",
    )
    assert create_message_response["status_code"] == HTTP_OK
    body = create_message_response["data"]
    assert body.get("success") is True
    assistant_content = str(
        body.get("assistant_message", {}).get("content") or ""
    ).lower()
    assert EXPERIMENT_SCOPE_REFUSAL_SUBSTRING in assistant_content
