"""
Logging configuration for the application.
"""

import logging
import sys
from typing import Any

# Configure logging format
LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def setup_logging(level: str = "INFO") -> None:
    """
    Setup application logging configuration.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format=LOGGING_FORMAT,
        datefmt=DATE_FORMAT,
        stream=sys.stdout,
        force=True,
    )

    # Configure specific loggers
    configure_loggers()


def configure_loggers() -> None:
    """Configure specific logger levels and handlers."""
    loggers_config: dict[str, Any] = {
        "app": {"level": logging.INFO},
        "app.services": {"level": logging.INFO},
        "app.services.data": {"level": logging.DEBUG},
        "app.routers": {"level": logging.INFO},
        "uvicorn": {"level": logging.INFO},
        "psycopg2": {"level": logging.WARNING},
    }

    for logger_name, config in loggers_config.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(config["level"])


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
