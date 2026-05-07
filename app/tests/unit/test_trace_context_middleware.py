import json
from uuid import UUID, uuid4

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from fastapi.testclient import TestClient

from app.core.middleware import TraceContextMiddleware
from app.core.tracing import current_trace_id, current_trace_source


def _build_app() -> FastAPI:
    app = FastAPI()

    @app.get("/api/v1/recipes/probe")
    async def recipe_probe() -> dict[str, str | None]:
        return {
            "trace_id": current_trace_id(),
            "trace_source": current_trace_source(),
        }

    @app.get("/api/v1/experiments/threads/{thread_id}/probe")
    async def thread_probe(thread_id: str) -> dict[str, str | None]:
        return {
            "thread_id": thread_id,
            "trace_id": current_trace_id(),
            "trace_source": current_trace_source(),
        }

    @app.get("/api/v1/experiments/threads/{thread_id}/stream")
    async def thread_stream(thread_id: str):
        def event_stream():
            payload = {
                "thread_id": thread_id,
                "trace_id": current_trace_id(),
                "trace_source": current_trace_source(),
            }
            yield f"data: {json.dumps(payload)}\n\n"

        return StreamingResponse(event_stream(), media_type="text/event-stream")

    app.add_middleware(TraceContextMiddleware, api_base_path="/api/v1")
    return app


def test_trace_context_uses_request_id_outside_experiment_threads() -> None:
    client = TestClient(_build_app())

    response = client.get("/api/v1/recipes/probe")

    assert response.status_code == 200
    body = response.json()
    assert body["trace_source"] == "request"
    assert body["trace_id"]
    assert str(UUID(body["trace_id"])) == body["trace_id"]


def test_trace_context_uses_thread_id_for_experiment_thread_routes() -> None:
    client = TestClient(_build_app())
    thread_id = str(uuid4())

    response = client.get(f"/api/v1/experiments/threads/{thread_id}/probe")

    assert response.status_code == 200
    body = response.json()
    assert body["thread_id"] == thread_id
    assert body["trace_source"] == "thread"
    assert body["trace_id"] == thread_id


def test_trace_context_is_available_during_streaming_response() -> None:
    client = TestClient(_build_app())
    thread_id = str(uuid4())

    response = client.get(f"/api/v1/experiments/threads/{thread_id}/stream")

    assert response.status_code == 200
    data_line = next(
        line for line in response.text.splitlines() if line.startswith("data: ")
    )
    payload = json.loads(data_line[len("data: ") :])
    assert payload["thread_id"] == thread_id
    assert payload["trace_source"] == "thread"
    assert payload["trace_id"] == thread_id
