from __future__ import annotations

from contextlib import contextmanager
from datetime import UTC, datetime

from psycopg2.extras import Json

from app.core.prompts import EXPERIMENT_AGENT_SCOPE_REFUSAL
from app.services.data.managers.experiment_manager import ExperimentManager
from app.services.experiment_service import ExperimentService


class FakeRecipeManager:
    def __init__(self, recipes: dict[str, dict] | None = None) -> None:
        self.recipes: dict[str, dict] = recipes or {}
        self.exact_calls: list[dict] = []
        self.prefix_calls: list[dict] = []

    def get_full_recipe(
        self,
        recipe_id: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ):
        del include_test_data, viewer_user_id
        recipe = self.recipes.get(recipe_id)
        if recipe is None:
            return None
        return dict(recipe)

    def get_recipe_metadata(
        self,
        recipe_id: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ):
        del include_test_data, viewer_user_id
        recipe = self.recipes.get(recipe_id)
        if not recipe:
            return None
        return {
            "id": recipe["id"],
            "title": recipe.get("title"),
            "created_at": recipe.get("created_at"),
        }

    def find_recipe_by_exact_title(
        self,
        title: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> dict | None:
        self.exact_calls.append(
            {
                "title": title,
                "include_test_data": include_test_data,
                "viewer_user_id": viewer_user_id,
            }
        )
        normalized = title.strip().lower()
        for recipe in self.recipes.values():
            if str(recipe.get("title") or "").strip().lower() == normalized:
                return self.get_recipe_metadata(
                    recipe["id"],
                    include_test_data=include_test_data,
                    viewer_user_id=viewer_user_id,
                )
        return None

    def find_recipe_by_title_prefix(
        self,
        title_prefix: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> dict | None:
        self.prefix_calls.append(
            {
                "title_prefix": title_prefix,
                "include_test_data": include_test_data,
                "viewer_user_id": viewer_user_id,
            }
        )
        normalized = title_prefix.strip().lower()
        matches = [
            recipe
            for recipe in self.recipes.values()
            if str(recipe.get("title") or "").strip().lower().startswith(normalized)
        ]
        if not matches:
            return None
        matches.sort(
            key=lambda recipe: (
                len(str(recipe.get("title") or "")),
                str(recipe.get("created_at") or ""),
            )
        )
        return self.get_recipe_metadata(
            matches[0]["id"],
            include_test_data=include_test_data,
            viewer_user_id=viewer_user_id,
        )


class FakeEmbeddingsService:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def embed_search_query(self, query: str) -> list[float]:
        self.calls.append(query)
        return [0.1, 0.2, 0.3]


class FakeHybridSearchService:
    def __init__(self, results_by_query: dict[str, list[dict]] | None = None) -> None:
        self.results_by_query = results_by_query or {}
        self.calls: list[dict] = []

    def search(
        self,
        query: str,
        query_embedding: list[float],
        limit: int = 10,
        *,
        weights: tuple[float, float, float] | None = None,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        self.calls.append(
            {
                "query": query,
                "query_embedding": query_embedding,
                "limit": limit,
                "weights": weights,
                "include_test_data": include_test_data,
                "viewer_user_id": viewer_user_id,
            }
        )
        return self.results_by_query.get(query, [])


class FakeExperimentManager:
    def __init__(self) -> None:
        now = datetime.now(UTC).isoformat()
        self.thread = {
            "id": "thread-1",
            "title": None,
            "metadata": {"orchestration": "langgraph-ready"},
            "created_by_user_id": None,
            "context_recipe_ids": [],
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        self.messages: list[dict] = []
        self._sequence = 0

    def get_thread(
        self,
        thread_id: str,
        message_limit: int = 100,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> dict | None:
        del include_test_data, viewer_user_id
        if thread_id != self.thread["id"]:
            return None
        payload = dict(self.thread)
        payload["context_recipe_ids"] = list(self.thread["context_recipe_ids"])
        payload["messages"] = self.list_messages(thread_id, limit=message_limit)
        return payload

    def set_context_recipe_ids(
        self,
        thread_id: str,
        context_recipe_ids: list[str],
        viewer_user_id: str | None = None,
    ) -> None:
        del viewer_user_id
        if thread_id == self.thread["id"]:
            self.thread["context_recipe_ids"] = list(context_recipe_ids)

    def create_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        tool_name=None,
        tool_call=None,
        viewer_user_id: str | None = None,
    ) -> dict | None:
        del tool_name, tool_call, viewer_user_id
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

    def set_thread_title_if_empty(
        self,
        thread_id: str,
        title: str,
        viewer_user_id: str | None = None,
    ) -> bool:
        del viewer_user_id
        if thread_id != self.thread["id"]:
            return False
        if not self.thread["title"]:
            self.thread["title"] = title
        return True

    def list_messages(
        self,
        thread_id: str,
        limit: int = 100,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        del viewer_user_id
        if thread_id != self.thread["id"]:
            return []
        return list(self.messages[-max(1, limit) :])

    def get_context_recipe_ids(
        self,
        thread_id: str,
        include_test_data: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[str]:
        del include_test_data, viewer_user_id
        if thread_id != self.thread["id"]:
            return []
        return list(self.thread["context_recipe_ids"])

    def list_threads(
        self,
        limit: int = 20,
        include_test: bool = False,
        viewer_user_id: str | None = None,
    ) -> list[dict]:
        del include_test, limit, viewer_user_id
        return [dict(self.thread)]


class FakeCursor:
    def __init__(self, *, fetchone_results=None):
        self._fetchone_results = list(fetchone_results or [])
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        if not self._fetchone_results:
            return None
        return self._fetchone_results.pop(0)


def _patch_db_context(monkeypatch, manager, cursor):
    def fake_get_db_context():
        @contextmanager
        def _ctx():
            yield None, cursor

        return _ctx()

    monkeypatch.setattr(manager, "get_db_context", fake_get_db_context)


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


def test_build_context_payload_includes_full_recipe_content() -> None:
    service = ExperimentService(
        experiment_manager=FakeExperimentManager(),
        recipe_manager=FakeRecipeManager(
            recipes={
                "recipe-1": {
                    "id": "recipe-1",
                    "title": "Creamy Tomato Pasta",
                    "servings": "4",
                    "total_time": "35 minutes",
                    "ingredients": [
                        "12 oz pasta",
                        "2 tbsp olive oil",
                        "4 cloves garlic",
                        "1 onion",
                        "1 tsp chili flakes",
                        "28 oz tomatoes",
                        "1/2 cup cream",
                        "1/2 cup parmesan",
                        "1 tbsp butter",
                    ],
                    "instructions": [
                        "Boil the pasta.",
                        "Saute the aromatics.",
                        "Simmer the sauce.",
                        "Finish with cream and cheese.",
                    ],
                }
            }
        ),
        text_generation_fn=lambda _user_prompt, _system_prompt: "unused",
        stream_generation_fn=lambda _user_prompt, _system_prompt: iter(()),
    )

    payload = service._build_context_payload(["recipe-1"])

    assert payload == [
        {
            "id": "recipe-1",
            "title": "Creamy Tomato Pasta",
            "servings": "4",
            "total_time": "35 minutes",
            "ingredients": [
                "12 oz pasta",
                "2 tbsp olive oil",
                "4 cloves garlic",
                "1 onion",
                "1 tsp chili flakes",
                "28 oz tomatoes",
                "1/2 cup cream",
                "1/2 cup parmesan",
                "1 tbsp butter",
            ],
            "instructions": [
                "Boil the pasta.",
                "Saute the aromatics.",
                "Simmer the sauce.",
                "Finish with cream and cheese.",
            ],
        }
    ]


def test_create_thread_insert_omits_mode_column(monkeypatch) -> None:
    manager = ExperimentManager()
    cursor = FakeCursor(
        fetchone_results=[
            {
                "id": "thread-1",
                "title": "Weeknight curry",
                "metadata": {"orchestration": "langgraph-ready"},
                "created_by_user_id": "user-123",
                "created_at": None,
                "updated_at": None,
            },
        ]
    )
    _patch_db_context(monkeypatch, manager, cursor)

    thread = manager.create_thread(
        title="Weeknight curry",
        metadata={"orchestration": "langgraph-ready"},
        created_by_user_id="user-123",
    )

    assert thread["id"] == "thread-1"
    query, params = cursor.executed[0]
    assert "INSERT INTO experiment_threads" in query
    assert "mode" not in query
    assert len(params) == 3
    assert params[0] == "Weeknight curry"
    assert isinstance(params[1], Json)
    assert params[1].adapted == {"orchestration": "langgraph-ready"}
    assert params[2] == "user-123"


def test_resolve_attach_recipe_names_uses_exact_title_match_before_embedding() -> None:
    recipe_manager = FakeRecipeManager(
        recipes={
            "recipe-1": {
                "id": "recipe-1",
                "title": "Chicken Tikka Masala",
                "created_at": "2026-04-26T00:00:00+00:00",
            }
        }
    )
    embeddings_service = FakeEmbeddingsService()
    hybrid_search_service = FakeHybridSearchService(
        {
            "Chicken Tikka Masala": [
                {
                    "id": "recipe-1",
                    "name": "Chicken Tikka Masala",
                    "distance": 0.01,
                }
            ]
        }
    )
    service = ExperimentService(
        experiment_manager=FakeExperimentManager(),
        recipe_manager=recipe_manager,
        recipe_embeddings_service=embeddings_service,
        recipe_hybrid_search_service=hybrid_search_service,
        text_generation_fn=lambda _user_prompt, _system_prompt: "unused",
        stream_generation_fn=lambda _user_prompt, _system_prompt: iter(()),
    )

    attached, unresolved = service._resolve_attach_recipe_names(
        ["Chicken Tikka Masala"]
    )

    assert attached == [
        {
            "id": "recipe-1",
            "title": "Chicken Tikka Masala",
            "created_at": "2026-04-26T00:00:00+00:00",
        }
    ]
    assert unresolved == []
    assert embeddings_service.calls == []
    assert hybrid_search_service.calls == []


def test_resolve_attach_recipe_names_uses_prefix_title_match_before_embedding() -> None:
    recipe_manager = FakeRecipeManager(
        recipes={
            "recipe-1": {
                "id": "recipe-1",
                "title": "Chicken Tikka Masala",
                "created_at": "2026-04-26T00:00:00+00:00",
            }
        }
    )
    embeddings_service = FakeEmbeddingsService()
    hybrid_search_service = FakeHybridSearchService()
    service = ExperimentService(
        experiment_manager=FakeExperimentManager(),
        recipe_manager=recipe_manager,
        recipe_embeddings_service=embeddings_service,
        recipe_hybrid_search_service=hybrid_search_service,
        text_generation_fn=lambda _user_prompt, _system_prompt: "unused",
        stream_generation_fn=lambda _user_prompt, _system_prompt: iter(()),
    )

    attached, unresolved = service._resolve_attach_recipe_names(["Chicken Tikka"])

    assert attached == [
        {
            "id": "recipe-1",
            "title": "Chicken Tikka Masala",
            "created_at": "2026-04-26T00:00:00+00:00",
        }
    ]
    assert unresolved == []
    assert embeddings_service.calls == []
    assert hybrid_search_service.calls == []


def test_resolve_attach_recipe_names_falls_back_to_hybrid_search_on_title_miss() -> (
    None
):
    embeddings_service = FakeEmbeddingsService()
    hybrid_search_service = FakeHybridSearchService(
        {
            "Chikn Tikka Masala": [
                {
                    "id": "recipe-1",
                    "name": "Chicken Tikka Masala",
                    "distance": 0.01,
                    "created_at": "2026-04-26T00:00:00+00:00",
                }
            ]
        }
    )
    service = ExperimentService(
        experiment_manager=FakeExperimentManager(),
        recipe_manager=FakeRecipeManager(),
        recipe_embeddings_service=embeddings_service,
        recipe_hybrid_search_service=hybrid_search_service,
        text_generation_fn=lambda _user_prompt, _system_prompt: "unused",
        stream_generation_fn=lambda _user_prompt, _system_prompt: iter(()),
    )

    attached, unresolved = service._resolve_attach_recipe_names(["Chikn Tikka Masala"])

    assert attached == [
        {
            "id": "recipe-1",
            "title": "Chicken Tikka Masala",
            "created_at": "2026-04-26T00:00:00+00:00",
        }
    ]
    assert unresolved == []
    assert embeddings_service.calls == ["Chikn Tikka Masala"]
    assert hybrid_search_service.calls == [
        {
            "query": "Chikn Tikka Masala",
            "query_embedding": [0.1, 0.2, 0.3],
            "limit": 1,
            "weights": None,
            "include_test_data": False,
            "viewer_user_id": None,
        }
    ]


def test_resolve_attach_recipe_names_marks_unresolved_when_hybrid_search_finds_nothing() -> (
    None
):
    service = ExperimentService(
        experiment_manager=FakeExperimentManager(),
        recipe_manager=FakeRecipeManager(),
        recipe_embeddings_service=FakeEmbeddingsService(),
        recipe_hybrid_search_service=FakeHybridSearchService(),
        text_generation_fn=lambda _user_prompt, _system_prompt: "unused",
        stream_generation_fn=lambda _user_prompt, _system_prompt: iter(()),
    )

    attached, unresolved = service._resolve_attach_recipe_names(["Missing Recipe"])

    assert attached == []
    assert unresolved == ["Missing Recipe"]


def test_resolve_attach_recipe_names_forwards_viewer_to_exact_and_prefix_lookups() -> (
    None
):
    recipe_manager = FakeRecipeManager(
        recipes={
            "recipe-1": {
                "id": "recipe-1",
                "title": "Chicken Tikka Masala",
                "created_at": "2026-04-26T00:00:00+00:00",
            }
        }
    )
    embeddings_service = FakeEmbeddingsService()
    hybrid_search_service = FakeHybridSearchService()
    service = ExperimentService(
        experiment_manager=FakeExperimentManager(),
        recipe_manager=recipe_manager,
        recipe_embeddings_service=embeddings_service,
        recipe_hybrid_search_service=hybrid_search_service,
        text_generation_fn=lambda _user_prompt, _system_prompt: "unused",
        stream_generation_fn=lambda _user_prompt, _system_prompt: iter(()),
    )

    attached, unresolved = service._resolve_attach_recipe_names(
        ["Chicken Tikka"],
        viewer_user_id="11111111-1111-1111-1111-111111111111",
    )

    assert attached == [
        {
            "id": "recipe-1",
            "title": "Chicken Tikka Masala",
            "created_at": "2026-04-26T00:00:00+00:00",
        }
    ]
    assert unresolved == []
    assert recipe_manager.exact_calls == [
        {
            "title": "Chicken Tikka",
            "include_test_data": False,
            "viewer_user_id": "11111111-1111-1111-1111-111111111111",
        }
    ]
    assert recipe_manager.prefix_calls == [
        {
            "title_prefix": "Chicken Tikka",
            "include_test_data": False,
            "viewer_user_id": "11111111-1111-1111-1111-111111111111",
        }
    ]
    assert embeddings_service.calls == []
    assert hybrid_search_service.calls == []
