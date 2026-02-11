#!/usr/bin/env python3
"""
Simple test runner for unit and E2E tests.
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parents[2]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))


def main():
    """Run tests based on command line arguments."""
    from app.tests.utils.test_runners import (
        run_all_tests,
        run_e2e_tests,
        run_unit_tests,
    )

    if len(sys.argv) < 2:
        result = run_all_tests()
    elif sys.argv[1] == "unit":
        result = run_unit_tests()
    elif sys.argv[1] == "e2e":
        result = run_e2e_tests()
    elif sys.argv[1] == "parallel":
        result = run_all_tests(parallel=True)
    else:
        print("Usage: python3 app/tests/test_runner.py [unit|e2e|parallel]")
        result = 1

    sys.exit(result)


if __name__ == "__main__":
    main()
