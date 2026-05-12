# tests/test_process_registry.py
"""process_registry + MonitoringDB.process_runs テスト（Issue #310）"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB


@pytest.fixture
def mdb(monitoring_conn):
    return MonitoringDB(monitoring_conn)


# ---------------------------------------------------------------------------
# MonitoringDB — process_runs メソッド
# ---------------------------------------------------------------------------


class TestStartProcess:
    def test_returns_run_id(self, mdb):
        run_id = mdb.start_process("my_job")
        assert isinstance(run_id, int)
        assert run_id > 0

    def test_row_inserted_with_running_status(self, mdb, monitoring_conn):
        run_id = mdb.start_process("my_job", pid=12345)
        row = monitoring_conn.execute(
            "SELECT job_name, pid, status, finished_at FROM process_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
        assert row is not None
        assert row[0] == "my_job"
        assert row[1] == 12345
        assert row[2] == "running"
        assert row[3] is None

    def test_custom_started_at(self, mdb, monitoring_conn):
        ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        run_id = mdb.start_process("j", started_at=ts)
        row = monitoring_conn.execute(
            "SELECT started_at FROM process_runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert "2025-01-01" in row[0]

    def test_log_file_stored(self, mdb, monitoring_conn):
        run_id = mdb.start_process("j", log_file="logs/foo.log")
        row = monitoring_conn.execute(
            "SELECT log_file FROM process_runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert row[0] == "logs/foo.log"


class TestFinishProcess:
    def test_updates_status_and_finished_at(self, mdb, monitoring_conn):
        run_id = mdb.start_process("j")
        mdb.finish_process(run_id, status="success")
        row = monitoring_conn.execute(
            "SELECT status, finished_at FROM process_runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert row[0] == "success"
        assert row[1] is not None

    def test_failed_status_with_error_msg(self, mdb, monitoring_conn):
        run_id = mdb.start_process("j")
        mdb.finish_process(run_id, status="failed", error_msg="boom")
        row = monitoring_conn.execute(
            "SELECT status, error_msg FROM process_runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert row[0] == "failed"
        assert row[1] == "boom"

    def test_warning_status(self, mdb, monitoring_conn):
        run_id = mdb.start_process("j")
        mdb.finish_process(run_id, status="warning")
        row = monitoring_conn.execute(
            "SELECT status FROM process_runs WHERE id = ?", (run_id,)
        ).fetchone()
        assert row[0] == "warning"


class TestListRecentProcesses:
    def test_includes_running_processes(self, mdb):
        run_id = mdb.start_process("running_job")
        rows = mdb.list_recent_processes(hours=1)
        ids = [r["id"] for r in rows]
        assert run_id in ids

    def test_includes_recently_completed(self, mdb):
        run_id = mdb.start_process("completed_job")
        mdb.finish_process(run_id, status="success")
        rows = mdb.list_recent_processes(hours=24)
        ids = [r["id"] for r in rows]
        assert run_id in ids

    def test_excludes_old_completed(self, mdb, monitoring_conn):
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        monitoring_conn.execute(
            "INSERT INTO process_runs (job_name, started_at, finished_at, status)"
            " VALUES ('old_job', ?, ?, 'success')",
            (old_ts, old_ts),
        )
        monitoring_conn.commit()
        rows = mdb.list_recent_processes(hours=24)
        names = [r["job_name"] for r in rows]
        assert "old_job" not in names

    def test_always_includes_running_regardless_of_age(self, mdb, monitoring_conn):
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=72)).isoformat()
        monitoring_conn.execute(
            "INSERT INTO process_runs (job_name, started_at, status)"
            " VALUES ('old_running', ?, 'running')",
            (old_ts,),
        )
        monitoring_conn.commit()
        rows = mdb.list_recent_processes(hours=24)
        names = [r["job_name"] for r in rows]
        assert "old_running" in names

    def test_returns_dicts(self, mdb):
        mdb.start_process("j")
        rows = mdb.list_recent_processes(hours=24)
        assert all(isinstance(r, dict) for r in rows)

    def test_ordered_started_at_desc(self, mdb):
        id1 = mdb.start_process("first")
        id2 = mdb.start_process("second")
        rows = mdb.list_recent_processes(hours=24)
        ids = [r["id"] for r in rows]
        assert ids.index(id2) < ids.index(id1)


class TestPruneOldProcessRuns:
    def test_deletes_old_completed(self, mdb, monitoring_conn):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        monitoring_conn.execute(
            "INSERT INTO process_runs (job_name, started_at, finished_at, status)"
            " VALUES ('old', ?, ?, 'success')",
            (old_ts, old_ts),
        )
        monitoring_conn.commit()
        deleted = mdb.prune_old_process_runs(days=30)
        assert deleted >= 1
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM process_runs WHERE job_name = 'old'"
        ).fetchone()[0]
        assert count == 0

    def test_keeps_running_even_if_old(self, mdb, monitoring_conn):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        monitoring_conn.execute(
            "INSERT INTO process_runs (job_name, started_at, status)"
            " VALUES ('old_running', ?, 'running')",
            (old_ts,),
        )
        monitoring_conn.commit()
        mdb.prune_old_process_runs(days=30)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM process_runs WHERE job_name = 'old_running'"
        ).fetchone()[0]
        assert count == 1

    def test_keeps_recent_completed(self, mdb):
        run_id = mdb.start_process("recent")
        mdb.finish_process(run_id, status="success")
        mdb.prune_old_process_runs(days=30)
        count = mdb._conn.execute(
            "SELECT COUNT(*) FROM process_runs WHERE id = ?", (run_id,)
        ).fetchone()[0]
        assert count == 1

    def test_returns_deleted_count(self, mdb, monitoring_conn):
        old_ts = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        for _ in range(3):
            monitoring_conn.execute(
                "INSERT INTO process_runs (job_name, started_at, finished_at, status)"
                " VALUES ('x', ?, ?, 'success')",
                (old_ts, old_ts),
            )
        monitoring_conn.commit()
        deleted = mdb.prune_old_process_runs(days=30)
        assert deleted == 3


# ---------------------------------------------------------------------------
# process_registry 関数（SQLite を使う統合テスト）
# ---------------------------------------------------------------------------


class TestProcessRegistryFunctions:
    def test_register_and_update(self, tmp_path, monkeypatch):
        db_path = tmp_path / "monitoring.db"
        monkeypatch.setattr(
            "kabusys.operations.process_registry.Settings",
            lambda: type("S", (), {"sqlite_path": db_path})(),
        )

        from kabusys.operations.process_registry import register_process, update_process

        run_id = register_process("test_job", log_file="logs/test.log")
        assert isinstance(run_id, int)

        # DB にレコードが存在する
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM process_runs WHERE id = ?", (run_id,)).fetchone()
        assert row["job_name"] == "test_job"
        assert row["status"] == "running"
        assert row["log_file"] == "logs/test.log"
        conn.close()

        # update_process で完了に変わる
        update_process(run_id, status="success")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM process_runs WHERE id = ?", (run_id,)).fetchone()
        assert row["status"] == "success"
        assert row["finished_at"] is not None
        conn.close()

    def test_update_process_failed_with_error_msg(self, tmp_path, monkeypatch):
        db_path = tmp_path / "monitoring.db"
        monkeypatch.setattr(
            "kabusys.operations.process_registry.Settings",
            lambda: type("S", (), {"sqlite_path": db_path})(),
        )

        from kabusys.operations.process_registry import register_process, update_process

        run_id = register_process("fail_job")
        update_process(run_id, status="failed", error_msg="oops")

        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        row = conn.execute("SELECT * FROM process_runs WHERE id = ?", (run_id,)).fetchone()
        assert row["status"] == "failed"
        assert row["error_msg"] == "oops"
        conn.close()

    def test_list_processes(self, tmp_path, monkeypatch):
        db_path = tmp_path / "monitoring.db"
        monkeypatch.setattr(
            "kabusys.operations.process_registry.Settings",
            lambda: type("S", (), {"sqlite_path": db_path})(),
        )

        from kabusys.operations.process_registry import (
            list_processes,
            register_process,
            update_process,
        )

        run_id = register_process("list_job")
        update_process(run_id, status="success")

        rows = list_processes(hours=24)
        assert any(r["job_name"] == "list_job" for r in rows)


# ---------------------------------------------------------------------------
# is_pid_alive
# ---------------------------------------------------------------------------


class TestIsPidAlive:
    def test_current_pid_is_alive(self):
        import os

        from kabusys.operations.process_registry import is_pid_alive

        assert is_pid_alive(os.getpid()) is True

    def test_nonexistent_pid_is_dead(self):
        from kabusys.operations.process_registry import is_pid_alive

        assert is_pid_alive(999999999) is False
