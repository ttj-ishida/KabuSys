"""SystemMonitor 単体テスト（Issue #37）"""
from __future__ import annotations

import os
from datetime import date, datetime as _real_datetime, datetime, timezone
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


class TestProcessCheck:

    def test_no_pid_file_process_ok_false(self, monitor):
        """PID ファイルなし → process_ok=False, stale_pid_detected=False"""
        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = monitor.check_once(today=date(2026, 3, 31))

        assert result.process_ok is False
        assert result.stale_pid_detected is False

    def test_valid_pid_process_ok_true(self, monitor, tmp_path):
        """自プロセスの PID を書いたファイル → process_ok=True"""
        pid_file = tmp_path / "execution.pid"
        pid_file.write_text(str(os.getpid()))
        mon = SystemMonitor(monitor._db._conn, monitor._duckdb_conn, pid_file=pid_file)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=date(2026, 3, 31))

        assert result.process_ok is True
        assert result.stale_pid_detected is False

    def test_stale_pid_detected_and_deleted(self, monitor, tmp_path):
        """存在しない PID → process_ok=False, stale_pid_detected=True, ファイル削除"""
        pid_file = tmp_path / "execution.pid"
        pid_file.write_text("999999999")  # 存在しない PID
        mon = SystemMonitor(monitor._db._conn, monitor._duckdb_conn, pid_file=pid_file)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk, \
             patch("psutil.pid_exists", return_value=False):
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=date(2026, 3, 31))

        assert result.process_ok is False
        assert result.stale_pid_detected is True
        assert not pid_file.exists()


class TestDataFreshness:

    def _make_monitor(self, monitoring_conn, duckdb_prices_conn, tmp_path):
        pid_file = tmp_path / "execution.pid"
        return SystemMonitor(monitoring_conn, duckdb_prices_conn, pid_file=pid_file)

    def test_fresh_data_ok(self, monitoring_conn, duckdb_prices_conn, tmp_path):
        """当日の株価データあり → data_freshness_ok=True"""
        today = date(2026, 3, 31)
        duckdb_prices_conn.execute(
            "INSERT INTO raw_prices (date, code) VALUES (?, ?)",
            [today, "1234"],
        )
        mon = self._make_monitor(monitoring_conn, duckdb_prices_conn, tmp_path)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=today)

        assert result.data_freshness_ok is True

    def test_stale_data_not_ok(self, monitoring_conn, duckdb_prices_conn, tmp_path):
        """4日以上古い株価データ → data_freshness_ok=False"""
        today = date(2026, 3, 31)
        stale_date = date(2026, 3, 27)  # 4日前
        duckdb_prices_conn.execute(
            "INSERT INTO raw_prices (date, code) VALUES (?, ?)",
            [stale_date, "1234"],
        )
        mon = self._make_monitor(monitoring_conn, duckdb_prices_conn, tmp_path)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=today)

        assert result.data_freshness_ok is False

    def test_no_data_not_ok(self, monitoring_conn, duckdb_prices_conn, tmp_path):
        """データなし（空テーブル）→ data_freshness_ok=False"""
        mon = self._make_monitor(monitoring_conn, duckdb_prices_conn, tmp_path)

        with patch("psutil.cpu_percent", return_value=10.0), \
             patch("psutil.virtual_memory") as mock_mem, \
             patch("psutil.disk_usage") as mock_disk:
            mock_mem.return_value = MagicMock(percent=20.0)
            mock_disk.return_value = MagicMock(percent=30.0)
            result = mon.check_once(today=date(2026, 3, 31))

        assert result.data_freshness_ok is False


class _FakeDatetime(_real_datetime):
    """datetime.now() を 08:55 に固定するフェイク。シグナルウィンドウ内に収まる。"""

    @classmethod
    def now(cls, tz=None):
        return _real_datetime(2026, 3, 31, 8, 55, 0)


class TestExecutionEnginePid:

    def _make_engine(self, tmp_path):
        """テスト用 ExecutionEngine を最小モックで構築する。"""
        from datetime import date, time
        from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine

        broker = MagicMock()
        repo = MagicMock()
        risk_manager = MagicMock()
        order_manager = MagicMock()
        duckdb_conn = MagicMock()
        cfg = EngineConfig(
            target_date=date(2026, 3, 31),
            signal_send_start=time(8, 50),
            signal_send_end=time(9, 10),
            market_close=time(15, 30),
        )
        pid_file = tmp_path / "execution.pid"
        return ExecutionEngine(
            broker, repo, risk_manager, order_manager, duckdb_conn, cfg,
            pid_file=pid_file,
        ), pid_file

    def test_pid_file_written_on_start(self, tmp_path):
        """run_session() 開始時に PID ファイルが生成される"""
        engine, pid_file = self._make_engine(tmp_path)
        pid_existed_during = []

        def capture_and_raise():
            pid_existed_during.append(pid_file.exists())
            raise KeyboardInterrupt

        def drain_and_raise():
            pid_existed_during.append(pid_file.exists())
            raise KeyboardInterrupt

        with patch("datetime.datetime", _FakeDatetime), \
             patch.object(engine, "_process_signals", side_effect=capture_and_raise), \
             patch.object(engine, "_drain_push_queue", side_effect=drain_and_raise), \
             patch.object(engine, "_websocket_worker"):
            with pytest.raises(KeyboardInterrupt):
                engine.run_session()

        assert pid_existed_during[0] is True  # 実行中は PID ファイルが存在した

    def test_pid_file_removed_on_clean_exit(self, tmp_path):
        """finally ブロックで PID ファイルが削除される"""
        engine, pid_file = self._make_engine(tmp_path)

        with patch("datetime.datetime", _FakeDatetime), \
             patch.object(engine, "_process_signals", side_effect=KeyboardInterrupt), \
             patch.object(engine, "_drain_push_queue", side_effect=KeyboardInterrupt), \
             patch.object(engine, "_websocket_worker"):
            with pytest.raises(KeyboardInterrupt):
                engine.run_session()

        # KeyboardInterrupt 後も finally で削除される
        assert not pid_file.exists()
