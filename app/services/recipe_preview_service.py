from __future__ import annotations

import contextvars
import importlib
import ipaddress
import socket
import threading
from dataclasses import dataclass
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


@dataclass(frozen=True)
class _BrowserRequestPolicy:
    start_host: str
    service: "RecipePreviewService"


_AUTO_BROWSE_PATCH_LOCK = threading.Lock()
_AUTO_BROWSE_GUARD_INSTALLED = False
_AUTO_BROWSE_POLICY: contextvars.ContextVar[_BrowserRequestPolicy | None] = (
    contextvars.ContextVar(
        "recipe_preview_auto_browse_policy",
        default=None,
    )
)


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
        validation_error = await self._validate_external_url_async(start_url)
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

        start_host = self._normalized_hostname(start_url)
        if not start_host:
            return None, "start_url must include a valid hostname."

        guard_install_error = self._ensure_auto_browse_route_guard()
        if guard_install_error:
            return None, guard_install_error

        # Keep user intent while biasing extraction toward complete recipe text.
        prompt = (
            f"{target_instruction.strip()}\n\n"
            "Return the full recipe text from the page. Do not summarize. "
            f"Do not navigate away from host '{start_host}'."
        )
        try:
            client = OpenRouterClient(
                api_key=settings.OPEN_ROUTER_API_KEY,
                model_name=settings.LLM_MODEL_NAME,
            )
        except Exception as exc:
            logger.error("Failed to initialize preview scrape client: %s", exc)
            return None, "Failed to initialize URL scraping client."

        policy_token = _AUTO_BROWSE_POLICY.set(
            _BrowserRequestPolicy(
                start_host=start_host,
                service=self,
            )
        )
        try:
            result = await run_agent(
                client,
                start_url=start_url,
                target_prompt=prompt,
                max_steps=max_steps,
                max_actions_per_step=max_actions_per_step,
                extraction_schema=RECIPE_TEXT_SCHEMA,
                headless=True,
            )
        except Exception as exc:
            logger.error("URL scrape agent failed: %s", exc)
            return None, f"URL scrape failed: {exc!s}"
        finally:
            _AUTO_BROWSE_POLICY.reset(policy_token)

        if result.error:
            return None, f"URL scrape failed: {result.error}"

        source_url = result.source_url or start_url
        trace_urls = [self._extract_trace_url(step) for step in (result.trace or [])]
        trace_urls = [url for url in trace_urls if url]
        url_scope_error = await self._validate_navigation_scope(
            start_host=start_host,
            source_url=source_url,
            trace_urls=trace_urls,
        )
        if url_scope_error:
            return None, url_scope_error

        raw_scraped_text = self._select_scraped_text(
            result.answer, result.structured_data
        )
        if not raw_scraped_text:
            return None, "URL scrape succeeded but did not return recipe text."

        return {
            "raw_scraped_text": raw_scraped_text,
            "source_url": source_url,
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

    @staticmethod
    def _normalized_hostname(url: str) -> str:
        parsed = urlparse(url)
        return (parsed.hostname or "").strip().lower().rstrip(".")

    @staticmethod
    def _extract_trace_url(step) -> str:
        if isinstance(step, dict):
            url = step.get("url")
        else:
            url = getattr(step, "url", None)
        if not isinstance(url, str):
            return ""
        return url.strip()

    async def _validate_external_url_async(self, url: str) -> Optional[str]:
        return await anyio.to_thread.run_sync(
            self._validate_external_url,
            url,
        )

    async def _validate_navigation_request_url(
        self,
        request_url: str,
        start_host: str,
        navigation_request: bool,
    ) -> Optional[str]:
        normalized_url = (request_url or "").strip()
        if not normalized_url:
            return "request URL is empty."

        parsed = urlparse(normalized_url)
        if parsed.scheme not in {"http", "https"}:
            if navigation_request:
                return "navigation request must use http or https."
            return None

        validation_error = await self._validate_external_url_async(normalized_url)
        if validation_error:
            return validation_error

        if navigation_request:
            current_host = self._normalized_hostname(normalized_url)
            if current_host != start_host:
                return (
                    "Navigation to a different host is not allowed "
                    f"('{start_host}' -> '{current_host}')."
                )

        return None

    def _ensure_auto_browse_route_guard(self) -> Optional[str]:
        global _AUTO_BROWSE_GUARD_INSTALLED

        if _AUTO_BROWSE_GUARD_INSTALLED:
            return None

        try:
            auto_browse_run_module = importlib.import_module("agent.run")
            auto_browse_browser_module = importlib.import_module("agent.browser")
        except Exception as exc:
            logger.error("Failed to import auto-browse internals for guard: %s", exc)
            return (
                "Installed auto-browse version does not support request-level URL "
                "guards. Upgrade auto-browse to continue."
            )

        with _AUTO_BROWSE_PATCH_LOCK:
            if _AUTO_BROWSE_GUARD_INSTALLED:
                return None

            original_run_browser = getattr(auto_browse_run_module, "run_browser", None)
            if not callable(original_run_browser):
                return "auto-browse run_browser hook unavailable."

            normalize_start_url = getattr(
                auto_browse_browser_module,
                "_normalize_start_url",
                None,
            )
            async_playwright_factory = getattr(
                auto_browse_browser_module,
                "async_playwright",
                None,
            )
            if async_playwright_factory is None:
                return "auto-browse browser runtime is unavailable."

            async def guarded_run_browser(start_url: str, *, headless: bool = True):
                policy = _AUTO_BROWSE_POLICY.get()
                if policy is None:
                    return await original_run_browser(start_url, headless=headless)

                normalized_start_url = start_url
                if callable(normalize_start_url):
                    normalized_start_url = normalize_start_url(start_url)

                pw = await async_playwright_factory().start()
                browser = await pw.chromium.launch(
                    headless=headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                    ],
                )
                context = await browser.new_context(
                    user_agent=(
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/122.0.0.0 Safari/537.36"
                    ),
                    locale="en-US",
                    timezone_id="America/New_York",
                    viewport={"width": 1366, "height": 768},
                )
                await context.set_extra_http_headers(
                    {"Accept-Language": "en-US,en;q=0.9"}
                )

                request_validation_cache: dict[tuple[str, bool], Optional[str]] = {}

                async def _route_handler(route, request) -> None:
                    request_url = (getattr(request, "url", "") or "").strip()
                    request_host = policy.service._normalized_hostname(request_url)
                    navigation_request = bool(request.is_navigation_request())
                    cache_key = (request_host, navigation_request)

                    if cache_key in request_validation_cache:
                        validation_error = request_validation_cache[cache_key]
                    else:
                        validation_error = (
                            await policy.service._validate_navigation_request_url(
                                request_url=request_url,
                                start_host=policy.start_host,
                                navigation_request=navigation_request,
                            )
                        )
                        request_validation_cache[cache_key] = validation_error

                    if validation_error:
                        logger.warning(
                            "Blocked browser request during recipe preview: url=%s "
                            "navigation=%s reason=%s",
                            request_url,
                            navigation_request,
                            validation_error,
                        )
                        await route.abort()
                        return
                    await route.continue_()

                await context.route("**/*", _route_handler)
                page = await context.new_page()
                await page.add_init_script(
                    """
                    Object.defineProperty(navigator, "webdriver", { get: () => undefined });
                    """
                )
                await page.goto(normalized_start_url, wait_until="domcontentloaded")
                return pw, browser, page

            setattr(auto_browse_run_module, "run_browser", guarded_run_browser)
            _AUTO_BROWSE_GUARD_INSTALLED = True

        return None

    async def _validate_navigation_scope(
        self,
        start_host: str,
        source_url: str,
        trace_urls: list[str],
    ) -> Optional[str]:
        candidate_urls = [source_url, *trace_urls]
        seen: set[str] = set()
        for url in candidate_urls:
            normalized_url = (url or "").strip()
            if not normalized_url or normalized_url in seen:
                continue
            seen.add(normalized_url)

            validation_error = await self._validate_external_url_async(normalized_url)
            if validation_error:
                return (
                    f"Scraper navigated to a disallowed URL: {normalized_url}. "
                    f"Reason: {validation_error}"
                )

            current_host = self._normalized_hostname(normalized_url)
            if current_host != start_host:
                return (
                    "Scraper navigated outside the allowed host "
                    f"('{start_host}' -> '{current_host}')."
                )
        return None

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
