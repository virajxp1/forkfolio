from html.parser import HTMLParser
import ipaddress
import os
import socket
from typing import Optional
from urllib.parse import urljoin, urlsplit

import httpx

from app.core.logging import get_logger
from app.api.schemas import Recipe
from app.services.data.managers.recipe_manager import RecipeManager
from app.services.recipe_dedupe_impl import RecipeDedupeServiceImpl
from app.services.recipe_embeddings_impl import RecipeEmbeddingsServiceImpl
from app.services.recipe_extractor_impl import RecipeExtractorImpl
from app.services.recipe_input_cleanup_impl import RecipeInputCleanupServiceImpl

logger = get_logger(__name__)

URL_FETCH_TIMEOUT_SECONDS = 20.0
URL_FETCH_USER_AGENT = "Mozilla/5.0 (compatible; ForkFolioRecipeBot/1.0)"
URL_FETCH_MAX_REDIRECTS = 5
URL_FETCH_ALLOWED_SCHEMES = frozenset({"http", "https"})
URL_FETCH_REQUIRE_HTTPS = (
    os.getenv("PREVIEW_URL_REQUIRE_HTTPS", "").strip().lower() == "true"
)
URL_FETCH_DOMAIN_ALLOWLIST = tuple(
    sorted(
        {
            domain.strip().lower().rstrip(".")
            for domain in os.getenv("PREVIEW_URL_ALLOWLIST", "").split(",")
            if domain.strip()
        }
    )
)
URL_FETCH_REDIRECT_STATUS_CODES = frozenset({301, 302, 303, 307, 308})
MAX_EXTRACTED_TEXT_CHARS = 25000
HTML_IGNORED_TAGS = {
    "script",
    "style",
    "noscript",
    "svg",
    "canvas",
    "iframe",
    "template",
}
HTML_BLOCK_TAGS = {
    "article",
    "aside",
    "br",
    "dd",
    "div",
    "dl",
    "dt",
    "footer",
    "form",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "td",
    "th",
    "tr",
    "ul",
}


class _VisibleTextExtractor(HTMLParser):
    """Extract visible text while skipping common non-content HTML blocks."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs  # Unused
        normalized = tag.lower()
        if normalized in HTML_IGNORED_TAGS:
            self._ignored_depth += 1
            return
        if normalized in HTML_BLOCK_TAGS:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in HTML_IGNORED_TAGS:
            if self._ignored_depth > 0:
                self._ignored_depth -= 1
            return
        if normalized in HTML_BLOCK_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._ignored_depth > 0:
            return
        cleaned = " ".join(data.split())
        if cleaned:
            self._parts.append(f"{cleaned} ")

    def visible_text(self) -> str:
        if not self._parts:
            return ""

        text = "".join(self._parts)
        lines: list[str] = []
        for line in text.splitlines():
            normalized = " ".join(line.split())
            if normalized:
                lines.append(normalized)
        return "\n".join(lines)


class RecipeProcessingService:
    """
    Service that handles the complete recipe processing pipeline:
    1. Cleanup raw input
    2. Extract structured recipe data
    3. Deduplicate
    4. Generate embeddings
    5. Store in database (recipe + embeddings)
    6. Return database ID
    """

    def __init__(
        self,
        cleanup_service: RecipeInputCleanupServiceImpl | None = None,
        extractor_service: RecipeExtractorImpl | None = None,
        recipe_manager: RecipeManager | None = None,
        embeddings_service: RecipeEmbeddingsServiceImpl | None = None,
        dedupe_service: RecipeDedupeServiceImpl | None = None,
    ):
        self.cleanup_service = cleanup_service or RecipeInputCleanupServiceImpl()
        self.extractor_service = extractor_service or RecipeExtractorImpl()
        self.recipe_manager = recipe_manager or RecipeManager()
        self.embeddings_service = embeddings_service or RecipeEmbeddingsServiceImpl()
        self.dedupe_service = dedupe_service or RecipeDedupeServiceImpl()

    def process_raw_recipe(
        self,
        raw_input: str,
        source_url: Optional[str] = None,
        enforce_deduplication: bool = True,
        is_test: bool = False,
    ) -> tuple[Optional[str], Optional[str], bool]:
        """
        Process raw recipe input through the complete pipeline.

        Args:
            raw_input: Raw unstructured recipe text
            source_url: Optional source URL for reference
            enforce_deduplication: When true, attempt to dedupe before inserting
            is_test: Mark the resulting recipe as test data

        Returns:
            Tuple of (recipe_id, error_message, created).
            If successful, recipe_id contains the database ID and created indicates
            whether a new recipe was inserted.
        """
        try:
            # Step 1: Clean up the raw input
            cleaned_text = self._cleanup_input(raw_input)
            if not cleaned_text:
                return None, "Failed to cleanup input text", False

            # Step 2: Extract structured recipe data
            recipe, extraction_error = self._extract_recipe(cleaned_text)
            if extraction_error or not recipe:
                return None, f"Recipe extraction failed: {extraction_error}", False

            # Step 3: Deduplicate
            embedding: Optional[list[float]] = None
            if enforce_deduplication:
                is_duplicate, existing_id, embedding = (
                    self.dedupe_service.find_duplicate(
                        recipe,
                        include_test_data=is_test,
                    )
                )
                if is_duplicate and existing_id:
                    logger.info(f"Duplicate recipe detected: {existing_id}")
                    return existing_id, None, False

            # Step 4: Generate embeddings (title + ingredients)
            if embedding is None:
                embedding = self._generate_title_ingredients_embedding(recipe)
                if embedding is None:
                    return None, "Failed to generate recipe embeddings", False

            # Step 5: Insert into database (recipe + embeddings)
            recipe_id = self._store_recipe(recipe, source_url, embedding, is_test)
            if not recipe_id:
                return None, "Failed to store recipe in database", False
            logger.info(f"Successfully processed recipe with ID: {recipe_id}")
            return recipe_id, None, True

        except Exception as e:
            error_msg = f"Recipe processing failed: {e!s}"
            logger.error(error_msg)
            return None, error_msg, False

    def preview_recipe_from_url(
        self, source_url: str
    ) -> tuple[Optional[Recipe], Optional[str], dict[str, int]]:
        """
        Fetch and parse a URL, then return an extracted recipe preview.

        This flow intentionally does not write to the database.
        """
        diagnostics: dict[str, int] = {}
        try:
            raw_html = self._fetch_raw_html(source_url)
            if not raw_html:
                return None, "Failed to fetch raw HTML from URL", diagnostics

            extracted_text = self._extract_relevant_content(
                raw_html, max_chars=MAX_EXTRACTED_TEXT_CHARS
            )
            diagnostics["raw_html_length"] = len(raw_html)
            diagnostics["extracted_text_length"] = len(extracted_text)
            if not extracted_text:
                return None, "Failed to extract readable content from HTML", diagnostics

            recipe, extraction_error = self._attempt_preview_extraction(
                extracted_text, diagnostics
            )
            if extraction_error or not recipe:
                return (
                    None,
                    f"Recipe extraction failed: {extraction_error}",
                    diagnostics,
                )

            logger.info("Recipe preview extracted successfully for URL: %s", source_url)
            return recipe, None, diagnostics
        except Exception as e:
            error_msg = f"Recipe URL preview failed: {e!s}"
            logger.error(error_msg)
            return None, error_msg, diagnostics

    def _fetch_raw_html(self, source_url: str) -> Optional[str]:
        """
        Fetch raw HTML from a URL using HTTPX with SSRF protections.

        - Validates source URL host/scheme
        - Resolves hostname and blocks private/internal ranges
        - Re-validates every redirect target
        """
        current_url = source_url
        try:
            with httpx.Client(
                timeout=URL_FETCH_TIMEOUT_SECONDS,
                follow_redirects=False,
                headers={"User-Agent": URL_FETCH_USER_AGENT},
            ) as client:
                for _ in range(URL_FETCH_MAX_REDIRECTS + 1):
                    validated_url, validation_error = self._validate_outbound_url(
                        current_url
                    )
                    if validation_error or not validated_url:
                        logger.warning(
                            "Blocked outbound URL fetch for recipe preview. url=%s reason=%s",
                            current_url,
                            validation_error,
                        )
                        return None

                    response = client.get(validated_url)
                    if response.status_code in URL_FETCH_REDIRECT_STATUS_CODES:
                        location = response.headers.get("location")
                        if not location:
                            logger.error(
                                "Redirect response missing Location header. url=%s status=%s",
                                validated_url,
                                response.status_code,
                            )
                            return None
                        current_url = urljoin(validated_url, location)
                        continue

                    response.raise_for_status()
                    return response.text

            logger.error(
                "URL fetch exceeded redirect limit. url=%s max_redirects=%s",
                source_url,
                URL_FETCH_MAX_REDIRECTS,
            )
            return None
        except httpx.HTTPStatusError as e:
            logger.error(
                "URL fetch returned non-200 response. url=%s status=%s",
                source_url,
                e.response.status_code,
            )
            return None
        except httpx.HTTPError as e:
            logger.error("URL fetch failed for %s: %s", source_url, e)
            return None
        except Exception as e:
            logger.error("URL fetch validation failed for %s: %s", source_url, e)
            return None

    def _validate_outbound_url(
        self, candidate_url: str
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Validate URL target for outbound fetch to reduce SSRF risk.

        Returns:
            Tuple of (validated_url, error_message)
        """
        parsed = urlsplit(candidate_url)
        scheme = parsed.scheme.lower()
        if scheme not in URL_FETCH_ALLOWED_SCHEMES:
            return None, f"Unsupported URL scheme: {scheme}"

        if URL_FETCH_REQUIRE_HTTPS and scheme != "https":
            return None, "Only HTTPS preview URLs are allowed"

        hostname = (parsed.hostname or "").strip().lower().rstrip(".")
        if not hostname:
            return None, "URL hostname is missing"

        if URL_FETCH_DOMAIN_ALLOWLIST and not self._is_allowlisted_hostname(hostname):
            return None, f"Host is not allowlisted: {hostname}"

        if hostname == "localhost":
            return None, "Loopback host is not allowed"

        port = parsed.port or (443 if scheme == "https" else 80)
        direct_ip = self._parse_ip_literal(hostname)
        if direct_ip is not None:
            if self._is_disallowed_ip(direct_ip):
                return None, f"Blocked IP target: {direct_ip}"
            return candidate_url, None

        try:
            addr_info = socket.getaddrinfo(hostname, port, type=socket.SOCK_STREAM)
        except socket.gaierror as e:
            return None, f"Failed to resolve host '{hostname}': {e}"

        if not addr_info:
            return None, f"No addresses resolved for host '{hostname}'"

        resolved_ips: set[str] = set()
        for item in addr_info:
            sockaddr = item[4]
            if not sockaddr:
                continue
            ip_text = sockaddr[0]
            if ip_text in resolved_ips:
                continue
            resolved_ips.add(ip_text)
            resolved_ip = self._parse_ip_literal(ip_text)
            if resolved_ip is None:
                return None, f"Resolved non-IP address for host '{hostname}'"
            if self._is_disallowed_ip(resolved_ip):
                return None, f"Blocked resolved IP for host '{hostname}': {resolved_ip}"

        return candidate_url, None

    @staticmethod
    def _parse_ip_literal(
        host_value: str,
    ) -> Optional[ipaddress.IPv4Address | ipaddress.IPv6Address]:
        try:
            return ipaddress.ip_address(host_value)
        except ValueError:
            return None

    @staticmethod
    def _is_disallowed_ip(
        ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address,
    ) -> bool:
        return (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_unspecified
            or ip_obj.is_reserved
        )

    @staticmethod
    def _is_allowlisted_hostname(hostname: str) -> bool:
        return any(
            hostname == allowed or hostname.endswith(f".{allowed}")
            for allowed in URL_FETCH_DOMAIN_ALLOWLIST
        )

    def _extract_relevant_content(self, raw_html: str, max_chars: int) -> str:
        """
        Parse HTML and extract visible text with light deterministic cleanup only.
        """
        if not raw_html or not raw_html.strip():
            return ""

        parser = _VisibleTextExtractor()
        parser.feed(raw_html)
        parser.close()

        visible_text = parser.visible_text()
        if not visible_text:
            return ""

        lines = [line.strip() for line in visible_text.splitlines() if line.strip()]
        if not lines:
            return ""

        extracted = "\n".join(lines)
        if len(extracted) > max_chars:
            extracted = extracted[:max_chars]

        return extracted

    def _attempt_preview_extraction(
        self,
        extracted_text: str,
        diagnostics: dict[str, int],
    ) -> tuple[Optional[Recipe], Optional[str]]:
        cleaned_text = self._cleanup_input(extracted_text)
        diagnostics["cleaned_text_length"] = len(cleaned_text or "")
        if not cleaned_text:
            return None, "Failed to cleanup extracted website content"

        recipe, extraction_error = self._extract_recipe(cleaned_text)
        if extraction_error or not recipe:
            return None, extraction_error
        return recipe, None

    def _cleanup_input(self, raw_input: str) -> Optional[str]:
        """
        Step 1: Clean up messy raw input using the cleanup service.

        Args:
            raw_input: Raw messy input text

        Returns:
            Cleaned text or None if cleanup failed
        """
        try:
            cleaned_text = self.cleanup_service.cleanup_input(raw_input)
            logger.info(
                f"Input cleanup completed. Original length: {len(raw_input)}, "
                f"Cleaned length: {len(cleaned_text)}"
            )
            return cleaned_text
        except Exception as e:
            logger.error(f"Input cleanup failed: {e}")
            return None

    def _extract_recipe(
        self, cleaned_text: str
    ) -> tuple[Optional[Recipe], Optional[str]]:
        """
        Step 2: Extract structured recipe data from cleaned text.

        Args:
            cleaned_text: Clean recipe text

        Returns:
            Tuple of (Recipe object, error_message)
        """
        try:
            recipe, error = self.extractor_service.extract_recipe_from_raw_text(
                cleaned_text
            )
            if error:
                logger.error(f"Recipe extraction failed: {error}")
                return None, error

            logger.info(f"Recipe extraction successful: {recipe.title}")
            return recipe, None

        except Exception as e:
            error_msg = f"Recipe extraction error: {e!s}"
            logger.error(error_msg)
            return None, error_msg

    def _store_recipe(
        self,
        recipe: Recipe,
        source_url: Optional[str],
        embedding: list[float],
        is_test: bool,
    ) -> Optional[str]:
        """
        Step 4: Store the recipe and embeddings in the database.

        Args:
            recipe: Recipe object to store
            source_url: Optional source URL
            embedding: Embedding vector for title + ingredients

        Returns:
            Database ID of stored recipe or None if storage failed
        """
        try:
            # Create the main recipe record and embeddings in one transaction
            recipe_id = self.recipe_manager.create_recipe_from_model(
                recipe=recipe,
                source_url=source_url,
                embedding_type="title_ingredients",
                embedding=embedding,
                is_test_data=is_test,
            )

            logger.info(f"Recipe stored successfully with ID: {recipe_id}")
            return recipe_id

        except Exception as e:
            logger.error(f"Recipe storage failed: {e}")
            return None

    def _generate_title_ingredients_embedding(
        self, recipe: Recipe
    ) -> Optional[list[float]]:
        """Step 3: Generate embeddings for the recipe."""
        try:
            return self.embeddings_service.embed_title_ingredients(
                title=recipe.title,
                ingredients=recipe.ingredients,
            )
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None
