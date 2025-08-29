"""Simple test helpers."""

from app.tests.utils.constants import DEBUG_TEXT_LENGTH


def truncate_debug_text(text: str, max_length: int = DEBUG_TEXT_LENGTH) -> str:
    """Truncate text for debug output."""
    if len(text) > max_length:
        return text[:max_length] + "..."
    return text
