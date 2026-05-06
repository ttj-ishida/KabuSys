"""tests/test_backtest_persistence.py"""

from __future__ import annotations

import json as _json
from datetime import date

import duckdb
import pytest

from kabusys.backtest.engine import BacktestResult
from kabusys.backtest.metrics import BacktestMetrics
from kabusys.backtest.persistence import save_backtest_to_db
from kabusys.backtest.report import (
    BacktestReport,
    HeadlineMetrics,
    PerformanceSection,
    ReportMeta,
    TradeSection,
)
from kabusys.backtest.simulator import DailySnapshot, TradeRecord
from kabusys.data.schema import init_schema


class TestBacktestTablesExist:
    """init_schema() で 3 テーブルが作成されることを確認。"""

    def test_backtest_runs_table_exists(self):
        conn = init_schema(":memory:")
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'backtest_runs'"
        ).fetchone()
        assert result[0] == 1
        conn.close()

    def test_backtest_trades_table_exists(self):
        conn = init_schema(":memory:")
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'backtest_trades'"
        ).fetchone()
        assert result[0] == 1
        conn.close()

    def test_backtest_daily_equity_table_exists(self):
        conn = init_schema(":memory:")
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'backtest_daily_equity'"
        ).fetchone()
        assert result[0] == 1
        conn.close()

    def test_backtest_runs_primary_key(self):
        conn = init_schema(":memory:")
        conn.execute(
            "INSERT INTO backtest_runs "
            "(run_id, start_date, end_date, initial_cash, scope_mode, params_json) "
            "VALUES ('run1', '2024-01-01', '2024-12-31', 10000000, 'default_universe', '{}')"
        )
        with pytest.raises(duckdb.ConstraintException):
            conn.execute(
                "INSERT INTO backtest_runs "
                "(run_id, start_date, end_date, initial_cash, scope_mode, params_json) "
                "VALUES ('run1', '2024-01-01', '2024-12-31', 10000000, 'default_universe', '{}')"
            )
        conn.close()


# ---------------------------------------------------------------------------
# テスト用フィクスチャ
# ---------------------------------------------------------------------------


def _make_result() -> BacktestResult:
    history = [
        DailySnapshot(
            date=date(2024, 1, 4),
            cash=9_500_000.0,
            positions={"7203": 100},
            portfolio_value=10_100_000.0,
        ),
        DailySnapshot(
            date=date(2024, 1, 5),
            cash=9_500_000.0,
            positions={"7203": 100},
            portfolio_value=10_200_000.0,
        ),
    ]
    trades = [
        TradeRecord(
            date=date(2024, 1, 4),
            code="7203",
            side="buy",
            shares=100,
            price=6000.0,
            commission=3300.0,
            realized_pnl=None,
        ),
        TradeRecord(
            date=date(2024, 1, 5),
            code="7203",
            side="sell",
            shares=100,
            price=6100.0,
            commission=3355.0,
            realized_pnl=6645.0,
        ),
    ]
    metrics = BacktestMetrics(
        cagr=0.12,
        sharpe_ratio=1.5,
        max_drawdown=0.05,
        win_rate=0.6,
        payoff_ratio=1.8,
        total_trades=1,
        annual_volatility=0.15,
        calmar_ratio=2.4,
        profit_factor=2.1,
        avg_holding_days=1.0,
    )
    return BacktestResult(
        history=history,
        trades=trades,
        metrics=metrics,
        scope_mode="default_universe",
        effective_universe_size=100,
    )


def _make_report(
    result: BacktestResult, run_id: str = "test-run-001"
) -> BacktestReport:
    meta = ReportMeta(
        run_id=run_id,
        generated_at="2024-01-05T00:00:00+00:00",
        start_date="2024-01-04",
        end_date="2024-01-05",
        initial_cash=10_000_000.0,
        slippage_rate=0.001,
        commission_rate=0.00055,
        allocation_method="risk_based",
        max_position_pct=0.10,
        max_utilization=0.70,
        max_positions=10,
        risk_pct=0.005,
        stop_loss_pct=0.08,
        lot_size=100,
        scope_mode="default_universe",
        effective_universe_size=100,
    )
    headline = HeadlineMetrics(
        initial_cash=10_000_000.0,
        final_value=10_200_000.0,
        total_return=0.02,
        cagr=0.12,
        realized_pnl=6645.0,
        total_commission=6655.0,
        sharpe_ratio=1.5,
        max_drawdown=0.05,
        annual_volatility=0.15,
        calmar_ratio=2.4,
    )
    trade_section = TradeSection(
        total_trades=1,
        win_rate=0.6,
        payoff_ratio=1.8,
        profit_factor=2.1,
        avg_profit=6645.0,
        avg_loss=0.0,
        avg_holding_days=1.0,
    )
    return BacktestReport(
        meta=meta,
        headline=headline,
        trades=trade_section,
        performance=PerformanceSection(monthly_returns=[]),
        warnings=[],
    )


# ---------------------------------------------------------------------------
# save_backtest_to_db テスト
# ---------------------------------------------------------------------------


class TestSaveBacktestToDb:
    def setup_method(self):
        self.conn = init_schema(":memory:")
        self.result = _make_result()
        self.report = _make_report(self.result)

    def teardown_method(self):
        self.conn.close()

    def test_inserts_one_row_into_backtest_runs(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        count = self.conn.execute("SELECT COUNT(*) FROM backtest_runs").fetchone()[0]
        assert count == 1

    def test_backtest_runs_metrics_are_correct(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        row = self.conn.execute(
            "SELECT run_id, cagr, sharpe, max_drawdown, total_trades, effective_universe_size "
            "FROM backtest_runs WHERE run_id = 'test-run-001'"
        ).fetchone()
        assert row[0] == "test-run-001"
        assert abs(row[1] - 0.12) < 1e-6  # cagr
        assert abs(row[2] - 1.5) < 1e-6  # sharpe
        assert abs(row[3] - 0.05) < 1e-6  # max_drawdown
        assert row[4] == 1  # total_trades
        assert row[5] == 100  # effective_universe_size

    def test_inserts_all_trades(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        count = self.conn.execute("SELECT COUNT(*) FROM backtest_trades").fetchone()[0]
        assert count == 2

    def test_sell_trade_realized_pnl_is_correct(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        row = self.conn.execute(
            "SELECT realized_pnl FROM backtest_trades "
            "WHERE run_id = 'test-run-001' AND side = 'sell'"
        ).fetchone()
        assert row is not None
        assert abs(float(row[0]) - 6645.0) < 0.01

    def test_buy_trade_realized_pnl_is_null(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        row = self.conn.execute(
            "SELECT realized_pnl FROM backtest_trades "
            "WHERE run_id = 'test-run-001' AND side = 'buy'"
        ).fetchone()
        assert row is not None
        assert row[0] is None

    def test_inserts_all_daily_equity_rows(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        count = self.conn.execute(
            "SELECT COUNT(*) FROM backtest_daily_equity"
        ).fetchone()[0]
        assert count == 2

    def test_daily_equity_portfolio_value_is_correct(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        row = self.conn.execute(
            "SELECT portfolio_value FROM backtest_daily_equity "
            "WHERE run_id = 'test-run-001' AND date = '2024-01-05'"
        ).fetchone()
        assert row is not None
        assert abs(float(row[0]) - 10_200_000.0) < 0.01

    def test_duplicate_run_id_raises(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        with pytest.raises(Exception):
            save_backtest_to_db(
                self.conn, self.report.meta.run_id, self.result, self.report
            )

    def test_empty_trades_and_history_succeed(self):
        empty_result = BacktestResult(
            history=[],
            trades=[],
            metrics=BacktestMetrics(
                cagr=0.0,
                sharpe_ratio=0.0,
                max_drawdown=0.0,
                win_rate=0.0,
                payoff_ratio=0.0,
                total_trades=0,
            ),
        )
        report2 = _make_report(empty_result, run_id="test-run-002")
        save_backtest_to_db(self.conn, report2.meta.run_id, empty_result, report2)
        count = self.conn.execute(
            "SELECT COUNT(*) FROM backtest_runs WHERE run_id = 'test-run-002'"
        ).fetchone()[0]
        assert count == 1

    def test_params_json_contains_initial_cash(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        row = self.conn.execute(
            "SELECT params_json FROM backtest_runs WHERE run_id = 'test-run-001'"
        ).fetchone()
        params = _json.loads(row[0])
        assert params["initial_cash"] == 10_000_000.0

    def test_scope_mode_is_stored(self):
        save_backtest_to_db(
            self.conn, self.report.meta.run_id, self.result, self.report
        )
        row = self.conn.execute(
            "SELECT scope_mode FROM backtest_runs WHERE run_id = 'test-run-001'"
        ).fetchone()
        assert row[0] == "default_universe"

    def test_manual_codes_scope_codes_json_stored(self):
        manual_result = BacktestResult(
            history=self.result.history,
            trades=self.result.trades,
            metrics=self.result.metrics,
            scope_mode="manual_codes",
            scope_codes=["7203", "9984"],
        )
        meta2 = ReportMeta(
            run_id="test-run-003",
            generated_at="2024-01-05T00:00:00+00:00",
            start_date="2024-01-04",
            end_date="2024-01-05",
            initial_cash=10_000_000.0,
            slippage_rate=0.001,
            commission_rate=0.00055,
            allocation_method="risk_based",
            max_position_pct=0.10,
            max_utilization=0.70,
            max_positions=10,
            risk_pct=0.005,
            stop_loss_pct=0.08,
            lot_size=100,
            scope_mode="manual_codes",
            scope_codes=["7203", "9984"],
        )
        report3 = BacktestReport(
            meta=meta2,
            headline=self.report.headline,
            trades=self.report.trades,
            performance=self.report.performance,
            warnings=[],
        )
        save_backtest_to_db(self.conn, "test-run-003", manual_result, report3)
        row = self.conn.execute(
            "SELECT scope_mode, scope_codes_json FROM backtest_runs WHERE run_id = 'test-run-003'"
        ).fetchone()
        assert row[0] == "manual_codes"
        assert _json.loads(row[1]) == ["7203", "9984"]


class TestRunCliPersistence:
    """run.py の永続化呼び出しを直接関数呼び出しで検証する。"""

    def test_run_backtest_saves_to_db(self, tmp_path):
        db_path = tmp_path / "test.duckdb"
        conn = init_schema(str(db_path))
        conn.close()

        result = _make_result()
        report = _make_report(result, run_id="cli-test-001")

        conn_persist = duckdb.connect(str(db_path))
        try:
            save_backtest_to_db(conn_persist, report.meta.run_id, result, report)
        finally:
            conn_persist.close()

        conn_verify = duckdb.connect(str(db_path))
        count = conn_verify.execute(
            "SELECT COUNT(*) FROM backtest_runs WHERE run_id = 'cli-test-001'"
        ).fetchone()[0]
        conn_verify.close()
        assert count == 1

    def test_db_persistence_does_not_affect_existing_schema(self, tmp_path):
        db_path = tmp_path / "test2.duckdb"
        conn = init_schema(str(db_path))
        conn.close()

        result = _make_result()
        report = _make_report(result, run_id="cli-test-002")

        conn_persist = duckdb.connect(str(db_path))
        try:
            save_backtest_to_db(conn_persist, report.meta.run_id, result, report)
        finally:
            conn_persist.close()

        conn_verify = duckdb.connect(str(db_path))
        count = conn_verify.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'prices_daily'"
        ).fetchone()[0]
        conn_verify.close()
        assert count == 1
