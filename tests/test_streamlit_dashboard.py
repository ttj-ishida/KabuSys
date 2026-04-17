"""tests/test_streamlit_dashboard.py — Streamlit ダッシュボード テスト"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db


@pytest.fixture
def mon_conn():
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    return conn


def test_load_positions_empty(mon_conn):
    """positions が空の場合は空リストを返す"""
    from kabusys.monitoring.streamlit_dashboard import load_positions

    result = load_positions(mon_conn)
    assert result == []


def test_load_positions_returns_nonzero_qty_only(mon_conn):
    """qty != 0 のみ返す"""
    from kabusys.monitoring.streamlit_dashboard import load_positions

    db = MonitoringDB(mon_conn)
    db.upsert_position(code="7203", qty=100, avg_price=1000.0)
    db.upsert_position(code="6758", qty=0, avg_price=2000.0)  # 除外

    result = load_positions(mon_conn)

    assert len(result) == 1
    assert result[0]["code"] == "7203"


def test_load_recent_orders_empty(mon_conn):
    """trade_logs が空の場合は空リストを返す"""
    from kabusys.monitoring.streamlit_dashboard import load_recent_orders

    result = load_recent_orders(mon_conn)
    assert result == []


def test_load_recent_orders_limit(mon_conn):
    """limit=3 を指定すると最大3件返す"""
    from kabusys.monitoring.streamlit_dashboard import load_recent_orders

    db = MonitoringDB(mon_conn)
    for i in range(5):
        db.log_trade_event(
            event_type="ORDER_CREATED",
            client_order_id=f"order-{i}",
            code="7203",
            side="buy",
            qty=100,
            price=1000.0,
        )

    result = load_recent_orders(mon_conn, limit=3)
    assert len(result) == 3


def test_load_latest_system_status_none(mon_conn):
    """system_status が空の場合は None を返す"""
    from kabusys.monitoring.streamlit_dashboard import load_latest_system_status

    result = load_latest_system_status(mon_conn)
    assert result is None


def test_load_latest_system_status_returns_latest(mon_conn):
    """system_status が複数行あっても最新の1件のみ返す"""
    from kabusys.monitoring.streamlit_dashboard import load_latest_system_status

    db = MonitoringDB(mon_conn)
    older = datetime(2026, 4, 1, 9, 0, tzinfo=timezone.utc)
    newer = datetime(2026, 4, 1, 9, 1, tzinfo=timezone.utc)
    db.log_system_status(10.0, 50.0, 40.0, True, recorded_at=older)
    db.log_system_status(90.0, 80.0, 70.0, False, recorded_at=newer)

    result = load_latest_system_status(mon_conn)

    assert result is not None
    assert result["cpu_percent"] == pytest.approx(90.0)


def test_load_recent_risk_logs_empty(mon_conn):
    """risk_logs が空の場合は空リストを返す"""
    from kabusys.monitoring.streamlit_dashboard import load_recent_risk_logs

    result = load_recent_risk_logs(mon_conn)
    assert result == []
