"""Test runner utilities and commands."""

import subprocess


def run_unit_tests() -> int:
    """Run unit tests only."""
    cmd = ["python", "-m", "pytest", "app/tests/unit/", "-v"]
    result = subprocess.run(cmd, check=False)
    return result.returncode


def run_e2e_tests(parallel: bool = False) -> int:
    """Run E2E tests only."""
    cmd = ["python", "-m", "pytest", "app/tests/e2e/", "-v"]
    if parallel:
        cmd.extend(["-n", "auto"])

    result = subprocess.run(cmd, check=False)
    return result.returncode


def run_all_tests(parallel: bool = False) -> int:
    """Run all tests."""
    cmd = ["python", "-m", "pytest", "app/tests/", "-v"]
    if parallel:
        cmd.extend(["-n", "auto"])

    result = subprocess.run(cmd, check=False)
    return result.returncode
