from __future__ import annotations

import ipaddress
import socket
from typing import Optional
from urllib.parse import urlparse

import anyio

from app.core.config import settings
from app.core.logging import get_logger
from app.services.recipe_extractor_impl import RecipeExtractorImpl
from app.services.recipe_input_cleanup_impl import RecipeInputCleanupServiceImpl

logger = get_logger(__name__)

RECIPE_TEXT_SCHEMA = {
    "raw_recipe_text": (
        "Full recipe text from the page, including title, ingredients, instructions, "
        "servings, and total time when available."
    )
}

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata",
    "metadata.google.internal",
}


class RecipePreviewService:
    """
    Build non-persistent recipe previews from URL content.
    """

    def __init__(
        self,
        cleanup_service: RecipeInputCleanupServiceImpl | None = None,
        extractor_service: RecipeExtractorImpl | None = None,
    ):
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
        validation_error = self._validate_external_url(start_url)
        if validation_error:
            return None, validation_error

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
        try:
            from auto_browse import OpenRouterClient, run_agent
        except ImportError:
            return (
                None,
                "auto-browse is not installed. Install and configure it before using URL preview.",
            )

        if not settings.OPEN_ROUTER_API_KEY:
            return None, "OPEN_ROUTER_API_KEY is not configured."
        if not settings.LLM_MODEL_NAME:
            return None, "LLM model name is not configured."

        # Keep user intent while biasing extraction toward complete recipe text.
        prompt = (
            f"{target_instruction.strip()}\n\n"
            "Return the full recipe text from the page. Do not summarize."
        )
        client = OpenRouterClient(
            api_key=settings.OPEN_ROUTER_API_KEY,
            model_name=settings.LLM_MODEL_NAME,
        )
        result = await run_agent(
            client,
            start_url=start_url,
            target_prompt=prompt,
            max_steps=max_steps,
            max_actions_per_step=max_actions_per_step,
            extraction_schema=RECIPE_TEXT_SCHEMA,
            headless=True,
        )

        if result.error:
            return None, f"URL scrape failed: {result.error}"

        raw_scraped_text = self._select_scraped_text(
            result.answer, result.structured_data
        )
        if not raw_scraped_text:
            return None, "URL scrape succeeded but did not return recipe text."

        return {
            "raw_scraped_text": raw_scraped_text,
            "source_url": result.source_url or start_url,
            "evidence": result.evidence,
            "confidence": result.confidence,
            "trace_steps": len(getattr(result, "trace", None) or []),
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

    @staticmethod
    def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        # Allow only globally routable targets to reduce SSRF attack surface.
        return not ip.is_global

    @classmethod
    def _validate_external_url(cls, start_url: str) -> Optional[str]:
        parsed = urlparse(start_url)
        if parsed.scheme not in {"http", "https"}:
            return "start_url must use http or https."

        hostname = (parsed.hostname or "").strip().lower().rstrip(".")
        if not hostname:
            return "start_url must include a valid hostname."
        if hostname in BLOCKED_HOSTNAMES:
            return "start_url host is not allowed."

        try:
            literal_ip = ipaddress.ip_address(hostname)
        except ValueError:
            literal_ip = None
        if literal_ip and cls._is_blocked_ip(literal_ip):
            return "start_url resolves to a blocked address."

        try:
            resolved = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        except socket.gaierror:
            return "start_url hostname could not be resolved."
        except Exception as exc:
            logger.error("Failed to resolve start_url hostname '%s': %s", hostname, exc)
            return "Failed to validate start_url hostname."

        found_ip = False
        for info in resolved:
            address = info[4][0]
            normalized = address.split("%", 1)[0]
            try:
                ip = ipaddress.ip_address(normalized)
            except ValueError:
                continue
            found_ip = True
            if cls._is_blocked_ip(ip):
                return "start_url resolves to a blocked address."

        if not found_ip:
            return "start_url hostname did not resolve to an IP address."
        return None
