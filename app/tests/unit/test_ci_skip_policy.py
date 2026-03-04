from types import SimpleNamespace

import pytest

from app.tests import conftest as tests_conftest


def _build_session(skipped_count: int, exitstatus: pytest.ExitCode) -> SimpleNamespace:
    def write_sep(*_args, **_kwargs) -> None:
        return None

    reporter = SimpleNamespace(
        stats={"skipped": [object() for _ in range(skipped_count)]},
        write_sep=write_sep,
    )

    def get_plugin(name: str) -> SimpleNamespace | None:
        if name == "terminalreporter":
            return reporter
        return None

    pluginmanager = SimpleNamespace(get_plugin=get_plugin)
    config = SimpleNamespace(pluginmanager=pluginmanager)
    return SimpleNamespace(config=config, exitstatus=exitstatus)


def test_sessionfinish_does_not_fail_when_not_in_ci(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    session = _build_session(skipped_count=2, exitstatus=pytest.ExitCode.OK)

    tests_conftest.pytest_sessionfinish(session, pytest.ExitCode.OK)

    assert session.exitstatus == pytest.ExitCode.OK


def test_sessionfinish_fails_when_skips_exist_in_ci(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CI", "true")
    session = _build_session(skipped_count=1, exitstatus=pytest.ExitCode.OK)

    tests_conftest.pytest_sessionfinish(session, pytest.ExitCode.OK)

    assert session.exitstatus == pytest.ExitCode.TESTS_FAILED


def test_sessionfinish_keeps_status_when_no_skips_in_ci(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("CI", "true")
    session = _build_session(skipped_count=0, exitstatus=pytest.ExitCode.OK)

    tests_conftest.pytest_sessionfinish(session, pytest.ExitCode.OK)

    assert session.exitstatus == pytest.ExitCode.OK
