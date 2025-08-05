"""
Custom exception types for the application.
"""


class ForkFolioError(Exception):
    """Base exception for all ForkFolio errors"""

    pass


class DatabaseError(ForkFolioError):
    """Database operation errors"""

    pass


class RecipeNotFoundError(ForkFolioError):
    """Recipe not found in database"""

    pass


class RecipeProcessingError(ForkFolioError):
    """Recipe processing pipeline errors"""

    pass


class RecipeExtractionError(RecipeProcessingError):
    """Recipe extraction from raw text failed"""

    pass


class RecipeCleanupError(RecipeProcessingError):
    """Recipe input cleanup failed"""

    pass


class ConnectionPoolError(DatabaseError):
    """Connection pool management errors"""

    pass


class ValidationError(ForkFolioError):
    """Data validation errors"""

    pass
