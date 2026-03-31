"""tests/test_monitoring_engine.py — Phase 7 監視エンジン テスト"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kabusys.monitoring.monitoring_db import MonitoringDB, init_monitoring_db


# ─── Fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def mon_conn():
    """インメモリ monitoring.db。"""
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    return conn


@pytest.fixture
def mock_duckdb():
    return MagicMock()


# ─── SystemMonitor ────────────────────────────────────────────────────────────

def _make_psutil_mocks():
    """psutil の cpu/mem/disk を固定値でモックするパッチ群を返す。"""
    return [
        patch("psutil.cpu_percent", return_value=30.0),
        patch("psutil.virtual_memory", return_value=MagicMock(percent=50.0)),
        patch("psutil.disk_usage", return_value=MagicMock(percent=40.0)),
    ]


def test_system_monitor_no_pid_file(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルなし → process_ok=False, stale_pid_detected=False"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=date.today())
        finally:
            for p in patches:
                p.stop()

    assert result.process_ok is False
    assert result.stale_pid_detected is False


def test_system_monitor_pid_alive(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルあり + プロセス生存 → process_ok=True, stale_pid_detected=False"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    pid_file = tmp_path / "execution.pid"
    pid_file.write_text("12345")
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()), \
         patch("psutil.pid_exists", return_value=True):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=date.today())
        finally:
            for p in patches:
                p.stop()

    assert result.process_ok is True
    assert result.stale_pid_detected is False
    assert pid_file.exists()  # ファイルは残る


def test_system_monitor_stale_pid(mon_conn, mock_duckdb, tmp_path):
    """PID ファイルあり + プロセス死亡 → stale_pid_detected=True, ファイル削除, risk_log記録"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    pid_file = tmp_path / "execution.pid"
    pid_file.write_text("12345")
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=date.today()), \
         patch("psutil.pid_exists", return_value=False):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=date.today())
        finally:
            for p in patches:
                p.stop()

    assert result.process_ok is False
    assert result.stale_pid_detected is True
    assert not pid_file.exists()  # ファイルが削除される

    # risk_logs に STALE_PID が記録されているか確認
    mon_conn.row_factory = sqlite3.Row
    rows = mon_conn.execute("SELECT * FROM risk_logs WHERE event_type='STALE_PID'").fetchall()
    assert len(rows) == 1


def test_system_monitor_data_freshness_ok(mon_conn, mock_duckdb, tmp_path):
    """株価データが 2 日前 → data_freshness_ok=True"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    today = date(2026, 4, 1)
    last_price = date(2026, 3, 30)  # 2日前
    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=last_price):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=today)
        finally:
            for p in patches:
                p.stop()

    assert result.data_freshness_ok is True


def test_system_monitor_data_freshness_ng(mon_conn, mock_duckdb, tmp_path):
    """株価データが 4 日前 → data_freshness_ok=False"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    today = date(2026, 4, 1)
    last_price = date(2026, 3, 28)  # 4日前
    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=last_price):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=today)
        finally:
            for p in patches:
                p.stop()

    assert result.data_freshness_ok is False


def test_system_monitor_data_freshness_none(mon_conn, mock_duckdb, tmp_path):
    """get_last_price_date が None（空 DuckDB）→ data_freshness_ok=False"""
    from kabusys.monitoring.system_monitor import SystemMonitor

    pid_file = tmp_path / "execution.pid"
    monitor = SystemMonitor(mon_conn, mock_duckdb, pid_file=pid_file)

    with patch("kabusys.monitoring.system_monitor.get_last_price_date", return_value=None):
        patches = _make_psutil_mocks()
        for p in patches:
            p.start()
        try:
            result = monitor.check_once(today=date.today())
        finally:
            for p in patches:
                p.stop()

    assert result.data_freshness_ok is False
