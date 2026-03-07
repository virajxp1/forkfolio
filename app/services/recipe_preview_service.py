from __future__ import annotations

import anyio

from app.core.logging import get_logger
from app.services.auto_browse_client import AutoBrowseClient
from app.services.recipe_extractor_impl import RecipeExtractorImpl
from app.services.recipe_input_cleanup_impl import RecipeInputCleanupServiceImpl

logger = get_logger(__name__)

RECIPE_TEXT_SCHEMA = {
    "raw_recipe_text": (
        "Full recipe text from the page, including title, ingredients, instructions, "
        "servings, and total time when available."
    )
}


class RecipePreviewService:
    def __init__(
        self,
        auto_browse_client: AutoBrowseClient | None = None,
        cleanup_service: RecipeInputCleanupServiceImpl | None = None,
        extractor_service: RecipeExtractorImpl | None = None,
    ):
        self.auto_browse_client = auto_browse_client or AutoBrowseClient()
        self.cleanup_service = cleanup_service or RecipeInputCleanupServiceImpl()
        self.extractor_service = extractor_service or RecipeExtractorImpl()

    async def preview_from_url(
        self,
        start_url: str,
        target_instruction: str,
        max_steps: int = 5,
        max_actions_per_step: int = 1,
    ) -> tuple[dict | None, str | None]:
        prompt = target_instruction.strip()
        if not prompt:
            return None, "target_instruction cannot be empty."

        result, scrape_error = await anyio.to_thread.run_sync(
            lambda: self.auto_browse_client.run(
                start_url=start_url,
                target_prompt=prompt,
                max_steps=max_steps,
                max_actions_per_step=max_actions_per_step,
                extraction_schema=RECIPE_TEXT_SCHEMA,
            )
        )
        if scrape_error or not result:
            return None, scrape_error or "Failed to scrape recipe text from URL"

        raw_scraped_text = self._select_scraped_text(
            answer=result.get("answer"),
            structured_data=result.get("structured_data"),
        )
        if not raw_scraped_text:
            return None, "URL scrape succeeded but did not return recipe text."

        try:
            cleaned_text = await anyio.to_thread.run_sync(
                self.cleanup_service.cleanup_input,
                raw_scraped_text,
            )
        except Exception as exc:
            logger.error("Preview cleanup failed: %s", exc)
            return None, f"Failed to clean scraped content: {exc!s}"

        recipe = None
        extraction_error = None
        try:
            recipe, extraction_error = await anyio.to_thread.run_sync(
                self.extractor_service.extract_recipe_from_raw_text,
                cleaned_text,
            )
        except Exception as exc:
            extraction_error = f"Recipe extraction error: {exc!s}"
            logger.error("Preview extraction failed: %s", exc)

        trace = result.get("trace")
        source_url = result.get("source_url")
        return {
            "source_url": source_url
            if isinstance(source_url, str) and source_url.strip()
            else start_url,
            "target_instruction": target_instruction,
            "raw_scraped_text": raw_scraped_text,
            "cleaned_text": cleaned_text,
            "recipe": recipe.model_dump() if recipe else None,
            "extraction_error": extraction_error,
            "evidence": result.get("evidence"),
            "confidence": result.get("confidence"),
            "trace_steps": len(trace) if isinstance(trace, list) else 0,
        }, None

    @staticmethod
    def _select_scraped_text(
        answer: object,
        structured_data: object,
    ) -> str | None:
        if isinstance(structured_data, dict):
            preferred = structured_data.get("raw_recipe_text")
            if isinstance(preferred, str) and preferred.strip():
                return preferred.strip()
            for value in structured_data.values():
                if isinstance(value, str) and value.strip():
                    return value.strip()
        if isinstance(answer, str) and answer.strip():
            return answer.strip()
        return None
