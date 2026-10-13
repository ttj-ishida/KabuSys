# tests/test_run_execution.py
from datetime import date, time
from pathlib import Path
from unittest.mock import MagicMock, patch

import duckdb
import pytest
import yaml as yaml_mod

import kabusys.run_execution as re_mod
from kabusys.execution.broker_api import Position
from kabusys.execution.reconciler import ReconcileResult
from kabusys.execution.risk_manager import RiskConfig
from kabusys.run_execution import main


def _make_reconciler_mock() -> MagicMock:
    """ReconcileResult を正しく返す Reconciler クラスモックを生成する。"""
    mock_reconciler_cls = MagicMock()
    mock_reconciler_instance = MagicMock()
    mock_reconciler_instance.run.return_value = ReconcileResult()
    mock_reconciler_cls.return_value = mock_reconciler_instance
    return mock_reconciler_cls


def _run_main(is_paper: bool = False):
    """全依存をモックして main() を実行するヘルパー。"""
    mock_broker = MagicMock()
    mock_broker.get_available_cash.return_value = 10_000_000.0
    mock_broker.get_positions.return_value = []
    mock_engine = MagicMock()

    with (
        patch("kabusys.run_execution.set_process_priority") as mock_priority,
        patch("kabusys.run_execution.Settings") as mock_settings_cls,
        patch("kabusys.run_execution.sqlite3.connect") as mock_sqlite,
        patch("kabusys.run_execution.init_monitoring_db"),
        patch("kabusys.run_execution.duckdb.connect"),
        patch("kabusys.run_execution.BrokerClientFactory.create", return_value=mock_broker),
        patch("kabusys.run_execution.OrderRepository"),
        patch("kabusys.run_execution.OrderManager"),
        patch("kabusys.run_execution.RiskManager"),
        patch("kabusys.run_execution.Reconciler", _make_reconciler_mock()),
        patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine),
        patch("kabusys.run_execution._load_risk_config", return_value=MagicMock()),
    ):
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
    def test_env_time_override(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_SIGNAL_SEND_END", "15:30")
        assert re_mod._env_time("KABUSYS_SIGNAL_SEND_END", time(9, 10)) == time(15, 30)

    def test_sets_high_priority_first(self):
        mock_priority, _, _, _ = _run_main()
        mock_priority.assert_called_once_with("high")

    def test_paper_mode_uses_paper_sqlite_path(self):
        _, mock_sqlite, _, settings = _run_main(is_paper=True)
        paths_called = [c.args[0] for c in mock_sqlite.call_args_list if c.args]
        assert str(settings.paper_sqlite_path) in paths_called

    def test_dev_mode_uses_sqlite_path(self):
        _, mock_sqlite, _, settings = _run_main(is_paper=False)
        paths_called = [c.args[0] for c in mock_sqlite.call_args_list if c.args]
        assert str(settings.sqlite_path) in paths_called

    def test_calls_run_session(self):
        _, _, mock_engine, _ = _run_main()
        mock_engine.run_session.assert_called_once()

    def test_initial_portfolio_value_includes_positions(self):
        mock_broker = MagicMock()
        mock_broker.get_available_cash.return_value = 1_000_000.0
        mock_broker.get_positions.return_value = [
            Position(code="1234", qty=100, avg_price=2000.0, current_price=2500.0),
            # 100 * 2500 = 250_000
        ]
        mock_engine = MagicMock()

        with (
            patch("kabusys.run_execution.set_process_priority"),
            patch("kabusys.run_execution.Settings") as mock_settings_cls,
            patch("kabusys.run_execution.sqlite3.connect"),
            patch("kabusys.run_execution.init_monitoring_db"),
            patch("kabusys.run_execution.duckdb.connect"),
            patch(
                "kabusys.run_execution.BrokerClientFactory.create",
                return_value=mock_broker,
            ),
            patch("kabusys.run_execution.OrderRepository"),
            patch("kabusys.run_execution.OrderManager"),
            patch("kabusys.run_execution.RiskManager"),
            patch("kabusys.run_execution.Reconciler", _make_reconciler_mock()),
            patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine),
            patch("kabusys.run_execution._load_risk_config") as mock_load,
        ):
            mock_load.return_value = MagicMock()
            settings = MagicMock()
            settings.is_paper = False
            settings.sqlite_path = Path("/prod.db")
            settings.duckdb_path = Path("/data.duckdb")
            mock_settings_cls.return_value = settings

            main()

        # _load_risk_config は total_assets = 1_000_000 + 250_000 = 1_250_000 で呼ばれる
        mock_load.assert_called_once()
        assert mock_load.call_args.kwargs["initial_portfolio_value"] == 1_250_000.0

    def test_initial_portfolio_value_fallback_to_avg_price_when_no_current_price(self):
        mock_broker = MagicMock()
        mock_broker.get_available_cash.return_value = 500_000.0
        mock_broker.get_positions.return_value = [
            Position(code="9999", qty=200, avg_price=1500.0, current_price=None),
            # current_price=None → avg_price で代替: 200 * 1500 = 300_000
        ]
        mock_engine = MagicMock()

        with (
            patch("kabusys.run_execution.set_process_priority"),
            patch("kabusys.run_execution.Settings") as mock_settings_cls,
            patch("kabusys.run_execution.sqlite3.connect"),
            patch("kabusys.run_execution.init_monitoring_db"),
            patch("kabusys.run_execution.duckdb.connect"),
            patch(
                "kabusys.run_execution.BrokerClientFactory.create",
                return_value=mock_broker,
            ),
            patch("kabusys.run_execution.OrderRepository"),
            patch("kabusys.run_execution.OrderManager"),
            patch("kabusys.run_execution.RiskManager"),
            patch("kabusys.run_execution.Reconciler", _make_reconciler_mock()),
            patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine),
            patch("kabusys.run_execution._load_risk_config") as mock_load,
        ):
            mock_load.return_value = MagicMock()
            settings = MagicMock()
            settings.is_paper = False
            settings.sqlite_path = Path("/prod.db")
            settings.duckdb_path = Path("/data.duckdb")
            mock_settings_cls.return_value = settings

            main()

        # total_assets = 500_000 + 300_000 = 800_000
        assert mock_load.call_args.kwargs["initial_portfolio_value"] == 800_000.0

    def test_initial_portfolio_value_fallback_to_avg_price_when_current_price_is_zero(
        self,
    ):
        mock_broker = MagicMock()
        mock_broker.get_available_cash.return_value = 500_000.0
        mock_broker.get_positions.return_value = [
            Position(code="8888", qty=100, avg_price=1000.0, current_price=0.0),
            # current_price=0 → avg_price で代替: 100 * 1000 = 100_000
        ]
        mock_engine = MagicMock()

        with (
            patch("kabusys.run_execution.set_process_priority"),
            patch("kabusys.run_execution.Settings") as mock_settings_cls,
            patch("kabusys.run_execution.sqlite3.connect"),
            patch("kabusys.run_execution.init_monitoring_db"),
            patch("kabusys.run_execution.duckdb.connect"),
            patch(
                "kabusys.run_execution.BrokerClientFactory.create",
                return_value=mock_broker,
            ),
            patch("kabusys.run_execution.OrderRepository"),
            patch("kabusys.run_execution.OrderManager"),
            patch("kabusys.run_execution.RiskManager"),
            patch("kabusys.run_execution.Reconciler", _make_reconciler_mock()),
            patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine),
            patch("kabusys.run_execution._load_risk_config") as mock_load,
        ):
            mock_load.return_value = MagicMock()
            settings = MagicMock()
            settings.is_paper = False
            settings.sqlite_path = Path("/prod.db")
            settings.duckdb_path = Path("/data.duckdb")
            mock_settings_cls.return_value = settings

            main()

        # total_assets = 500_000 + 100_000 = 600_000
        assert mock_load.call_args.kwargs["initial_portfolio_value"] == 600_000.0


def test_run_execution_stops_on_flag(tmp_path):
    """停止フラグが事前に存在するとき、エンジンを起動せず終了することを確認する。

    run_execution.main() はフラグが起動前に存在する場合、エンジンを生成した後に
    早期リターンする実装になっており、engine.run_session() と engine.stop() は
    いずれも呼ばれない。
    """
    stop_flag = tmp_path / "stop.flag"
    stop_flag.touch()  # フラグを事前に作成

    mock_engine = MagicMock()

    with (
        patch.object(re_mod, "_STOP_FLAG", stop_flag),
        patch("kabusys.run_execution.set_process_priority"),
        patch("kabusys.run_execution.Settings"),
        patch("kabusys.run_execution.sqlite3.connect"),
        patch("kabusys.run_execution.init_monitoring_db"),
        patch("kabusys.run_execution.duckdb.connect"),
        patch("kabusys.run_execution.BrokerClientFactory.create"),
        patch("kabusys.run_execution.OrderRepository"),
        patch("kabusys.run_execution.OrderManager"),
        patch("kabusys.run_execution.RiskManager"),
        patch("kabusys.run_execution.Reconciler", _make_reconciler_mock()),
        patch("kabusys.run_execution.ExecutionEngine", return_value=mock_engine),
    ):
        re_mod.main()

    # フラグが起動前に存在 → エンジンは起動せず早期リターン。stop() は呼ばれない
    mock_engine.run_session.assert_not_called()
    mock_engine.stop.assert_not_called()


class TestLoadRiskConfig:
    def _write_yaml(self, tmp_path, data: dict) -> Path:
        p = tmp_path / "risk_config.yaml"
        p.write_text(yaml_mod.dump(data), encoding="utf-8")
        return p

    def test_loads_all_fields(self, tmp_path):
        p = self._write_yaml(
            tmp_path,
            {
                "risk": {
                    "max_position_pct": 0.15,
                    "max_utilization": 0.70,
                    "rate_limit_per_sec": 3,
                    "circuit_breaker_errors": 5,
                    "circuit_breaker_window_sec": 30,
                    "max_drawdown": 0.10,
                }
            },
        )
        config = re_mod._load_risk_config(p, initial_portfolio_value=5_000_000.0)
        assert isinstance(config, RiskConfig)
        assert config.max_position_pct == 0.15
        assert config.max_utilization == 0.70
        assert config.rate_limit_per_sec == 3
        assert config.circuit_breaker_errors == 5
        assert config.circuit_breaker_window_sec == 30
        assert config.max_drawdown == 0.10
        assert config.initial_portfolio_value == 5_000_000.0

    def test_file_not_found_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            re_mod._load_risk_config(tmp_path / "nonexistent.yaml", 0.0)

    def test_missing_key_raises(self, tmp_path):
        p = self._write_yaml(tmp_path, {"risk": {"max_position_pct": 0.20}})
        with pytest.raises(KeyError):
            re_mod._load_risk_config(p, 0.0)

    def test_missing_top_level_risk_key_raises(self, tmp_path):
        p = self._write_yaml(tmp_path, {"other": {}})
        with pytest.raises(KeyError):
            re_mod._load_risk_config(p, 0.0)

    def test_invalid_yaml_raises_value_error(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text("risk: [\ninvalid yaml", encoding="utf-8")
        with pytest.raises(ValueError, match="パース失敗"):
            re_mod._load_risk_config(p, 0.0)

    def test_max_position_pct_out_of_range_raises(self, tmp_path):
        p = self._write_yaml(
            tmp_path,
            {
                "risk": {
                    "max_position_pct": 1.5,  # > 1
                    "max_utilization": 0.80,
                    "rate_limit_per_sec": 5,
                    "circuit_breaker_errors": 10,
                    "circuit_breaker_window_sec": 60,
                    "max_drawdown": 0.20,
                }
            },
        )
        with pytest.raises(ValueError, match="max_position_pct"):
            re_mod._load_risk_config(p, 0.0)

    def test_max_position_pct_exceeds_max_utilization_raises(self, tmp_path):
        p = self._write_yaml(
            tmp_path,
            {
                "risk": {
                    "max_position_pct": 0.90,
                    "max_utilization": 0.80,
                    "rate_limit_per_sec": 5,
                    "circuit_breaker_errors": 10,
                    "circuit_breaker_window_sec": 60,
                    "max_drawdown": 0.20,
                }
            },
        )
        with pytest.raises(ValueError, match="max_position_pct"):
            re_mod._load_risk_config(p, 0.0)

    def test_rate_limit_per_sec_zero_raises(self, tmp_path):
        p = self._write_yaml(
            tmp_path,
            {
                "risk": {
                    "max_position_pct": 0.20,
                    "max_utilization": 0.80,
                    "rate_limit_per_sec": 0,
                    "circuit_breaker_errors": 10,
                    "circuit_breaker_window_sec": 60,
                    "max_drawdown": 0.20,
                }
            },
        )
        with pytest.raises(ValueError, match="rate_limit_per_sec"):
            re_mod._load_risk_config(p, 0.0)

    def test_circuit_breaker_errors_negative_raises(self, tmp_path):
        p = self._write_yaml(
            tmp_path,
            {
                "risk": {
                    "max_position_pct": 0.20,
                    "max_utilization": 0.80,
                    "rate_limit_per_sec": 5,
                    "circuit_breaker_errors": -1,
                    "circuit_breaker_window_sec": 60,
                    "max_drawdown": 0.20,
                }
            },
        )
        with pytest.raises(ValueError, match="circuit_breaker_errors"):
            re_mod._load_risk_config(p, 0.0)


# ---------------------------------------------------------------------------
# Issue #413: DuckDB read_only + signal_date
# ---------------------------------------------------------------------------


def _run_main_capture(signal_date, argv=None, engine_failed=False):
    """main() を実行し (duckdb.connect モック, ExecutionEngine クラスモック, count モック) を返す。"""
    mock_broker = MagicMock()
    mock_broker.get_available_cash.return_value = 10_000_000.0
    mock_broker.get_positions.return_value = []
    with (
        patch("kabusys.run_execution.set_process_priority"),
        patch("kabusys.run_execution.Settings") as mock_settings_cls,
        patch("kabusys.run_execution.sqlite3.connect"),
        patch("kabusys.run_execution.init_monitoring_db"),
        patch("kabusys.run_execution.duckdb.connect") as mock_duck,
        patch("kabusys.run_execution.BrokerClientFactory.create", return_value=mock_broker),
        patch("kabusys.run_execution.OrderRepository"),
        patch("kabusys.run_execution.OrderManager"),
        patch("kabusys.run_execution.RiskManager"),
        patch("kabusys.run_execution.Reconciler", _make_reconciler_mock()),
        patch("kabusys.run_execution.ExecutionEngine") as mock_engine_cls,
        patch("kabusys.run_execution._load_risk_config", return_value=MagicMock()),
        patch("kabusys.run_execution.prev_trading_day", return_value=signal_date),
        patch("kabusys.run_execution._count_pending_signals", return_value=0) as mock_count,
    ):
        mock_engine_cls.return_value.signal_processing_failed = engine_failed
        settings = MagicMock()
        settings.is_paper = False
        settings.sqlite_path = Path("/prod.db")
        settings.duckdb_path = Path("/data.duckdb")
        mock_settings_cls.return_value = settings
        main(argv)
    return mock_duck, mock_engine_cls, mock_count


class TestRunExecutionSignalQueue:
    def test_duckdb_opened_read_only(self):
        mock_duck, _, _ = _run_main_capture(date(2026, 3, 27))
        assert mock_duck.call_count == 1
        assert mock_duck.call_args.kwargs.get("read_only") is True

    def test_engine_config_uses_prev_trading_day_as_signal_date(self):
        _, mock_engine_cls, mock_count = _run_main_capture(date(2026, 3, 27))
        config = mock_engine_cls.call_args.kwargs["config"]
        assert config.target_date == date.today()
        assert config.signal_date == date(2026, 3, 27)
        assert mock_count.call_args.args[1] == date(2026, 3, 27)

    def test_count_pending_signals_counts_signal_date_only(self):
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE signal_queue (signal_id VARCHAR, date DATE, status VARCHAR)")
        conn.execute(
            "INSERT INTO signal_queue VALUES"
            " ('a', '2026-03-27', 'pending'), ('b', '2026-03-27', 'pending'),"
            " ('c', '2026-03-27', 'filled'), ('d', '2026-03-30', 'pending')"
        )
        assert re_mod._count_pending_signals(conn, date(2026, 3, 27)) == 2
        conn.close()


class TestRunExecutionFailureAndOverride:
    def test_signal_processing_failure_ends_with_failed_status(self):
        """I1: エンジンのシグナル処理が失敗したら、ジョブは failed・非ゼロ終了。"""
        with patch("kabusys.run_execution.update_process") as mock_update:
            with patch("kabusys.run_execution.register_process", return_value=7):
                with pytest.raises(SystemExit) as exc_info:
                    _run_main_capture(date(2026, 3, 27), engine_failed=True)
        assert exc_info.value.code == 1
        mock_update.assert_called_once_with(7, status="failed")

    def test_success_when_signal_processing_ok(self):
        with patch("kabusys.run_execution.update_process") as mock_update:
            with patch("kabusys.run_execution.register_process", return_value=7):
                _run_main_capture(date(2026, 3, 27), engine_failed=False)
        mock_update.assert_called_once_with(7, status="success")

    def test_notifier_passed_to_engine(self):
        with patch("kabusys.run_execution.build_notifier") as mock_build:
            _, mock_engine_cls, _ = _run_main_capture(date(2026, 3, 27))
        assert mock_engine_cls.call_args.kwargs["notifier"] is mock_build.return_value

    def test_cli_signal_date_overrides_default(self, monkeypatch):
        """I3: --signal-date で読む queue 日付を上書きできる（Paper E2E・注入用）。"""
        monkeypatch.delenv("KABUSYS_SIGNAL_DATE", raising=False)
        _, mock_engine_cls, mock_count = _run_main_capture(
            date(2026, 3, 27), argv=["--signal-date", "2026-03-20"]
        )
        assert mock_engine_cls.call_args.kwargs["config"].signal_date == date(2026, 3, 20)
        assert mock_count.call_args.args[1] == date(2026, 3, 20)

    def test_env_signal_date_overrides_default(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_SIGNAL_DATE", "2026-03-19")
        _, mock_engine_cls, _ = _run_main_capture(date(2026, 3, 27))
        assert mock_engine_cls.call_args.kwargs["config"].signal_date == date(2026, 3, 19)

    def test_cli_wins_over_env(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_SIGNAL_DATE", "2026-03-19")
        _, mock_engine_cls, _ = _run_main_capture(
            date(2026, 3, 27), argv=["--signal-date", "2026-03-20"]
        )
        assert mock_engine_cls.call_args.kwargs["config"].signal_date == date(2026, 3, 20)

    def test_invalid_env_signal_date_raises(self, monkeypatch):
        monkeypatch.setenv("KABUSYS_SIGNAL_DATE", "2026/03/19")
        with pytest.raises(ValueError, match="KABUSYS_SIGNAL_DATE"):
            re_mod._resolve_signal_date(MagicMock(), date(2026, 3, 30), None)

    def test_default_uses_prev_trading_day(self, monkeypatch):
        monkeypatch.delenv("KABUSYS_SIGNAL_DATE", raising=False)
        with patch("kabusys.run_execution.prev_trading_day", return_value=date(2026, 3, 27)):
            assert re_mod._resolve_signal_date(MagicMock(), date(2026, 3, 30), None) == date(
                2026, 3, 27
            )
