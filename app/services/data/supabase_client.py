from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool

from app.core.exceptions import ConnectionPoolError
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger(__name__)

# Global connection pool
_connection_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None


def init_connection_pool() -> None:
    """Initialize the connection pool (idempotent)."""
    global _connection_pool
    if _connection_pool is not None:
        return

    password = settings.SUPABASE_PASSWORD
    if not password:
        raise ValueError(
            "Database password is not configured. "
            "Set SUPABASE_PASSWORD in environment variables."
        )

    conn_args = {
        "host": settings.DB_HOST,
        "port": settings.DB_PORT,
        "dbname": settings.DB_NAME,
        "user": settings.DB_USER,
        "password": password,
        "sslmode": settings.DB_SSLMODE,
        "cursor_factory": psycopg2.extras.RealDictCursor,
        "connect_timeout": 5,
    }

    try:
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=settings.DB_POOL_MINCONN,
            maxconn=settings.DB_POOL_MAXCONN,
            **conn_args,
        )
        logger.info("Database connection pool initialized")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e!s}")
        raise ConnectionPoolError(f"Failed to initialize connection pool: {e!s}") from e


def get_db_connection():
    """Get a connection from the pool (lazy init)."""
    if _connection_pool is None:
        init_connection_pool()
    try:
        return _connection_pool.getconn()
    except Exception as e:
        logger.error(f"Failed to get connection from pool: {e!s}")
        raise ConnectionPoolError(f"Failed to get connection from pool: {e!s}") from e


def return_db_connection(conn) -> None:
    """Return a connection to the pool."""
    if _connection_pool and conn:
        try:
            _connection_pool.putconn(conn)
        except Exception as e:
            logger.warning(f"Failed to return connection to pool: {e!s}")


def get_pool_status() -> dict:
    """Basic pool status."""
    if _connection_pool is None:
        return {"pool_initialized": False}
    return {
        "pool_initialized": True,
        "minconn": _connection_pool.minconn,
        "maxconn": _connection_pool.maxconn,
    }


def close_connection_pool() -> None:
    """Close all connections in the pool."""
    global _connection_pool
    if _connection_pool:
        try:
            _connection_pool.closeall()
            logger.info("Connection pool closed")
        finally:
            _connection_pool = None


@contextmanager
def get_db_context() -> Generator[Any, None, None]:
    """Commit/rollback wrapper that always returns the connection to the pool."""
    conn = None
    try:
        conn = get_db_connection()
        yield conn
    except Exception:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    else:
        if conn:
            conn.commit()
    finally:
        if conn:
            return_db_connection(conn)
