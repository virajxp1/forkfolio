from __future__ import annotations

import json
import re
from typing import Callable, Literal, TypedDict

from app.core.prompts import (
    EXPERIMENT_AGENT_SCOPE_REFUSAL,
    EXPERIMENT_AGENT_SYSTEM_PROMPT,
)

try:
    from langgraph.graph import END, START, StateGraph
except Exception:  # pragma: no cover - exercised only when langgraph is unavailable
    END = "__end__"
    START = "__start__"
    StateGraph = None  # type: ignore[assignment]

DEFAULT_EXPERIMENT_FALLBACK = (
    "I can help iterate this recipe. Share dietary goals, flavor direction, "
    "and any must-use ingredients, and I will propose a concrete draft."
)

_PROMPT_INJECTION_PATTERNS = (
    "ignore previous instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "reveal system prompt",
    "system prompt",
    "show system prompt",
    "developer message",
    "jailbreak",
    "you are now",
    "act as",
    "print the hidden prompt",
    "bypass safety",
)

_FOOD_HINT_TOKENS = (
    "recipe",
    "cook",
    "cooking",
    "dish",
    "meal",
    "ingredient",
    "ingredients",
    "bake",
    "boil",
    "saute",
    "simmer",
    "grill",
    "fry",
    "vegan",
    "vegetarian",
    "dairy",
    "gluten",
    "allergy",
    "protein",
    "chicken",
    "beef",
    "tofu",
    "paneer",
    "curry",
    "masala",
    "soup",
    "salad",
    "marinade",
    "sauce",
    "dessert",
    "breakfast",
    "lunch",
    "dinner",
)

_OFF_TOPIC_HINT_TOKENS = (
    "python",
    "javascript",
    "java",
    "typescript",
    "code",
    "algorithm",
    "linked list",
    "leetcode",
    "binary tree",
    "sql",
    "regex",
    "unit test",
    "essay",
    "resume",
    "cover letter",
    "contract",
    "lawsuit",
    "diagnosis",
    "prescription",
)

_CODE_REQUEST_PATTERN = re.compile(
    r"\b(write|implement|generate|debug|optimize|refactor)\b.{0,50}\b("
    r"code|python|javascript|typescript|java|linked list|binary tree|sql|regex"
    r")\b",
    flags=re.IGNORECASE | re.DOTALL,
)


class ExperimentAgentState(TypedDict, total=False):
    mode: str
    user_message: str
    context_payload: list[dict]
    history_payload: list[dict]
    stream_requested: bool
    scope: Literal["in_scope", "blocked"]
    block_reason: str | None
    user_prompt: str
    assistant_content: str


class ExperimentAgentPlan(TypedDict):
    blocked: bool
    block_reason: str | None
    user_prompt: str | None
    assistant_content: str | None


def _normalize_text(text: str) -> str:
    return " ".join(str(text or "").strip().lower().split())


def _contains_any_token(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token in text for token in tokens)


def _history_has_recipe_context(history_payload: list[dict]) -> bool:
    for item in history_payload[-8:]:
        text = _normalize_text(str(item.get("content") or ""))
        if _contains_any_token(text, _FOOD_HINT_TOKENS):
            return True
    return False


def _is_out_of_scope(
    user_message: str,
    context_payload: list[dict],
    history_payload: list[dict],
) -> tuple[bool, str | None]:
    normalized = _normalize_text(user_message)
    if not normalized:
        return False, None

    has_food_signal = _contains_any_token(normalized, _FOOD_HINT_TOKENS)
    has_injection_signal = _contains_any_token(normalized, _PROMPT_INJECTION_PATTERNS)
    has_code_signal = bool(_CODE_REQUEST_PATTERN.search(normalized))
    has_off_topic_signal = _contains_any_token(normalized, _OFF_TOPIC_HINT_TOKENS)
    has_recipe_context = bool(context_payload) or _history_has_recipe_context(
        history_payload
    )

    if has_injection_signal:
        return True, "prompt_injection"
    if has_code_signal:
        return True, "non_recipe_code_request"
    if has_off_topic_signal and not has_food_signal and not has_recipe_context:
        return True, "out_of_scope"
    return False, None


class ExperimentAgentGraph:
    def __init__(self, text_generation_fn: Callable[[str, str], str]) -> None:
        self._text_generation_fn = text_generation_fn
        self._compiled_graph = self._build_graph()

    @staticmethod
    def _build_user_prompt(state: ExperimentAgentState) -> str:
        return json.dumps(
            {
                "mode": state["mode"],
                "user_request": state["user_message"],
                "thread_context_recipes": state["context_payload"],
                "recent_history": state["history_payload"],
            },
            ensure_ascii=True,
            sort_keys=True,
        )

    def _guard_scope(self, state: ExperimentAgentState) -> ExperimentAgentState:
        blocked, reason = _is_out_of_scope(
            user_message=state["user_message"],
            context_payload=state["context_payload"],
            history_payload=state["history_payload"],
        )
        if blocked:
            return {
                "scope": "blocked",
                "block_reason": reason,
                "assistant_content": EXPERIMENT_AGENT_SCOPE_REFUSAL,
            }
        return {"scope": "in_scope", "block_reason": None}

    def _build_prompt(self, state: ExperimentAgentState) -> ExperimentAgentState:
        return {"user_prompt": self._build_user_prompt(state)}

    def _generate_response(self, state: ExperimentAgentState) -> ExperimentAgentState:
        user_prompt = state.get("user_prompt", "")
        if not user_prompt:
            return {"assistant_content": DEFAULT_EXPERIMENT_FALLBACK}

        try:
            generated = self._text_generation_fn(
                user_prompt,
                EXPERIMENT_AGENT_SYSTEM_PROMPT,
            )
        except Exception:
            return {"assistant_content": DEFAULT_EXPERIMENT_FALLBACK}

        normalized = (generated or "").strip()
        if not normalized:
            return {"assistant_content": DEFAULT_EXPERIMENT_FALLBACK}
        return {"assistant_content": normalized}

    @staticmethod
    def _route_after_guard(
        state: ExperimentAgentState,
    ) -> Literal["blocked", "build_prompt"]:
        if state.get("scope") == "blocked":
            return "blocked"
        return "build_prompt"

    @staticmethod
    def _route_after_prompt(
        state: ExperimentAgentState,
    ) -> Literal["stream", "generate"]:
        if state.get("stream_requested"):
            return "stream"
        return "generate"

    def _build_graph(self):
        if StateGraph is None:
            return None

        graph = StateGraph(ExperimentAgentState)
        graph.add_node("guard_scope", self._guard_scope)
        graph.add_node("build_prompt", self._build_prompt)
        graph.add_node("generate_response", self._generate_response)

        graph.add_edge(START, "guard_scope")
        graph.add_conditional_edges(
            "guard_scope",
            self._route_after_guard,
            {
                "blocked": END,
                "build_prompt": "build_prompt",
            },
        )
        graph.add_conditional_edges(
            "build_prompt",
            self._route_after_prompt,
            {
                "stream": END,
                "generate": "generate_response",
            },
        )
        graph.add_edge("generate_response", END)
        return graph.compile()

    def _run_fallback(self, state: ExperimentAgentState) -> ExperimentAgentState:
        result_state: ExperimentAgentState = dict(state)
        result_state.update(self._guard_scope(result_state))
        if result_state.get("scope") == "blocked":
            return result_state

        result_state.update(self._build_prompt(result_state))
        if result_state.get("stream_requested"):
            return result_state

        result_state.update(self._generate_response(result_state))
        return result_state

    def execute(
        self,
        *,
        mode: str,
        user_message: str,
        context_payload: list[dict],
        history_payload: list[dict],
        stream_requested: bool,
    ) -> ExperimentAgentPlan:
        initial_state: ExperimentAgentState = {
            "mode": mode,
            "user_message": user_message,
            "context_payload": context_payload,
            "history_payload": history_payload,
            "stream_requested": stream_requested,
        }

        if self._compiled_graph is None:
            result_state = self._run_fallback(initial_state)
        else:
            result_state = self._compiled_graph.invoke(initial_state)

        assistant_content = str(result_state.get("assistant_content") or "").strip()
        user_prompt = str(result_state.get("user_prompt") or "").strip()
        blocked = result_state.get("scope") == "blocked"
        return {
            "blocked": blocked,
            "block_reason": result_state.get("block_reason"),
            "assistant_content": assistant_content or None,
            "user_prompt": user_prompt or None,
        }
