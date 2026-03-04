from __future__ import annotations

import requests

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AutoBrowseClient:
    def __init__(self):
        self.base_url = settings.AUTO_BROWSE_API_BASE_URL.strip().rstrip("/")
        self.api_token = settings.AUTO_BROWSE_API_TOKEN.strip()
        self.timeout_seconds = settings.AUTO_BROWSE_API_TIMEOUT_SECONDS

    def run(
        self,
        *,
        start_url: str,
        target_prompt: str,
        max_steps: int,
        max_actions_per_step: int,
        extraction_schema: dict[str, str] | None = None,
    ) -> tuple[dict | None, str | None]:
        if not self.base_url:
            return None, "AUTO_BROWSE_API_BASE_URL is not configured."
        if not self.api_token:
            return None, "AUTO_BROWSE_API_TOKEN is not configured."

        payload: dict[str, object] = {
            "start_url": start_url,
            "target_prompt": target_prompt,
            "max_steps": max_steps,
            "max_actions_per_step": max_actions_per_step,
        }
        if extraction_schema is not None:
            payload["extraction_schema"] = extraction_schema

        try:
            response = requests.post(
                f"{self.base_url}/run",
                json=payload,
                headers={"X-API-Token": self.api_token},
                timeout=self.timeout_seconds,
            )
        except requests.RequestException as exc:
            logger.error("Auto-browse API request failed: %s", exc)
            return None, f"URL scrape failed: unable to reach auto-browse API ({exc!s})"

        try:
            body = response.json()
        except ValueError:
            body = None

        if not isinstance(body, dict):
            return None, f"URL scrape failed with status {response.status_code}."
        if response.status_code != 200:
            detail = body.get("detail")
            if isinstance(detail, dict):
                detail = detail.get("error") or detail.get("message") or detail
            if isinstance(detail, str) and detail.strip():
                return None, f"URL scrape failed: {detail.strip()}"
            return None, f"URL scrape failed with status {response.status_code}."

        error = body.get("error")
        if isinstance(error, str) and error.strip():
            return None, f"URL scrape failed: {error.strip()}"
        return body, None
