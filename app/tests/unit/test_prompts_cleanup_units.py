from app.core import prompts
from app.core.config import settings


def test_cleanup_prompt_uses_metric_units_when_configured(monkeypatch) -> None:
    monkeypatch.setattr(settings, "RECIPE_UNIT_SYSTEM", "metric")

    prompt = prompts.build_cleanup_system_prompt()

    assert "Celsius with °C" in prompt
    assert 'Fahrenheit with °F (e.g., "350°F")' not in prompt


def test_cleanup_prompt_supports_both_unit_guidance() -> None:
    prompt = prompts.build_cleanup_system_prompt(unit_system="both")

    assert "Fahrenheit and Celsius" in prompt
    assert "350°F / 180°C" in prompt
