from contextlib import contextmanager

from psycopg2.extras import Json

from app.services.data.managers.experiment_manager import ExperimentManager


class FakeCursor:
    def __init__(self, *, fetchone_results=None):
        self._fetchone_results = list(fetchone_results or [])
        self.executed = []

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        if not self._fetchone_results:
            return None
        return self._fetchone_results.pop(0)


def _patch_db_context(monkeypatch, manager, cursor):
    def fake_get_db_context():
        @contextmanager
        def _ctx():
            yield None, cursor

        return _ctx()

    monkeypatch.setattr(manager, "get_db_context", fake_get_db_context)


def test_create_thread_insert_omits_mode_column(monkeypatch) -> None:
    manager = ExperimentManager()
    cursor = FakeCursor(
        fetchone_results=[
            {
                "id": "thread-1",
                "title": "Weeknight curry",
                "metadata": {"orchestration": "langgraph-ready"},
                "created_by_user_id": "user-123",
                "created_at": None,
                "updated_at": None,
            }
        ]
    )
    _patch_db_context(monkeypatch, manager, cursor)

    thread = manager.create_thread(
        title="Weeknight curry",
        metadata={"orchestration": "langgraph-ready"},
        created_by_user_id="user-123",
    )

    assert thread["id"] == "thread-1"
    query, params = cursor.executed[0]
    assert "INSERT INTO experiment_threads" in query
    assert "mode" not in query
    assert len(params) == 3
    assert params[0] == "Weeknight curry"
    assert isinstance(params[1], Json)
    assert params[1].adapted == {"orchestration": "langgraph-ready"}
    assert params[2] == "user-123"
