"""backtest_summarizer 単体テスト（Issue #233）"""

from __future__ import annotations

import json

import duckdb
import pytest

from kabusys.ai.backtest_summarizer import load_latest_summary

_BACKTEST_RUNS_DDL = """
    CREATE TABLE backtest_runs (
        run_id                  VARCHAR       PRIMARY KEY,
        created_at              TIMESTAMP     NOT NULL DEFAULT current_timestamp,
        start_date              DATE          NOT NULL,
        end_date                DATE          NOT NULL,
        initial_cash            DECIMAL(18,2) NOT NULL,
        scope_mode              VARCHAR       NOT NULL,
        scope_codes_json        VARCHAR,
        params_json             VARCHAR       NOT NULL,
        cagr                    DOUBLE,
        sharpe                  DOUBLE,
        max_drawdown            DOUBLE,
        win_rate                DOUBLE,
        payoff_ratio            DOUBLE,
        profit_factor           DOUBLE,
        annual_volatility       DOUBLE,
        calmar_ratio            DOUBLE,
        avg_holding_days        DOUBLE,
        total_trades            INTEGER,
        effective_universe_size INTEGER
    )
"""

_SAMPLE_PARAMS = {
    "weights": {"momentum": 0.4, "value": 0.3, "quality": 0.2, "ai": 0.1},
    "threshold": 0.60,
    "sector_boost": 0.03,
    "sector_quartile": 0.25,
    "stop_loss_rate": -0.08,
    "trailing_stop_atr_mult": 2.0,
    "gap_up_threshold": 0.04,
    "gap_down_threshold": -0.04,
    "min_holding_days": 5,
    "max_holding_days": 60,
    "topix_drawdown_threshold": -0.15,
    "topix_size_multiplier_bear": 0.5,
}


@pytest.fixture
def bt_conn():
    conn = duckdb.connect(":memory:")
    conn.execute(_BACKTEST_RUNS_DDL)
    yield conn
    conn.close()


def _insert_run(conn, run_id="r1", params=None):
    p = params if params is not None else _SAMPLE_PARAMS
    conn.execute(
        """
        INSERT INTO backtest_runs (
            run_id, start_date, end_date, initial_cash, scope_mode, params_json,
            cagr, sharpe, max_drawdown, win_rate, payoff_ratio, profit_factor, total_trades
        ) VALUES (?, '2026-01-01', '2026-04-30', 1000000, 'default_universe', ?,
                  0.123, 1.45, -0.082, 0.583, 1.82, 2.10, 142)
        """,
        [run_id, json.dumps(p)],
    )


class TestLoadLatestSummary:
    def test_returns_none_when_empty(self, bt_conn):
        assert load_latest_summary(bt_conn) is None

    def test_contains_cagr(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "+12.30%" in result

    def test_contains_sharpe_and_drawdown(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert "1.450" in result
        assert "-8.20%" in result

    def test_contains_win_rate_and_trades(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert "58.30%" in result
        assert "142" in result

    def test_contains_buy_logic_params(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "threshold=0.6" in result
        assert "sector_boost=0.03" in result

    def test_contains_risk_filter_params(self, bt_conn):
        _insert_run(bt_conn)
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "stop_loss_rate=-0.08" in result
        assert "trailing_stop_atr_mult=2.0" in result
        assert "topix_drawdown_threshold=-0.15" in result

    def test_invalid_params_json_no_crash(self, bt_conn):
        bt_conn.execute(
            """
            INSERT INTO backtest_runs (
                run_id, start_date, end_date, initial_cash, scope_mode, params_json,
                cagr, sharpe, max_drawdown, win_rate, payoff_ratio, profit_factor, total_trades
            ) VALUES ('r_bad', '2026-01-01', '2026-04-30', 1000000, 'default_universe',
                      'INVALID_JSON', 0.10, 1.0, -0.05, 0.5, 1.5, 1.8, 100)
            """
        )
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "CAGR" in result

    def test_returns_latest_when_multiple_runs(self, bt_conn):
        _insert_run(bt_conn, run_id="r_old")
        newer_params = dict(_SAMPLE_PARAMS, threshold=0.70)
        bt_conn.execute(
            """
            INSERT INTO backtest_runs (
                run_id, start_date, end_date, initial_cash, scope_mode, params_json,
                cagr, sharpe, max_drawdown, win_rate, payoff_ratio, profit_factor,
                total_trades, created_at
            ) VALUES ('r_new', '2026-01-01', '2026-04-30', 1000000, 'default_universe',
                      ?, 0.20, 1.8, -0.06, 0.60, 2.0, 2.5, 180,
                      current_timestamp + INTERVAL 1 SECOND)
            """,
            [json.dumps(newer_params)],
        )
        result = load_latest_summary(bt_conn)
        assert result is not None
        assert "r_new" in result
        assert "threshold=0.7" in result
