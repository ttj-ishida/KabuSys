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
