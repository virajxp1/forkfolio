"""Simple test helpers."""

import os
import time

from app.tests.utils.constants import DEBUG_TEXT_LENGTH


def truncate_debug_text(text: str, max_length: int = DEBUG_TEXT_LENGTH) -> str:
    """Truncate text for debug output."""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text


def maybe_throttle() -> None:
    """Optional sleep between live LLM calls to avoid rate limits."""
    delay = os.getenv("LLM_TEST_THROTTLE_SECONDS")
    if delay is None:
        delay_seconds = 1.0
    else:
        delay_seconds = float(delay)
    if delay_seconds > 0:
        time.sleep(delay_seconds)
