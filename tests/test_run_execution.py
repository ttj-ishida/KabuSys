# tests/test_run_execution.py
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

import kabusys.run_execution as re_mod
from kabusys.run_execution import main


def _run_main(is_paper: bool = False):
    """全依存をモックして main() を実行するヘルパー。"""
    mock_broker = MagicMock()
    mock_broker.get_available_cash.return_value = 10_000_000.0
    mock_engine = MagicMock()

    with patch("kabusys.run_execution.set_process_priority") as mock_priority, \
         patch("kabusys.run_execution.Settings") as mock_settings_cls, \
         patch("kabusys.run_execution.sqlite3.connect") as mock_sqlite, \
         patch("kabusys.run_execution.init_monitoring_db"), \
         patch("kabusys.run_execution.duckdb.connect"), \
         patch("kabusys.run_execution.BrokerClientFactory.create", return_value=mock_broker), \
         patch("kabusys.run_execution.OrderRepository"), \
         patch("kabusys.run_execution.OrderManager"), \
         patch("kabusys.run_execution.RiskManager"), \
         patch("kabusys.run_execution.Reconciler"), \
         patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine):

        settings = MagicMock()
        settings.is_paper = is_paper
        settings.paper_sqlite_path = Path("/paper.db")
        settings.sqlite_path = Path("/prod.db")
        settings.duckdb_path = Path("/data.duckdb")
        settings.pid_file_path = Path("/data/execution.pid")
        mock_settings_cls.return_value = settings

        main()

    return mock_priority, mock_sqlite, mock_engine, settings


class TestRunExecutionMain:
    def test_sets_high_priority_first(self):
        mock_priority, _, _, _ = _run_main()
        mock_priority.assert_called_once_with("high")

    def test_paper_mode_uses_paper_sqlite_path(self):
        _, mock_sqlite, _, settings = _run_main(is_paper=True)
        mock_sqlite.assert_called_once_with(str(settings.paper_sqlite_path))

    def test_dev_mode_uses_sqlite_path(self):
        _, mock_sqlite, _, settings = _run_main(is_paper=False)
        mock_sqlite.assert_called_once_with(str(settings.sqlite_path))

    def test_calls_run_session(self):
        _, _, mock_engine, _ = _run_main()
        mock_engine.run_session.assert_called_once()


def test_run_execution_stops_on_flag(tmp_path):
    """停止フラグが作成されたとき engine.stop() が呼ばれることを確認する。"""
    stop_flag = tmp_path / "stop.flag"
    # フラグを事前に作成（メインループがすぐに検知する）
    stop_flag.touch()

    mock_engine = MagicMock()
    mock_engine.run_session.return_value = None  # ブロックしない

    with patch.object(re_mod, "_STOP_FLAG", stop_flag), \
         patch("kabusys.run_execution.set_process_priority"), \
         patch("kabusys.run_execution.Settings"), \
         patch("kabusys.run_execution.sqlite3.connect"), \
         patch("kabusys.run_execution.init_monitoring_db"), \
         patch("kabusys.run_execution.duckdb.connect"), \
         patch("kabusys.run_execution.BrokerClientFactory.create"), \
         patch("kabusys.run_execution.OrderRepository"), \
         patch("kabusys.run_execution.OrderManager"), \
         patch("kabusys.run_execution.RiskManager"), \
         patch("kabusys.run_execution.Reconciler"), \
         patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine):
        re_mod.main()

    mock_engine.stop.assert_called_once()
