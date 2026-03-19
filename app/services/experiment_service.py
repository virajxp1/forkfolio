from __future__ import annotations

from typing import Callable, Iterator

from app.core.prompts import EXPERIMENT_AGENT_SYSTEM_PROMPT
from app.services.data.managers.experiment_manager import ExperimentManager
from app.services.data.managers.recipe_manager import RecipeManager
from app.services.experiment_agent_graph import (
    DEFAULT_EXPERIMENT_FALLBACK,
    ExperimentAgentGraph,
)
from app.services.llm_generation_service import (
    make_llm_call_text_generation,
    stream_llm_call_text_generation,
)


class ExperimentThreadNotFoundError(Exception):
    """Raised when an experiment thread is missing."""


class ExperimentValidationError(ValueError):
    """Raised for invalid experiment payloads."""

    def __init__(self, message: str, missing_recipe_ids: list[str] | None = None):
        super().__init__(message)
        self.missing_recipe_ids = missing_recipe_ids or []


class ExperimentService:
    """
    Orchestrates experiment-thread lifecycle and assistant turns.

    This service intentionally keeps a single entrypoint for assistant responses
    so LangGraph can be slotted in without changing endpoint contracts.
    """

    def __init__(
        self,
        experiment_manager: ExperimentManager | None = None,
        recipe_manager: RecipeManager | None = None,
        text_generation_fn: Callable[[str, str], str] | None = None,
        stream_generation_fn: Callable[[str, str], Iterator[str]] | None = None,
        agent_graph: ExperimentAgentGraph | None = None,
    ):
        self.experiment_manager = experiment_manager or ExperimentManager()
        self.recipe_manager = recipe_manager or RecipeManager()
        self._text_generation_fn = text_generation_fn or make_llm_call_text_generation
        self._stream_generation_fn = (
            stream_generation_fn or stream_llm_call_text_generation
        )
        self._agent_graph = agent_graph or ExperimentAgentGraph(
            text_generation_fn=self._text_generation_fn
        )

    @staticmethod
    def _normalize_mode(mode: str | None) -> str:
        if mode is None:
            return "invent_new"
        normalized_mode = mode.strip().lower()
        allowed = {"invent_new", "modify_existing"}
        if normalized_mode not in allowed:
            raise ExperimentValidationError(
                "mode must be one of: invent_new, modify_existing"
            )
        return normalized_mode

    @staticmethod
    def _normalize_context_recipe_ids(recipe_ids: list[str]) -> list[str]:
        seen = set()
        normalized: list[str] = []
        for recipe_id in recipe_ids:
            recipe_id_text = str(recipe_id).strip()
            if not recipe_id_text or recipe_id_text in seen:
                continue
            seen.add(recipe_id_text)
            normalized.append(recipe_id_text)
        return normalized

    @staticmethod
    def _normalize_attach_recipe_names(recipe_names: list[str] | None) -> list[str]:
        seen = set()
        normalized: list[str] = []
        for recipe_name in recipe_names or []:
            name = str(recipe_name).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            normalized.append(name)
        return normalized

    @staticmethod
    def _normalize_attach_recipe_ids(recipe_ids: list[str] | None) -> list[str]:
        return ExperimentService._normalize_context_recipe_ids(recipe_ids or [])

    def _validate_recipe_ids(self, recipe_ids: list[str]) -> list[str]:
        normalized_ids = self._normalize_context_recipe_ids(recipe_ids)
        if not normalized_ids:
            return []

        missing_ids: list[str] = []
        for recipe_id in normalized_ids:
            if not self.recipe_manager.get_full_recipe(recipe_id):
                missing_ids.append(recipe_id)

        if missing_ids:
            raise ExperimentValidationError(
                "One or more context recipes were not found.",
                missing_recipe_ids=missing_ids,
            )
        return normalized_ids

    def create_thread(
        self,
        mode: str | None = None,
        title: str | None = None,
        context_recipe_ids: list[str] | None = None,
        is_test: bool = False,
    ) -> dict:
        normalized_mode = self._normalize_mode(mode)
        normalized_title = (
            title.strip() if isinstance(title, str) and title.strip() else None
        )
        validated_context_ids = self._validate_recipe_ids(context_recipe_ids or [])
        metadata: dict[str, object] = {"orchestration": "langgraph-ready"}
        if is_test:
            metadata["is_test"] = True

        return self.experiment_manager.create_thread(
            mode=normalized_mode,
            title=normalized_title,
            metadata=metadata,
            context_recipe_ids=validated_context_ids,
        )

    def list_threads(self, limit: int = 20, include_test: bool = False) -> list[dict]:
        return self.experiment_manager.list_threads(
            limit=limit,
            include_test=include_test,
        )

    def _resolve_attach_recipe_names(
        self, recipe_names: list[str]
    ) -> tuple[list[dict], list[str]]:
        attached_recipes: list[dict] = []
        unresolved_names: list[str] = []

        for recipe_name in self._normalize_attach_recipe_names(recipe_names):
            matches = self.recipe_manager.find_recipes_by_title_query(
                recipe_name, limit=1
            )
            if not matches:
                unresolved_names.append(recipe_name)
                continue
            attached_recipes.append(matches[0])
        return attached_recipes, unresolved_names

    def _resolve_attach_recipe_ids(
        self, recipe_ids: list[str]
    ) -> tuple[list[dict], list[str]]:
        attached_recipes: list[dict] = []
        unresolved_ids: list[str] = []

        for recipe_id in self._normalize_attach_recipe_ids(recipe_ids):
            recipe = self.recipe_manager.get_full_recipe(recipe_id)
            if not recipe:
                unresolved_ids.append(recipe_id)
                continue
            attached_recipes.append(
                {
                    "id": str(recipe.get("id") or recipe_id),
                    "title": recipe.get("title"),
                    "created_at": recipe.get("created_at"),
                }
            )
        return attached_recipes, unresolved_ids

    def _resolve_attach_recipes(
        self,
        attach_recipe_ids: list[str] | None = None,
        attach_recipe_names: list[str] | None = None,
    ) -> tuple[list[dict], list[str]]:
        if attach_recipe_ids:
            return self._resolve_attach_recipe_ids(attach_recipe_ids)
        return self._resolve_attach_recipe_names(attach_recipe_names or [])

    def get_thread(self, thread_id: str, message_limit: int = 100) -> dict:
        thread = self.experiment_manager.get_thread(
            thread_id=thread_id,
            message_limit=message_limit,
        )
        if not thread:
            raise ExperimentThreadNotFoundError("Experiment thread not found")
        return thread

    def _build_context_payload(self, context_recipe_ids: list[str]) -> list[dict]:
        context_payload: list[dict] = []
        for recipe_id in context_recipe_ids:
            recipe = self.recipe_manager.get_full_recipe(recipe_id)
            if not recipe:
                continue

            ingredients = recipe.get("ingredients") or []
            instructions = recipe.get("instructions") or []
            context_payload.append(
                {
                    "id": str(recipe.get("id")),
                    "title": recipe.get("title"),
                    "servings": recipe.get("servings"),
                    "total_time": recipe.get("total_time"),
                    "ingredients_preview": ingredients[:8],
                    "instructions_preview": instructions[:3],
                }
            )
        return context_payload

    @staticmethod
    def _build_history_payload(messages: list[dict], max_items: int = 12) -> list[dict]:
        history_items: list[dict] = []
        for message in messages[-max_items:]:
            history_items.append(
                {
                    "role": message.get("role"),
                    "content": message.get("content", ""),
                }
            )
        return history_items

    def _build_agent_plan(
        self,
        mode: str,
        user_message: str,
        context_recipe_ids: list[str],
        prior_messages: list[dict],
        stream_requested: bool,
    ) -> dict:
        context_payload = self._build_context_payload(context_recipe_ids)
        history_payload = self._build_history_payload(prior_messages)
        return self._agent_graph.execute(
            mode=mode,
            user_message=user_message,
            context_payload=context_payload,
            history_payload=history_payload,
            stream_requested=stream_requested,
        )

    @staticmethod
    def _chunk_text(text: str, chunk_words: int = 18) -> Iterator[str]:
        words = text.split()
        if not words:
            return
        for index in range(0, len(words), chunk_words):
            yield " ".join(words[index : index + chunk_words]) + " "

    def _build_attachment_event_text(
        self,
        attached_recipes: list[dict],
        unresolved_recipe_names: list[str],
    ) -> str | None:
        parts: list[str] = []
        if attached_recipes:
            titles = [
                recipe["title"] for recipe in attached_recipes if recipe.get("title")
            ]
            if titles:
                parts.append(f"Attached recipes: {', '.join(titles)}.")
        if unresolved_recipe_names:
            parts.append(
                f"Could not find recipes: {', '.join(unresolved_recipe_names)}."
            )
        if not parts:
            return None
        return " ".join(parts)

    def _run_agent_turn(
        self,
        mode: str,
        user_message: str,
        context_recipe_ids: list[str],
        prior_messages: list[dict],
    ) -> str:
        plan = self._build_agent_plan(
            mode=mode,
            user_message=user_message,
            context_recipe_ids=context_recipe_ids,
            prior_messages=prior_messages,
            stream_requested=False,
        )
        assistant_content = str(plan.get("assistant_content") or "").strip()
        if assistant_content:
            return assistant_content
        return DEFAULT_EXPERIMENT_FALLBACK

    def send_user_message(
        self,
        thread_id: str,
        content: str,
        context_recipe_ids: list[str] | None = None,
        attach_recipe_ids: list[str] | None = None,
        attach_recipe_names: list[str] | None = None,
    ) -> dict:
        normalized_content = content.strip()
        if not normalized_content:
            raise ExperimentValidationError("Message content cannot be empty.")

        thread = self.experiment_manager.get_thread(thread_id, message_limit=40)
        if not thread:
            raise ExperimentThreadNotFoundError("Experiment thread not found")

        if context_recipe_ids is not None:
            validated_context_ids = self._validate_recipe_ids(context_recipe_ids)
            self.experiment_manager.set_context_recipe_ids(
                thread_id=thread_id,
                context_recipe_ids=validated_context_ids,
            )
            thread["context_recipe_ids"] = validated_context_ids

        attached_recipes, unresolved_recipe_names = self._resolve_attach_recipes(
            attach_recipe_ids=attach_recipe_ids,
            attach_recipe_names=attach_recipe_names,
        )
        attachment_message = None
        if attached_recipes:
            existing_context_ids = thread.get("context_recipe_ids") or []
            combined_context_ids = self._normalize_context_recipe_ids(
                [
                    *existing_context_ids,
                    *[attached_recipe["id"] for attached_recipe in attached_recipes],
                ]
            )
            self.experiment_manager.set_context_recipe_ids(
                thread_id=thread_id,
                context_recipe_ids=combined_context_ids,
            )
            thread["context_recipe_ids"] = combined_context_ids

        attachment_event_text = self._build_attachment_event_text(
            attached_recipes=attached_recipes,
            unresolved_recipe_names=unresolved_recipe_names,
        )
        if attachment_event_text:
            attachment_message = self.experiment_manager.create_message(
                thread_id=thread_id,
                role="system",
                content=attachment_event_text,
            )

        user_message = self.experiment_manager.create_message(
            thread_id=thread_id,
            role="user",
            content=normalized_content,
        )
        if not user_message:
            raise ExperimentThreadNotFoundError("Experiment thread not found")

        self.experiment_manager.set_thread_title_if_empty(
            thread_id=thread_id,
            title=normalized_content[:80],
        )

        thread_messages = self.experiment_manager.list_messages(
            thread_id=thread_id, limit=40
        )
        thread_context_recipe_ids = self.experiment_manager.get_context_recipe_ids(
            thread_id
        )
        assistant_content = self._run_agent_turn(
            mode=thread["mode"],
            user_message=normalized_content,
            context_recipe_ids=thread_context_recipe_ids,
            prior_messages=thread_messages,
        )

        assistant_message = self.experiment_manager.create_message(
            thread_id=thread_id,
            role="assistant",
            content=assistant_content,
        )
        if not assistant_message:
            raise ExperimentThreadNotFoundError("Experiment thread not found")

        updated_thread = self.get_thread(thread_id=thread_id, message_limit=120)
        return {
            "thread": updated_thread,
            "user_message": user_message,
            "assistant_message": assistant_message,
            "attached_recipes": attached_recipes,
            "unresolved_recipe_names": unresolved_recipe_names,
            "attachment_message": attachment_message,
        }

    def stream_user_message(
        self,
        thread_id: str,
        content: str,
        context_recipe_ids: list[str] | None = None,
        attach_recipe_ids: list[str] | None = None,
        attach_recipe_names: list[str] | None = None,
    ) -> Iterator[dict]:
        normalized_content = content.strip()
        if not normalized_content:
            raise ExperimentValidationError("Message content cannot be empty.")

        thread = self.experiment_manager.get_thread(thread_id, message_limit=40)
        if not thread:
            raise ExperimentThreadNotFoundError("Experiment thread not found")

        if context_recipe_ids is not None:
            validated_context_ids = self._validate_recipe_ids(context_recipe_ids)
            self.experiment_manager.set_context_recipe_ids(
                thread_id=thread_id,
                context_recipe_ids=validated_context_ids,
            )
            thread["context_recipe_ids"] = validated_context_ids

        attached_recipes, unresolved_recipe_names = self._resolve_attach_recipes(
            attach_recipe_ids=attach_recipe_ids,
            attach_recipe_names=attach_recipe_names,
        )
        attachment_message = None
        if attached_recipes:
            existing_context_ids = thread.get("context_recipe_ids") or []
            combined_context_ids = self._normalize_context_recipe_ids(
                [
                    *existing_context_ids,
                    *[attached_recipe["id"] for attached_recipe in attached_recipes],
                ]
            )
            self.experiment_manager.set_context_recipe_ids(
                thread_id=thread_id,
                context_recipe_ids=combined_context_ids,
            )
            thread["context_recipe_ids"] = combined_context_ids

        attachment_event_text = self._build_attachment_event_text(
            attached_recipes=attached_recipes,
            unresolved_recipe_names=unresolved_recipe_names,
        )
        if attachment_event_text:
            attachment_message = self.experiment_manager.create_message(
                thread_id=thread_id,
                role="system",
                content=attachment_event_text,
            )
            if attachment_message:
                yield {
                    "event": "attachment",
                    "data": {
                        "attachment_message": attachment_message,
                        "attached_recipes": attached_recipes,
                        "unresolved_recipe_names": unresolved_recipe_names,
                    },
                }

        user_message = self.experiment_manager.create_message(
            thread_id=thread_id,
            role="user",
            content=normalized_content,
        )
        if not user_message:
            raise ExperimentThreadNotFoundError("Experiment thread not found")

        self.experiment_manager.set_thread_title_if_empty(
            thread_id=thread_id,
            title=normalized_content[:80],
        )

        yield {"event": "status", "data": {"step": "drafting"}}

        thread_messages = self.experiment_manager.list_messages(
            thread_id=thread_id, limit=40
        )
        thread_context_recipe_ids = self.experiment_manager.get_context_recipe_ids(
            thread_id
        )
        plan = self._build_agent_plan(
            mode=thread["mode"],
            user_message=normalized_content,
            context_recipe_ids=thread_context_recipe_ids,
            prior_messages=thread_messages,
            stream_requested=True,
        )

        assistant_parts: list[str] = []
        if plan.get("blocked"):
            blocked_text = str(plan.get("assistant_content") or "").strip()
            if not blocked_text:
                blocked_text = DEFAULT_EXPERIMENT_FALLBACK
            for blocked_chunk in self._chunk_text(blocked_text):
                assistant_parts.append(blocked_chunk)
                yield {"event": "delta", "data": {"text": blocked_chunk}}
        else:
            user_prompt = str(plan.get("user_prompt") or "").strip()
            if not user_prompt:
                for fallback_chunk in self._chunk_text(DEFAULT_EXPERIMENT_FALLBACK):
                    assistant_parts.append(fallback_chunk)
                    yield {"event": "delta", "data": {"text": fallback_chunk}}
            else:
                try:
                    for chunk in self._stream_generation_fn(
                        user_prompt,
                        EXPERIMENT_AGENT_SYSTEM_PROMPT,
                    ):
                        text_chunk = chunk or ""
                        if not text_chunk.strip():
                            continue
                        assistant_parts.append(text_chunk)
                        yield {"event": "delta", "data": {"text": text_chunk}}
                except Exception:
                    fallback = self._run_agent_turn(
                        mode=thread["mode"],
                        user_message=normalized_content,
                        context_recipe_ids=thread_context_recipe_ids,
                        prior_messages=thread_messages,
                    )
                    for fallback_chunk in self._chunk_text(fallback):
                        assistant_parts.append(fallback_chunk)
                        yield {"event": "delta", "data": {"text": fallback_chunk}}

        assistant_content = "".join(assistant_parts).strip()
        if not assistant_content:
            assistant_content = DEFAULT_EXPERIMENT_FALLBACK
            yield {"event": "delta", "data": {"text": assistant_content}}

        assistant_message = self.experiment_manager.create_message(
            thread_id=thread_id,
            role="assistant",
            content=assistant_content,
        )
        if not assistant_message:
            raise ExperimentThreadNotFoundError("Experiment thread not found")

        updated_thread = self.get_thread(thread_id=thread_id, message_limit=120)
        yield {
            "event": "final",
            "data": {
                "thread_id": thread_id,
                "thread": updated_thread,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "attachment_message": attachment_message,
                "attached_recipes": attached_recipes,
                "unresolved_recipe_names": unresolved_recipe_names,
            },
        }
