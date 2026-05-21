from __future__ import annotations

import json
import re
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.api.schemas import Recipe
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

SCRAPEGRAPH_RECIPE_PROMPT = """
Extract exactly one cooking recipe from this webpage.

Return:
- title
- ingredients as a list of ingredient lines
- instructions as an ordered list of cooking steps
- servings if explicitly present, otherwise an empty string
- total_time if explicitly present, otherwise an empty string

Rules:
- Do not invent missing data.
- Ignore ads, comments, navigation, author bio, equipment lists, nutrition blocks,
  substitutions, FAQ sections, and related recipes unless the information is part of
  the actual recipe.
- Keep ingredient and instruction text concise and human-readable.
""".strip()

LIST_ITEM_PREFIX_RE = re.compile(r"^\s*(?:[-*]|\d+[.)])\s*")


class ScrapeGraphRecipeSchema(BaseModel):
    title: str = Field(description="Recipe title shown on the page.")
    ingredients: list[str] = Field(
        default_factory=list,
        description="Ingredient lines only, one ingredient per item.",
    )
    instructions: list[str] = Field(
        default_factory=list,
        description="Ordered cooking steps only, one instruction per item.",
    )
    servings: str = Field(
        default="",
        description="Recipe servings or yield if explicitly present, otherwise empty string.",
    )
    total_time: str = Field(
        default="",
        description="Recipe total time if explicitly present, otherwise empty string.",
    )


class RecipeWebsiteExtractorImpl:
    """ScrapeGraphAI SDK-backed extractor used for webpage imports."""

    def __init__(
        self,
        model_name: str | None = None,
        openrouter_api_key: str | None = None,
    ) -> None:
        self.model_name = (model_name or settings.LLM_MODEL_NAME).strip()
        self.openrouter_api_key = (
            openrouter_api_key or settings.OPEN_ROUTER_API_KEY
        ).strip()

    def extract_recipe_from_html(
        self,
        raw_html: str,
    ) -> tuple[Optional[Recipe], Optional[str], dict[str, int]]:
        diagnostics: dict[str, int] = {"scrapegraphai_attempted": 1}

        if not self.model_name:
            return (
                None,
                "LLM model name is not set for ScrapeGraphAI extraction",
                diagnostics,
            )
        if not self.openrouter_api_key:
            return (
                None,
                "OPEN_ROUTER_API_KEY is not set for ScrapeGraphAI extraction",
                diagnostics,
            )

        try:
            raw_result = self._run_sdk_graph(raw_html)
        except Exception as exc:
            logger.warning(
                "ScrapeGraphAI SDK extraction failed. error=%s",
                exc,
            )
            return None, f"ScrapeGraphAI extraction failed: {exc!s}", diagnostics

        normalized_result = self._coerce_result(raw_result)
        if not normalized_result:
            return None, "ScrapeGraphAI returned an empty response", diagnostics

        diagnostics["scrapegraphai_result_chars"] = len(
            json.dumps(normalized_result, ensure_ascii=True)
        )
        recipe = self._normalize_recipe(normalized_result)
        if not recipe:
            return (
                None,
                "ScrapeGraphAI returned an incomplete recipe payload",
                diagnostics,
            )

        diagnostics["scrapegraphai_success"] = 1
        return recipe, None, diagnostics

    @staticmethod
    def _coerce_result(raw_result: Any) -> dict[str, Any]:
        if raw_result is None:
            return {}

        if isinstance(raw_result, dict):
            if isinstance(raw_result.get("result"), dict):
                return raw_result["result"]
            return raw_result

        if isinstance(raw_result, BaseModel):
            dumped = raw_result.model_dump()
            if isinstance(dumped.get("result"), dict):
                return dumped["result"]
            return dumped

        return {}

    def _run_sdk_graph(self, raw_html: str) -> Any:
        from langchain_openai import ChatOpenAI
        from scrapegraphai.graphs import SmartScraperGraph

        llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.openrouter_api_key,
            base_url="https://openrouter.ai/api/v1",
            temperature=0,
            max_tokens=settings.LLM_STRUCTURED_MAX_TOKENS,
            max_retries=settings.LLM_MAX_RETRIES,
            timeout=settings.REQUEST_TIMEOUT_SECONDS,
        )

        graph = SmartScraperGraph(
            prompt=SCRAPEGRAPH_RECIPE_PROMPT,
            source=raw_html,
            config={
                "llm": {
                    "model_instance": llm,
                    "model_tokens": 8192,
                },
                "verbose": False,
                "headless": True,
                "timeout": max(1, int(settings.REQUEST_TIMEOUT_SECONDS)),
            },
            schema=ScrapeGraphRecipeSchema,
        )

        return graph.run()

    def _normalize_recipe(self, payload: dict[str, Any]) -> Optional[Recipe]:
        title = self._normalize_scalar(payload.get("title"))
        ingredients = self._normalize_list(payload.get("ingredients"))
        instructions = self._normalize_list(payload.get("instructions"))
        servings = self._normalize_scalar(payload.get("servings"))
        total_time = self._normalize_scalar(payload.get("total_time"))

        if not title or not ingredients or not instructions:
            return None

        return Recipe(
            title=title,
            ingredients=ingredients,
            instructions=instructions,
            servings=servings,
            total_time=total_time,
        )

    @staticmethod
    def _normalize_scalar(value: Any) -> str:
        if value is None:
            return ""
        return " ".join(str(value).split())

    @staticmethod
    def _normalize_list(value: Any) -> list[str]:
        if isinstance(value, str):
            raw_items = value.splitlines()
        elif isinstance(value, list):
            raw_items = value
        else:
            return []

        normalized: list[str] = []
        for item in raw_items:
            if isinstance(item, dict):
                candidate = (
                    item.get("text") or item.get("value") or item.get("content") or ""
                )
            else:
                candidate = str(item)

            cleaned = LIST_ITEM_PREFIX_RE.sub("", candidate).strip()
            if cleaned:
                normalized.append(cleaned)

        return normalized
