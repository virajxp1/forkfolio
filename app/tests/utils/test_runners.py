"""Test runner utilities and commands."""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PYTEST_CONFIG_PATH = PROJECT_ROOT / "pytest.ini"


def _base_pytest_cmd() -> list[str]:
    return [sys.executable, "-m", "pytest", "-c", str(PYTEST_CONFIG_PATH)]


def _run_pytest(cmd: list[str]) -> int:
    result = subprocess.run(cmd, check=False, cwd=PROJECT_ROOT)
    return result.returncode


def run_unit_tests() -> int:
    """Run unit tests only."""
    cmd = [*_base_pytest_cmd(), "app/tests/unit/", "-v"]
    return _run_pytest(cmd)


def run_e2e_tests(parallel: bool = False) -> int:
    """Run E2E tests only."""
    cmd = [*_base_pytest_cmd(), "app/tests/e2e/", "-v"]
    if parallel:
        cmd.extend(["-n", "auto"])

    return _run_pytest(cmd)


def run_all_tests(parallel: bool = False) -> int:
    """Run all tests."""
    cmd = [*_base_pytest_cmd(), "app/tests/", "-v"]
    if parallel:
        cmd.extend(["-n", "auto"])

    return _run_pytest(cmd)
