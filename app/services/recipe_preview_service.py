from __future__ import annotations

from typing import Optional

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
    """
    Build non-persistent recipe previews from URL content.
    """

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
        max_steps: int = 10,
        max_actions_per_step: int = 2,
    ) -> tuple[Optional[dict], Optional[str]]:
        """
        Scrape + clean + extract a recipe preview from a URL without saving to DB.
        """
        scraped_result, scrape_error = await self._scrape_recipe_text(
            start_url=start_url,
            target_instruction=target_instruction,
            max_steps=max_steps,
            max_actions_per_step=max_actions_per_step,
        )
        if scrape_error or not scraped_result:
            return None, scrape_error or "Failed to scrape recipe text from URL"

        raw_scraped_text = scraped_result["raw_scraped_text"]
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
            logger.error("Preview extraction raised an exception: %s", exc)

        preview = {
            "source_url": scraped_result["source_url"],
            "target_instruction": target_instruction,
            "raw_scraped_text": raw_scraped_text,
            "cleaned_text": cleaned_text,
            "recipe": recipe.model_dump() if recipe else None,
            "extraction_error": extraction_error,
            "evidence": scraped_result.get("evidence"),
            "confidence": scraped_result.get("confidence"),
            "trace_steps": scraped_result.get("trace_steps", 0),
        }
        return preview, None

    async def _scrape_recipe_text(
        self,
        start_url: str,
        target_instruction: str,
        max_steps: int,
        max_actions_per_step: int,
    ) -> tuple[Optional[dict], Optional[str]]:
        prompt = target_instruction.strip()
        if not prompt:
            return None, "target_instruction cannot be empty."

        response_payload, client_error = await anyio.to_thread.run_sync(
            lambda: self.auto_browse_client.run(
                start_url=start_url,
                target_prompt=prompt,
                max_steps=max_steps,
                max_actions_per_step=max_actions_per_step,
                extraction_schema=RECIPE_TEXT_SCHEMA,
            )
        )
        if client_error:
            return None, client_error

        if not response_payload:
            return (
                None,
                "URL scrape failed: auto-browse API returned an empty response.",
            )

        structured_data = response_payload.get("structured_data")
        if not isinstance(structured_data, dict):
            structured_data = None
        answer = response_payload.get("answer")
        if not isinstance(answer, str):
            answer = None

        raw_scraped_text = self._select_scraped_text(
            answer=answer,
            structured_data=structured_data,
        )
        if not raw_scraped_text:
            return None, "URL scrape succeeded but did not return recipe text."

        source_url = response_payload.get("source_url")
        if not isinstance(source_url, str) or not source_url.strip():
            source_url = start_url

        trace = response_payload.get("trace")
        trace_steps = len(trace) if isinstance(trace, list) else 0

        return {
            "raw_scraped_text": raw_scraped_text,
            "source_url": source_url,
            "evidence": response_payload.get("evidence"),
            "confidence": response_payload.get("confidence"),
            "trace_steps": trace_steps,
        }, None

    @staticmethod
    def _select_scraped_text(
        answer: Optional[str], structured_data: Optional[dict[str, str | None]]
    ) -> Optional[str]:
        if structured_data:
            preferred = structured_data.get("raw_recipe_text")
            if isinstance(preferred, str) and preferred.strip():
                return preferred.strip()
            for value in structured_data.values():
                if isinstance(value, str) and value.strip():
                    return value.strip()

        if isinstance(answer, str) and answer.strip():
            return answer.strip()

        return None
