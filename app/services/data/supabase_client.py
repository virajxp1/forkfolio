import os
import configparser
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any, Optional

import psycopg2
import psycopg2.extras
import psycopg2.pool

from app.core.exceptions import ConnectionPoolError
from app.core.logging import get_logger

logger = get_logger(__name__)

# Global connection pool
_connection_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
_CONFIG_PATH = os.getenv("DB_CONFIG_FILE", "config/db.config.ini")


def _load_config() -> configparser.ConfigParser:
    cfg = configparser.ConfigParser()
    if not cfg.read(_CONFIG_PATH):
        raise FileNotFoundError(f"Database config file not found: {_CONFIG_PATH}")
    return cfg


def init_connection_pool() -> None:
    """Initialize the connection pool (idempotent)."""
    global _connection_pool
    if _connection_pool is not None:
        return

    cfg = _load_config()
    password = os.getenv("SUPABASE_PASSWORD") or os.getenv("DB_PASSWORD")
    if not password:
        raise ValueError("SUPABASE_PASSWORD (or DB_PASSWORD) must be set in the environment")

    host = cfg.get("database", "host")
    port = int(cfg.get("database", "port", fallback="5432"))
    user = cfg.get("database", "user")
    name = cfg.get("database", "name", fallback="postgres")
    sslmode = cfg.get("database", "sslmode", fallback="require")

    minconn = int(cfg.get("pool", "minconn", fallback="2"))
    maxconn = int(cfg.get("pool", "maxconn", fallback="10"))

    conn_args = {
        "host": host,
        "port": port,
        "dbname": name,
        "user": user,
        "password": password,
        "sslmode": sslmode,
        "cursor_factory": psycopg2.extras.RealDictCursor,
        "connect_timeout": 5,
    }

    try:
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
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
