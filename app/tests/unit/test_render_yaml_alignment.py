from pathlib import Path
import re

from app.core.config import settings

REPO_ROOT = Path(__file__).resolve().parents[3]
RENDER_CONFIG = REPO_ROOT / "render.yaml"


def _render_health_check_path() -> str:
    content = RENDER_CONFIG.read_text(encoding="utf-8")
    match = re.search(
        r"^\s*healthCheckPath:\s*([^\s#]+)\s*$",
        content,
        flags=re.MULTILINE,
    )
    assert match, "render.yaml must define healthCheckPath."
    return match.group(1).strip("\"'")


def test_render_health_check_matches_api_base_path() -> None:
    assert _render_health_check_path() == f"{settings.API_BASE_PATH}/health"
