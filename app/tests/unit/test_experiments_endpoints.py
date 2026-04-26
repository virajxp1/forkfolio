from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.endpoints import experiments
from app.core.dependencies import get_experiment_service
from app.services.experiment_service import (
    ExperimentThreadNotFoundError,
    ExperimentValidationError,
)

THREAD_ID = "11111111-1111-1111-1111-111111111111"
RECIPE_ID = "22222222-2222-2222-2222-222222222222"
MESSAGE_ID = "33333333-3333-3333-3333-333333333333"


class StubExperimentService:
    def list_threads(
        self,
        limit: int = 20,
        include_test: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        del viewer_user_id
        test_thread = {
            "id": "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            "mode": "invent_new",
            "title": "Experiment E2E seed",
            "metadata": {"orchestration": "langgraph-ready", "is_test": True},
            "created_by_user_id": None,
            "created_at": "2026-03-16T00:00:00+00:00",
            "updated_at": "2026-03-16T00:01:00+00:00",
            "last_message_role": "assistant",
            "last_message_content": "E2E assistant response.",
            "last_message_created_at": "2026-03-16T00:01:00+00:00",
        }
        return [
            {
                "id": THREAD_ID,
                "mode": "modify_existing",
                "title": "Veganize tikka masala",
                "metadata": {"orchestration": "langgraph-ready"},
                "created_by_user_id": None,
                "created_at": "2026-03-16T00:00:00+00:00",
                "updated_at": "2026-03-16T00:01:00+00:00",
                "last_message_role": "assistant",
                "last_message_content": "Use tofu and coconut yogurt.",
                "last_message_created_at": "2026-03-16T00:01:00+00:00",
            },
            *([test_thread] if include_test else []),
        ][:limit]

    def create_thread(
        self,
        mode: str,
        title: str | None = None,
        context_recipe_ids: list[str] | None = None,
        include_test_data: bool = False,
        is_test: bool = False,
        created_by_user_id: str | None = None,
    ) -> dict:
        del include_test_data
        if context_recipe_ids and RECIPE_ID not in context_recipe_ids:
            raise ExperimentValidationError(
                "One or more context recipes were not found.",
                missing_recipe_ids=context_recipe_ids,
            )
        return {
            "id": THREAD_ID,
            "mode": mode,
            "title": title,
            "metadata": {
                "orchestration": "langgraph-ready",
                **({"is_test": True} if is_test else {}),
            },
            "created_by_user_id": created_by_user_id,
            "context_recipe_ids": context_recipe_ids or [],
            "messages": [],
            "created_at": "2026-03-16T00:00:00+00:00",
            "updated_at": "2026-03-16T00:00:00+00:00",
        }

    def get_thread(
        self,
        thread_id: str,
        message_limit: int = 100,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> dict:
        del include_test_data
        del viewer_user_id
        if thread_id != THREAD_ID:
            raise ExperimentThreadNotFoundError("Experiment thread not found")
        return {
            "id": THREAD_ID,
            "mode": "modify_existing",
            "title": "Veganize tikka masala",
            "metadata": {"orchestration": "langgraph-ready"},
            "created_by_user_id": None,
            "context_recipe_ids": [RECIPE_ID],
            "messages": [
                {
                    "id": MESSAGE_ID,
                    "thread_id": THREAD_ID,
                    "sequence_no": 1,
                    "role": "user",
                    "content": "Make chicken tikka masala vegan",
                    "tool_name": None,
                    "tool_call": None,
                    "created_at": "2026-03-16T00:01:00+00:00",
                }
            ][:message_limit],
            "created_at": "2026-03-16T00:00:00+00:00",
            "updated_at": "2026-03-16T00:01:00+00:00",
        }

    def send_user_message(
        self,
        thread_id: str,
        content: str,
        context_recipe_ids: list[str] | None = None,
        attach_recipe_ids: list[str] | None = None,
        attach_recipe_names: list[str] | None = None,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> dict:
        del include_test_data
        del viewer_user_id
        if thread_id != THREAD_ID:
            raise ExperimentThreadNotFoundError("Experiment thread not found")
        if context_recipe_ids and RECIPE_ID not in context_recipe_ids:
            raise ExperimentValidationError(
                "One or more context recipes were not found.",
                missing_recipe_ids=context_recipe_ids,
            )
        return {
            "thread": self.get_thread(thread_id),
            "user_message": {
                "id": MESSAGE_ID,
                "thread_id": THREAD_ID,
                "sequence_no": 2,
                "role": "user",
                "content": content,
                "tool_name": None,
                "tool_call": None,
                "created_at": "2026-03-16T00:02:00+00:00",
            },
            "assistant_message": {
                "id": "44444444-4444-4444-4444-444444444444",
                "thread_id": THREAD_ID,
                "sequence_no": 3,
                "role": "assistant",
                "content": "Use tofu and coconut yogurt for the marinade.",
                "tool_name": None,
                "tool_call": None,
                "created_at": "2026-03-16T00:02:01+00:00",
            },
            "attached_recipes": [
                {"id": RECIPE_ID, "title": "Chicken Tikka Masala", "created_at": None}
            ]
            if attach_recipe_ids or attach_recipe_names
            else [],
            "unresolved_recipe_names": [],
            "attachment_message": None,
        }

    def stream_user_message(
        self,
        thread_id: str,
        content: str,
        context_recipe_ids: list[str] | None = None,
        attach_recipe_ids: list[str] | None = None,
        attach_recipe_names: list[str] | None = None,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ):
        del include_test_data
        del viewer_user_id
        if thread_id != THREAD_ID:
            raise ExperimentThreadNotFoundError("Experiment thread not found")
        yield {"event": "status", "data": {"step": "drafting"}}
        yield {"event": "delta", "data": {"text": "Use tofu and coconut yogurt."}}
        yield {
            "event": "final",
            "data": {
                "thread_id": THREAD_ID,
                "thread": self.get_thread(thread_id),
                "user_message": {
                    "id": MESSAGE_ID,
                    "thread_id": THREAD_ID,
                    "sequence_no": 2,
                    "role": "user",
                    "content": content,
                    "tool_name": None,
                    "tool_call": None,
                    "created_at": "2026-03-16T00:02:00+00:00",
                },
                "assistant_message": {
                    "id": "44444444-4444-4444-4444-444444444444",
                    "thread_id": THREAD_ID,
                    "sequence_no": 3,
                    "role": "assistant",
                    "content": "Use tofu and coconut yogurt.",
                    "tool_name": None,
                    "tool_call": None,
                    "created_at": "2026-03-16T00:02:01+00:00",
                },
                "attached_recipes": [],
                "unresolved_recipe_names": [],
                "attachment_message": None,
            },
        }


def build_experiments_app() -> FastAPI:
    app = FastAPI()
    app.include_router(experiments.router)
    app.dependency_overrides[get_experiment_service] = lambda: StubExperimentService()
    return app


def test_create_experiment_thread_success() -> None:
    client = TestClient(build_experiments_app())

    response = client.post(
        "/api/v1/experiments/threads",
        json={
            "mode": "modify_existing",
            "title": "Veganize tikka masala",
            "context_recipe_ids": [RECIPE_ID],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["thread"]["id"] == THREAD_ID
    assert body["thread"]["context_recipe_ids"] == [RECIPE_ID]


def test_create_experiment_thread_missing_context_recipe_returns_404() -> None:
    client = TestClient(build_experiments_app())

    response = client.post(
        "/api/v1/experiments/threads",
        json={"mode": "invent_new", "context_recipe_ids": [THREAD_ID]},
    )

    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["message"] == "One or more context recipes were not found."
    assert detail["missing_recipe_ids"] == [THREAD_ID]


def test_create_experiment_thread_rejects_invalid_viewer_header() -> None:
    client = TestClient(build_experiments_app())

    response = client.post(
        "/api/v1/experiments/threads",
        headers={"X-Viewer-User-Id": "not-a-uuid"},
        json={"mode": "invent_new"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid X-Viewer-User-Id header"


def test_get_experiment_thread_success() -> None:
    client = TestClient(build_experiments_app())

    response = client.get(f"/api/v1/experiments/threads/{THREAD_ID}")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["thread"]["id"] == THREAD_ID
    assert len(body["thread"]["messages"]) == 1


def test_list_experiment_threads_success() -> None:
    client = TestClient(build_experiments_app())

    response = client.get("/api/v1/experiments/threads")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["count"] == 1
    assert body["threads"][0]["id"] == THREAD_ID


def test_list_experiment_threads_with_include_test_param() -> None:
    client = TestClient(build_experiments_app())

    response = client.get("/api/v1/experiments/threads?include_test=true")

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["count"] == 2


def test_get_experiment_thread_not_found_returns_404() -> None:
    client = TestClient(build_experiments_app())

    response = client.get(f"/api/v1/experiments/threads/{RECIPE_ID}")

    assert response.status_code == 404
    assert response.json()["detail"] == "Experiment thread not found"


def test_create_experiment_message_success() -> None:
    client = TestClient(build_experiments_app())

    response = client.post(
        f"/api/v1/experiments/threads/{THREAD_ID}/messages",
        json={"content": "Make it nut-free too", "context_recipe_ids": [RECIPE_ID]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["thread_id"] == THREAD_ID
    assert body["assistant_message"]["role"] == "assistant"


def test_create_experiment_message_with_attach_names_success() -> None:
    client = TestClient(build_experiments_app())

    response = client.post(
        f"/api/v1/experiments/threads/{THREAD_ID}/messages",
        json={
            "content": "Attach chicken tikka masala",
            "attach_recipe_names": ["Chicken Tikka Masala"],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["attached_recipes"]) == 1


def test_create_experiment_message_with_attach_ids_success() -> None:
    client = TestClient(build_experiments_app())

    response = client.post(
        f"/api/v1/experiments/threads/{THREAD_ID}/messages",
        json={
            "content": "Attach exact recipe id",
            "attach_recipe_ids": [RECIPE_ID],
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert len(body["attached_recipes"]) == 1
    assert body["attached_recipes"][0]["id"] == RECIPE_ID


def test_create_experiment_message_invalid_thread_id_returns_422() -> None:
    client = TestClient(build_experiments_app())

    response = client.post(
        "/api/v1/experiments/threads/not-a-uuid/messages",
        json={"content": "hello"},
    )

    assert response.status_code == 422


def test_stream_experiment_message_success() -> None:
    client = TestClient(build_experiments_app())

    response = client.post(
        f"/api/v1/experiments/threads/{THREAD_ID}/messages/stream",
        json={"content": "Make it vegan"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: status" in response.text
    assert "event: delta" in response.text
    assert "event: final" in response.text
