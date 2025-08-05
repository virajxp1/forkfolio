import os
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import psycopg2
import psycopg2.extras
import psycopg2.pool

from app.core.exceptions import ConnectionPoolError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global connection pool
_connection_pool = None


def init_connection_pool():
    """Initialize the connection pool"""
    global _connection_pool  # noqa: PLW0603

    # Use DATABASE_URL if provided, otherwise build from components
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        password = os.getenv("SUPABASE_PASSWORD")
        if not password:
            raise ValueError(
                "SUPABASE_PASSWORD or DATABASE_URL environment variable is required"
            )

        # Use configurable host and port for different environments
        db_host = os.getenv("DATABASE_HOST", "db.ddrjsrzmbnovwqnstnvo.supabase.co")
        db_port = os.getenv("DATABASE_PORT", "5432")

        # Use different username format for Session Pooler vs Direct Connection
        if "pooler.supabase.com" in db_host:
            # Session Pooler format: postgres.project_ref
            username = "postgres.ddrjsrzmbnovwqnstnvo"
        else:
            # Direct Connection format
            username = "postgres"

        database_url = (
            f"postgresql://{username}:{password}@{db_host}:{db_port}/postgres"
        )

    try:
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=2,
            maxconn=20,
            dsn=database_url,
            cursor_factory=psycopg2.extras.RealDictCursor,
        )
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize connection pool: {e!s}")
        raise ConnectionPoolError(f"Failed to initialize connection pool: {e!s}") from e


def get_db_connection():
    """Get a connection from the pool"""
    if _connection_pool is None:
        init_connection_pool()

    try:
        return _connection_pool.getconn()
    except Exception as e:
        logger.error(f"Failed to get connection from pool: {e!s}")
        raise ConnectionPoolError(f"Failed to get connection from pool: {e!s}") from e


def return_db_connection(conn):
    """Return a connection to the pool"""
    if _connection_pool and conn:
        try:
            _connection_pool.putconn(conn)
        except Exception as e:
            logger.error(f"Failed to return connection to pool: {e!s}")
            # Don't raise here as it's called in finally blocks


def get_pool_status() -> dict:
    """Get connection pool status for monitoring"""
    if _connection_pool is None:
        return {"pool_initialized": False}

    # Note: psycopg2 pool doesn't expose these stats directly
    # This is a basic health check
    return {
        "pool_initialized": True,
        "minconn": _connection_pool.minconn,
        "maxconn": _connection_pool.maxconn,
    }


def close_connection_pool():
    """Close all connections in the pool"""
    global _connection_pool  # noqa: PLW0603
    if _connection_pool:
        try:
            _connection_pool.closeall()
            logger.info("Connection pool closed successfully")
        except Exception as e:
            logger.error(f"Error closing connection pool: {e!s}")
        finally:
            _connection_pool = None


@contextmanager
def get_db_context() -> Generator[Any, None, None]:
    """Context manager for database operations"""
    conn = None
    try:
        conn = get_db_connection()
        yield conn
    except Exception:
        if conn:
            conn.rollback()
        raise
    else:
        if conn:
            conn.commit()
    finally:
        if conn:
            return_db_connection(conn)
