import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Ensure .env is loaded and config paths resolve from repo root.
repo_root = Path(__file__).resolve().parents[2]
os.environ.setdefault("APP_CONFIG_FILE", str(repo_root / "config" / "app.config.ini"))

# Load repo .env, then allow a local .context/.env to override for secrets.
load_dotenv(dotenv_path=repo_root / ".env")
load_dotenv(dotenv_path=repo_root / ".context" / ".env", override=True)


def _is_ci_environment() -> bool:
    return bool(os.getenv("CI") or os.getenv("GITHUB_ACTIONS"))


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    if not _is_ci_environment():
        return

    terminal_reporter = session.config.pluginmanager.get_plugin("terminalreporter")
    if terminal_reporter is None:
        return

    skipped_reports = terminal_reporter.stats.get("skipped", [])
    if skipped_reports:
        terminal_reporter.write_sep(
            "=", f"{len(skipped_reports)} skipped test(s) found in CI; failing run."
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
