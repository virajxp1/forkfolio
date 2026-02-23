"""Custom exception types for the application."""


class ForkFolioError(Exception):
    """Base exception for all ForkFolio errors."""


class DatabaseError(ForkFolioError):
    """Database operation errors."""


class ConnectionPoolError(DatabaseError):
    """Connection pool management errors."""
