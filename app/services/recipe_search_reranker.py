from abc import ABC, abstractmethod


class RecipeSearchRerankerService(ABC):
    """Interface for reranking semantic search candidates."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        candidates: list[dict],
        max_results: int,
    ) -> list[dict]:
        """Return ranked entries containing candidate ids and rerank scores."""
        raise NotImplementedError
