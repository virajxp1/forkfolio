#!/usr/bin/env python3
"""
Test runner for different development workflows.
Provides fast feedback loops for developers.
"""

import subprocess
import sys
import time

# Constants
MIN_ARGS = 2


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n🔄 {description}")
    print(f"   Command: {' '.join(cmd)}")

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    duration = time.time() - start_time

    if result.returncode == 0:
        print(f"   ✅ Passed in {duration:.2f}s")
        return True
    else:
        print(f"   ❌ Failed in {duration:.2f}s")
        print(f"   Error: {result.stderr}")
        return False


def run_unit_tests():
    """Run unit tests - fastest feedback."""
    return run_command(
        ["python", "-m", "pytest", "-m", "unit", "-v"],
        "Running unit tests (fast feedback)",
    )


def run_integration_tests():
    """Run integration tests - medium speed."""
    return run_command(
        ["python", "-m", "pytest", "-m", "integration", "-v"],
        "Running integration tests (API layer)",
    )


def run_e2e_tests():
    """Run E2E tests - slowest but most comprehensive."""
    return run_command(
        ["python", "-m", "pytest", "-m", "e2e", "-v", "--tb=short"],
        "Running E2E tests (full system)",
    )


def run_all_tests():
    """Run all tests."""
    return run_command(["python", "-m", "pytest", "-v"], "Running all tests")


def run_parallel_tests():
    """Run tests in parallel for CI/CD."""
    return run_command(
        ["python", "-m", "pytest", "-n", "auto", "-v"], "Running tests in parallel"
    )


def run_development_workflow() -> bool:
    """Run development workflow: unit tests first, then integration if they pass."""
    print("🚀 Development workflow: Fast feedback loop")
    success = run_unit_tests()
    if success:
        success = run_integration_tests()
        if success:
            print("\n🎉 All fast tests passed! Ready to commit.")
        else:
            print("\n⚠️  Integration tests failed. Check API layer.")
    else:
        print("\n⚠️  Unit tests failed. Fix business logic first.")
    return success


def main():
    """Main test runner."""
    if len(sys.argv) < MIN_ARGS:
        print("🧪 Test Runner - Choose your workflow:")
        print("   python test_runner.py unit        # Fast unit tests (~2s)")
        print("   python test_runner.py integration # API tests (~10s)")
        print("   python test_runner.py e2e         # Full system tests (~30s)")
        print("   python test_runner.py all         # All tests (~45s)")
        print("   python test_runner.py parallel    # Parallel execution")
        print("   python test_runner.py dev         # Development workflow")
        return

    test_type = sys.argv[1].lower()

    test_functions = {
        "unit": run_unit_tests,
        "integration": run_integration_tests,
        "e2e": run_e2e_tests,
        "all": run_all_tests,
        "parallel": run_parallel_tests,
        "dev": run_development_workflow,
    }

    if test_type not in test_functions:
        print(f"❌ Unknown test type: {test_type}")
        return

    success = test_functions[test_type]()

    if success:
        print(f"\n🎉 {test_type.title()} tests completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 {test_type.title()} tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
