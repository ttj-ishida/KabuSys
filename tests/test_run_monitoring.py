# tests/test_run_monitoring.py
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from kabusys.run_monitoring import _get_poll_interval


def _make_settings():
    settings = MagicMock()
    settings.sqlite_path = Path("/prod.db")
    settings.duckdb_path = Path("/data.duckdb")
    settings.pid_file_path = Path("/data/execution.pid")
    settings.env = "development"
    return settings


def _run_main():
    """全依存をモックして main() を実行するヘルパー。time.sleep で1回ループ後に終了。"""
    mock_monitor = MagicMock()

    with (
        patch("kabusys.run_monitoring.set_process_priority") as mock_priority,
        patch("kabusys.run_monitoring.Settings") as mock_settings_cls,
        patch("kabusys.run_monitoring.sqlite3.connect") as mock_sqlite,
        patch("kabusys.run_monitoring.init_monitoring_db"),
        patch("kabusys.run_monitoring.duckdb.connect"),
        patch("kabusys.run_monitoring.SystemMonitor", return_value=mock_monitor),
        patch("kabusys.run_monitoring.time.sleep", side_effect=KeyboardInterrupt),
    ):
        mock_settings_cls.return_value = _make_settings()

        from kabusys.run_monitoring import main

        main()

    return mock_priority, mock_sqlite, mock_monitor


class TestRunMonitoringMain:
    def test_sets_high_priority_first(self):
        mock_priority, _, _ = _run_main()
        mock_priority.assert_called_once_with("high")

    def test_calls_check_once(self):
        _, _, mock_monitor = _run_main()
        mock_monitor.check_once.assert_called()

    def test_uses_sqlite_path(self):
        _, mock_sqlite, _ = _run_main()
        settings = _make_settings()
        mock_sqlite.assert_called_once_with(str(settings.sqlite_path))


def test_run_monitoring_stops_on_flag(tmp_path):
    """停止フラグが存在するとき監視ループが終了することを確認する。"""
    import kabusys.run_monitoring as rm_mod

    stop_flag = tmp_path / "stop.flag"
    stop_flag.touch()

    with (
        patch.object(rm_mod, "_STOP_FLAG", stop_flag),
        patch("kabusys.run_monitoring.set_process_priority"),
        patch("kabusys.run_monitoring.Settings", return_value=_make_settings()),
        patch("kabusys.run_monitoring.sqlite3.connect"),
        patch("kabusys.run_monitoring.init_monitoring_db"),
        patch("kabusys.run_monitoring.duckdb.connect"),
        patch("kabusys.run_monitoring.SystemMonitor"),
    ):
        rm_mod.main()  # フラグがあるのでループせずに終了するはず


class TestGetPollInterval:
    def test_default(self, monkeypatch):
        monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
        assert _get_poll_interval() == 60

    def test_override(self, monkeypatch):
        monkeypatch.setenv("MONITOR_POLL_INTERVAL", "30")
        assert _get_poll_interval() == 30

    def test_invalid_uses_default(self, monkeypatch, caplog):
        monkeypatch.setenv("MONITOR_POLL_INTERVAL", "abc")
        with caplog.at_level(logging.WARNING, logger="kabusys.run_monitoring"):
            result = _get_poll_interval()
        assert result == 60
        assert "不正" in caplog.text

    def test_zero_uses_default(self, monkeypatch, caplog):
        monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
        with caplog.at_level(logging.WARNING, logger="kabusys.run_monitoring"):
            result = _get_poll_interval()
        assert result == 60
        assert "不正" in caplog.text

    def test_negative_uses_default(self, monkeypatch, caplog):
        monkeypatch.setenv("MONITOR_POLL_INTERVAL", "-10")
        with caplog.at_level(logging.WARNING, logger="kabusys.run_monitoring"):
            result = _get_poll_interval()
        assert result == 60
        assert "不正" in caplog.text
