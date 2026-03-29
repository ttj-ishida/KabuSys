"""MonitoringDB 単体テスト（Issue #36）"""
import sqlite3
from datetime import datetime, timezone, timedelta

import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db


@pytest.fixture
def mdb(monitoring_conn):
    return MonitoringDB(monitoring_conn)


class TestInitMonitoringDb:

    def test_tables_created_idempotently(self, monitoring_conn):
        """init_monitoring_db を2回呼んでもエラーなし、5テーブルが存在する"""
        init_monitoring_db(monitoring_conn)  # 2回目の呼び出し
        tables = {
            row[0]
            for row in monitoring_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
        }
        assert {"system_status", "trade_logs", "positions", "risk_logs", "dashboard"}.issubset(tables)


class TestLogSystemStatus:

    def test_appends_row(self, mdb, monitoring_conn):
        """2回呼ぶと2行追記される"""
        mdb.log_system_status(50.0, 60.0, 70.0, True)
        mdb.log_system_status(55.0, 65.0, 75.0, False)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM system_status"
        ).fetchone()[0]
        assert count == 2

    def test_default_recorded_at_is_utc_now(self, mdb, monitoring_conn):
        """`recorded_at` 省略時に ISO8601 UTC 文字列が入り、now との差が5秒以内"""
        before = datetime.now(timezone.utc)
        mdb.log_system_status(50.0, 60.0, 70.0, True)
        after = datetime.now(timezone.utc)
        row = monitoring_conn.execute(
            "SELECT recorded_at FROM system_status"
        ).fetchone()
        recorded = datetime.fromisoformat(row[0])
        assert before - timedelta(seconds=5) <= recorded <= after + timedelta(seconds=5)
