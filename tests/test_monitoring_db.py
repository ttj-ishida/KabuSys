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


class TestLogTradeEvent:

    def test_appends_row_with_correct_fields(self, mdb, monitoring_conn):
        """全フィールドが正しく保存される"""
        ts = datetime(2026, 3, 30, 9, 0, 0, tzinfo=timezone.utc)
        mdb.log_trade_event(
            event_type="filled",
            client_order_id="order-001",
            code="1234",
            side="buy",
            qty=100,
            price=1500.0,
            filled_qty=100,
            state="filled",
            logged_at=ts,
        )
        row = monitoring_conn.execute(
            "SELECT * FROM trade_logs WHERE client_order_id = 'order-001'"
        ).fetchone()
        assert row["event_type"] == "filled"
        assert row["code"] == "1234"
        assert row["qty"] == 100
        assert row["price"] == 1500.0
        assert row["filled_qty"] == 100
        assert row["state"] == "filled"

    def test_market_order_price_defaults_to_zero(self, mdb, monitoring_conn):
        """成行注文は price=0.0 で記録できる（order_repository.py と同規約）"""
        mdb.log_trade_event(
            event_type="order_created",
            client_order_id="order-002",
            code="5678",
            side="buy",
            qty=100,
            price=0.0,
            state="created",
        )
        row = monitoring_conn.execute(
            "SELECT price FROM trade_logs WHERE client_order_id = 'order-002'"
        ).fetchone()
        assert row[0] == 0.0


class TestUpsertPosition:

    def test_insert_new_position(self, mdb, monitoring_conn):
        """新規 code が挿入される"""
        mdb.upsert_position("1234", 100, 1500.0)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM positions"
        ).fetchone()[0]
        assert count == 1

    def test_update_existing_position(self, mdb, monitoring_conn):
        """同一 code を2回 upsert すると上書きされる（行数は1のまま）"""
        mdb.upsert_position("1234", 100, 1500.0)
        mdb.upsert_position("1234", 50, 1600.0)
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM positions"
        ).fetchone()[0]
        assert count == 1
        row = monitoring_conn.execute(
            "SELECT qty, avg_price FROM positions WHERE code = '1234'"
        ).fetchone()
        assert row[0] == 50
        assert row[1] == 1600.0

    def test_delete_position(self, mdb, monitoring_conn):
        """`delete_position` 後にその code は取得されない"""
        mdb.upsert_position("1234", 100, 1500.0)
        mdb.delete_position("1234")
        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM positions WHERE code = '1234'"
        ).fetchone()[0]
        assert count == 0


class TestLogRiskEvent:

    def test_appends_row(self, mdb, monitoring_conn):
        """全フィールドが正しく保存される"""
        ts = datetime(2026, 3, 30, 9, 0, 0, tzinfo=timezone.utc)
        mdb.log_risk_event(
            event_type="drawdown_warning",
            metric_name="drawdown_pct",
            metric_value=5.5,
            threshold=5.0,
            detail='{"portfolio_value": 9450000}',
            logged_at=ts,
        )
        row = monitoring_conn.execute("SELECT * FROM risk_logs").fetchone()
        assert row["event_type"] == "drawdown_warning"
        assert row["metric_name"] == "drawdown_pct"
        assert row["metric_value"] == 5.5
        assert row["threshold"] == 5.0
        assert row["detail"] == '{"portfolio_value": 9450000}'

    def test_detail_can_be_none(self, mdb, monitoring_conn):
        """`detail` は NULL 可"""
        mdb.log_risk_event("circuit_breaker", "api_error_count", 3.0, 3.0)
        row = monitoring_conn.execute("SELECT detail FROM risk_logs").fetchone()
        assert row[0] is None
