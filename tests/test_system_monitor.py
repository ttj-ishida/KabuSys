"""SystemMonitor 単体テスト（Issue #37）"""
from __future__ import annotations

import os
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kabusys.monitoring.system_monitor import SystemCheckResult, SystemMonitor


@pytest.fixture
def monitor(monitoring_conn, duckdb_prices_conn, tmp_path):
    pid_file = tmp_path / "execution.pid"
    return SystemMonitor(monitoring_conn, duckdb_prices_conn, pid_file=pid_file)


class TestCheckOnce:

    def test_healthy_system_writes_db(self, monitor, monitoring_conn):
        """check_once() 後に system_status に1行書き込まれる"""
        with patch("psutil.cpu_percent", return_value=30.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=50.0)
            mock_disk.return_value = MagicMock(percent=60.0)
            monitor.check_once(today=date(2026, 3, 31))

        count = monitoring_conn.execute(
            "SELECT COUNT(*) FROM system_status"
        ).fetchone()[0]
        assert count == 1

    def test_returns_correct_result_fields(self, monitor):
        """SystemCheckResult の全フィールドが存在し型が正しい"""
        with patch("psutil.cpu_percent", return_value=30.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=50.0)
            mock_disk.return_value = MagicMock(percent=60.0)
            result = monitor.check_once(today=date(2026, 3, 31))

        assert isinstance(result, SystemCheckResult)
        assert isinstance(result.recorded_at, str)
        assert isinstance(result.cpu_percent, float)
        assert isinstance(result.memory_percent, float)
        assert isinstance(result.disk_percent, float)
        assert isinstance(result.process_ok, bool)
        assert isinstance(result.data_freshness_ok, bool)
        assert isinstance(result.stale_pid_detected, bool)
