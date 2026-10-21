"""Database initialisation is safe to repeat and to run concurrently.

Postgres itself is not available in the test environment, so the Postgres side is
checked with a recording fake connection (it proves WHICH statements run and in
what order, not how a real server behaves). The SQLite side is real.
"""

import os
import sqlite3
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import memory.database as database  # noqa: E402
from config import settings  # noqa: E402
from memory import db_backend  # noqa: E402


class _FakeCursor:
    def __init__(self, log):
        self.log = log

    def execute(self, sql, params=()):
        self.log.append(" ".join(sql.split()))
        return self

    def fetchall(self):
        return []

    def fetchone(self):
        return None


class _FakeConn:
    def __init__(self, log):
        self.log = log

    def cursor(self):
        return _FakeCursor(self.log)

    def commit(self):
        self.log.append("COMMIT")

    def close(self):
        pass


def test_postgres_init_takes_an_advisory_lock_before_any_ddl(monkeypatch):
    log = []
    monkeypatch.setattr(db_backend, "IS_POSTGRES", True)
    monkeypatch.setattr(database, "get_connection", lambda: _FakeConn(log))
    database.init_db()
    assert log[0] == "SELECT pg_advisory_xact_lock(7266301)"
    assert any(s.startswith("CREATE TABLE IF NOT EXISTS app_config") for s in log)
    assert log.index("SELECT pg_advisory_xact_lock(7266301)") < log.index(
        next(s for s in log if s.startswith("CREATE TABLE IF NOT EXISTS app_config"))
    )
    assert log[-1] == "COMMIT"  # the xact lock is released by this commit


def test_sqlite_init_never_runs_postgres_only_sql(monkeypatch):
    log = []
    monkeypatch.setattr(db_backend, "IS_POSTGRES", False)
    monkeypatch.setattr(database, "get_connection", lambda: _FakeConn(log))
    database.init_db()
    assert not any("pg_advisory" in s for s in log)


@pytest.fixture
def sqlite_file(tmp_path, monkeypatch):
    path = str(tmp_path / "init_test.db")
    monkeypatch.setattr(settings, "db_path", path)
    monkeypatch.setattr(db_backend, "IS_POSTGRES", False)
    return path


def test_init_is_repeatable_and_keeps_app_config(sqlite_file):
    database.init_db()
    database.set_app_config("inference_mode", "local")
    database.init_db()  # a warm restart must not disturb stored settings
    database.init_db()
    assert database.get_app_config() == {"inference_mode": "local"}
    tables = {r[0] for r in sqlite3.connect(sqlite_file).execute("select name from sqlite_master where type='table'")}
    assert "app_config" in tables


def test_concurrent_cold_starts_on_sqlite(sqlite_file):
    errors = []

    def start():
        try:
            database.init_db()
        except Exception as exc:  # noqa: BLE001
            errors.append(repr(exc))

    threads = [threading.Thread(target=start) for _ in range(8)]
    [t.start() for t in threads]
    [t.join(timeout=60) for t in threads]
    assert errors == []
    database.set_app_config("k", "v")
    assert database.get_app_config()["k"] == "v"


def test_app_config_set_replaces_and_none_removes(sqlite_file):
    database.init_db()
    database.set_app_config("a", "1")
    database.set_app_config("a", "2")
    assert database.get_app_config() == {"a": "2"}
    database.set_app_config("a", None)
    assert database.get_app_config() == {}
