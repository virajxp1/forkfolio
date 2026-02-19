"""
Unit tests for live embeddings generation.
"""

import pytest

from app.core.config import settings
from app.services.llm_generation_service import make_embedding
from app.tests.utils.helpers import maybe_throttle


@pytest.mark.slow
def test_live_embedding_generates_vector() -> None:
    if not settings.OPEN_ROUTER_API_KEY:
        pytest.skip("OPEN_ROUTER_API_KEY not set; skipping live embeddings test.")

    maybe_throttle()
    vector = make_embedding("pasta with tomato sauce")
    assert isinstance(vector, list)
    assert len(vector) == 768
    assert all(isinstance(v, float) for v in vector)
