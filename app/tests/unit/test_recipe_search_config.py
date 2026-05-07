import json
from pathlib import Path

import pytest

from app.api.v1.helpers import recipe_search
from app.core.config import settings


def _write_keywords(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


@pytest.fixture(autouse=True)
def clear_keyword_cache() -> None:
    recipe_search._load_keyword_sets.cache_clear()
    yield
    recipe_search._load_keyword_sets.cache_clear()


def test_compute_boosts_uses_configured_keyword_file(
    tmp_path: Path, monkeypatch
) -> None:
    keywords_path = tmp_path / "keywords.json"
    _write_keywords(
        keywords_path,
        {
            "cuisines": {
                "fusion": ["umami", "fermented"],
            },
            "families": {
                "curry": ["rendang"],
            },
        },
    )
    monkeypatch.setattr(settings, "SEARCH_KEYWORDS_FILE", keywords_path)
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_HEURISTICS_ENABLED", True)

    total_boost, cuisine_boost, family_boost = recipe_search._compute_boosts(
        query="umami rendang",
        candidate_name="fermented umami rendang noodles",
        cuisine_boost=0.15,
        family_boost=0.1,
    )

    assert cuisine_boost == 0.15
    assert family_boost == 0.1
    assert total_boost == 0.25


def test_compute_boosts_returns_zero_when_heuristics_disabled(monkeypatch) -> None:
    monkeypatch.setattr(settings, "SEMANTIC_SEARCH_HEURISTICS_ENABLED", False)

    total_boost, cuisine_boost, family_boost = recipe_search._compute_boosts(
        query="paneer curry",
        candidate_name="paneer tikka masala",
        cuisine_boost=0.15,
        family_boost=0.1,
    )

    assert total_boost == 0.0
    assert cuisine_boost == 0.0
    assert family_boost == 0.0
