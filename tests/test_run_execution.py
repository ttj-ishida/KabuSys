# tests/test_run_execution.py
from pathlib import Path
from unittest.mock import MagicMock, patch

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
