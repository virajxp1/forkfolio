from __future__ import annotations

from typing import Optional

import requests

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AutoBrowseClient:
    """
    Thin HTTP client for the hosted auto-browse API.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        timeout_seconds: float | None = None,
    ):
        resolved_base_url = (
            base_url if base_url is not None else settings.AUTO_BROWSE_API_BASE_URL
        )
        self.base_url = resolved_base_url.strip().rstrip("/")
        resolved_api_token = (
            api_token if api_token is not None else settings.AUTO_BROWSE_API_TOKEN
        )
        self.api_token = resolved_api_token.strip()
        self.timeout_seconds = (
            timeout_seconds
            if timeout_seconds is not None
            else settings.AUTO_BROWSE_API_TIMEOUT_SECONDS
        )

    def run(
        self,
        *,
        start_url: str,
        target_prompt: str,
        max_steps: int,
        max_actions_per_step: int,
        extraction_schema: dict[str, str] | None = None,
    ) -> tuple[Optional[dict], Optional[str]]:
        if not self.base_url:
            return None, "AUTO_BROWSE_API_BASE_URL is not configured."
        if not self.api_token:
            return None, "AUTO_BROWSE_API_TOKEN is not configured."

        request_payload = {
            "start_url": start_url,
            "target_prompt": target_prompt,
            "max_steps": max_steps,
            "max_actions_per_step": max_actions_per_step,
        }
        if extraction_schema is not None:
            request_payload["extraction_schema"] = extraction_schema

        try:
            response = requests.post(
                f"{self.base_url}/run",
                json=request_payload,
                headers={"X-API-Token": self.api_token},
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.error("Auto-browse API request failed: %s", exc)
            return None, f"URL scrape failed: unable to reach auto-browse API ({exc!s})"
        except Exception as exc:
            logger.error("Auto-browse API request raised unexpected error: %s", exc)
            return None, f"URL scrape failed: {exc!s}"

        response_payload = self._decode_json_response(response)
        if response.status_code != 200:
            return None, self._extract_api_error(response_payload, response.status_code)

        if not response_payload:
            return (
                None,
                "URL scrape failed: auto-browse API returned an empty response.",
            )

        result_error = response_payload.get("error")
        if isinstance(result_error, str) and result_error.strip():
            return None, f"URL scrape failed: {result_error.strip()}"

        return response_payload, None

    @staticmethod
    def _decode_json_response(response: requests.Response) -> Optional[dict]:
        try:
            payload = response.json()
        except ValueError:
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _extract_api_error(
        response_payload: Optional[dict],
        status_code: int,
    ) -> str:
        if response_payload:
            detail = response_payload.get("detail")
            if isinstance(detail, str) and detail.strip():
                return f"URL scrape failed: {detail.strip()}"
            if isinstance(detail, dict):
                nested = (
                    detail.get("error") or detail.get("message") or detail.get("detail")
                )
                if isinstance(nested, str) and nested.strip():
                    return f"URL scrape failed: {nested.strip()}"
                return f"URL scrape failed: {detail}"
            for key in ("error", "message"):
                value = response_payload.get(key)
                if isinstance(value, str) and value.strip():
                    return f"URL scrape failed: {value.strip()}"
        return f"URL scrape failed with status {status_code}."
