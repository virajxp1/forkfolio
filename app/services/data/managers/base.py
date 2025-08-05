import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from app.services.data.supabase_client import get_db_context

logger = logging.getLogger(__name__)


class BaseManager:
    """Base class for database managers with connection pooling."""

    @contextmanager
    def get_db_context(self) -> Generator[tuple[Any, Any], None, None]:
        """Get database connection and cursor with automatic cleanup"""
        with get_db_context() as conn:
            cursor = conn.cursor()
            try:
                yield conn, cursor
            finally:
                cursor.close()

    def close(self):
        """Deprecated - connections are now managed automatically"""
        logger.warning(
            "close() method is deprecated - connections are managed automatically"
        )
