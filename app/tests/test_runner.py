#!/usr/bin/env python3
"""
Simple test runner.
"""

import subprocess
import sys


def main():
    """Run tests."""
    if len(sys.argv) > 1 and sys.argv[1] == "parallel":
        cmd = ["python", "-m", "pytest", "app/tests/e2e/", "-n", "auto", "-v"]
    else:
        cmd = ["python", "-m", "pytest", "app/tests/e2e/", "-v"]

    result = subprocess.run(cmd, check=False)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
