"""intraday_collector のユニットテスト（インメモリ SQLite + tmp_path）"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pytest

from kabusys.monitoring.monitoring_db import init_monitoring_db
from kabusys.operations.intraday_collector import (
    check_pid_file,
    check_kill_switch,
    get_dashboard_row,
    count_recent_risk_events,
    get_latest_system_status,
    get_recent_risk_events,
    collect_intraday_snapshot,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_monitoring_db(c)
    yield c
    c.close()


def _insert_risk_event(conn, event_type: str, minutes_ago: int):
    ts = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)).isoformat()
    conn.execute(
        "INSERT INTO risk_logs (event_type, metric_name, metric_value, threshold, detail, logged_at)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (event_type, "test_metric", 0.0, 0.0, "test", ts),
    )
    conn.commit()


# --- check_pid_file ---


def test_check_pid_file_false_when_missing(tmp_path):
    assert check_pid_file(tmp_path / "no.pid") is False


def test_check_pid_file_true_for_current_process(tmp_path):
    pid_file = tmp_path / "proc.pid"
    pid_file.write_text(str(os.getpid()))
    assert check_pid_file(pid_file) is True


def test_check_pid_file_false_when_stale_pid(tmp_path):
    pid_file = tmp_path / "stale.pid"
    pid_file.write_text("999999999")
    assert check_pid_file(pid_file) is False


# --- check_kill_switch ---


def test_check_kill_switch_inactive(tmp_path):
    active, reason = check_kill_switch(tmp_path / "kill.flag")
    assert active is False
    assert reason == ""


def test_check_kill_switch_active(tmp_path):
    flag = tmp_path / "kill.flag"
    flag.write_text("Max drawdown exceeded")
    active, reason = check_kill_switch(flag)
    assert active is True
    assert reason == "Max drawdown exceeded"


# --- get_dashboard_row ---


def test_get_dashboard_row_none_when_empty(conn):
    assert get_dashboard_row(conn) is None


def test_get_dashboard_row_returns_drawdown(conn):
    from kabusys.monitoring.monitoring_db import MonitoringDB

    db = MonitoringDB(conn)
    db.upsert_dashboard(
        portfolio_value=1_000_000,
        cash=500_000,
        drawdown_pct=-0.05,
        open_order_count=0,
        position_count=0,
    )
    row = get_dashboard_row(conn)
    assert row is not None
    assert abs(row["drawdown_pct"] - (-0.05)) < 1e-9


# --- count_recent_risk_events ---


def test_count_recent_risk_events_zero_when_empty(conn):
    assert count_recent_risk_events(conn, "STALE_ORDER") == 0


def test_count_recent_risk_events_within_window(conn):
    _insert_risk_event(conn, "STALE_ORDER", 30)
    _insert_risk_event(conn, "STALE_ORDER", 10)
    assert count_recent_risk_events(conn, "STALE_ORDER") == 2


def test_count_recent_risk_events_ignores_old(conn):
    _insert_risk_event(conn, "STALE_ORDER", 90)
    assert count_recent_risk_events(conn, "STALE_ORDER") == 0


def test_count_recent_risk_events_ignores_other_type(conn):
    _insert_risk_event(conn, "ORDER_ERROR", 5)
    assert count_recent_risk_events(conn, "STALE_ORDER") == 0


# --- get_latest_system_status ---


def test_get_latest_system_status_none_when_empty(conn):
    assert get_latest_system_status(conn) is None


def test_get_latest_system_status_returns_latest(conn):
    from kabusys.monitoring.monitoring_db import MonitoringDB

    db = MonitoringDB(conn)
    db.log_system_status(40.0, 50.0, 60.0, True)
    db.log_system_status(80.0, 70.0, 60.0, True)
    row = get_latest_system_status(conn)
    assert row is not None
    assert abs(row["cpu_percent"] - 80.0) < 1e-9


# --- get_recent_risk_events ---


def test_get_recent_risk_events_empty(conn):
    assert get_recent_risk_events(conn) == []


def test_get_recent_risk_events_limit(conn):
    for i in range(5):
        _insert_risk_event(conn, "ORDER_ERROR", i)
    assert len(get_recent_risk_events(conn, limit=3)) == 3


# --- collect_intraday_snapshot ---


class FakeSettings:
    def __init__(self, pid_file_path: Path, kill_flag_path: Path):
        self.pid_file_path = pid_file_path
        self.kill_flag_path = kill_flag_path
        self.sqlite_path = Path("data/monitoring.db")


def test_collect_intraday_snapshot_all_ok(conn, tmp_path):
    from kabusys.monitoring.monitoring_db import MonitoringDB

    pid_file = tmp_path / "execution.pid"
    pid_file.write_text(str(os.getpid()))
    kill_flag = tmp_path / "kill.flag"

    settings = FakeSettings(pid_file_path=pid_file, kill_flag_path=kill_flag)

    db = MonitoringDB(conn)
    db.upsert_dashboard(
        portfolio_value=1_000_000,
        cash=500_000,
        drawdown_pct=-0.02,
        open_order_count=0,
        position_count=0,
    )
    db.log_system_status(30.0, 50.0, 60.0, True)

    snap = collect_intraday_snapshot(conn, settings)
    assert snap.execution_pid_ok is True
    assert snap.kill_switch_active is False
    assert snap.kill_switch_reason == ""
    assert snap.drawdown_pct is not None
    assert snap.process_ok is True


def test_collect_intraday_snapshot_kill_switch_active(conn, tmp_path):
    pid_file = tmp_path / "execution.pid"
    kill_flag = tmp_path / "kill.flag"
    kill_flag.write_text("Max drawdown exceeded")

    settings = FakeSettings(pid_file_path=pid_file, kill_flag_path=kill_flag)

    snap = collect_intraday_snapshot(conn, settings)
    assert snap.kill_switch_active is True
    assert snap.kill_switch_reason == "Max drawdown exceeded"


def test_collect_intraday_snapshot_no_db_data(conn, tmp_path):
    settings = FakeSettings(
        pid_file_path=tmp_path / "no.pid",
        kill_flag_path=tmp_path / "no.flag",
    )

    snap = collect_intraday_snapshot(conn, settings)
    assert snap.drawdown_pct is None
    assert snap.process_ok is True
