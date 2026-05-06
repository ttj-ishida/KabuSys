"""
バックテスト結果 DB 永続化モジュール。

run.py（CLI）から呼び出され、BacktestResult と BacktestReport を
backtest_runs / backtest_trades / backtest_daily_equity の 3 テーブルに
単一トランザクションで書き込む。
"""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

import duckdb

if TYPE_CHECKING:
    from kabusys.backtest.engine import BacktestResult
    from kabusys.backtest.report import BacktestReport

logger = logging.getLogger(__name__)


def save_backtest_to_db(
    conn: duckdb.DuckDBPyConnection,
    run_id: str,
    result: "BacktestResult",
    report: "BacktestReport",
) -> None:
    """バックテスト結果を DB の 3 テーブルに永続化する。

    3 テーブルへの書き込みを単一トランザクションで実行する。
    run_id の一意性は呼び出し元が保証すること。重複 run_id は
    PRIMARY KEY 制約エラーとして例外を送出する。

    Args:
        conn:   初期化済みの DuckDB 接続（backtest_runs 等のテーブルが存在すること）。
        run_id: 一意の実行 ID。report.meta.run_id と一致させること。
        result: run_backtest() の戻り値。
        report: build_report() の戻り値。
    """
    meta = report.meta
    m = result.metrics

    # params_json: ReportMeta から run_id / generated_at / report_type を除いた全パラメータ
    params = {
        "start_date": meta.start_date,
        "end_date": meta.end_date,
        "initial_cash": meta.initial_cash,
        "slippage_rate": meta.slippage_rate,
        "commission_rate": meta.commission_rate,
        "allocation_method": meta.allocation_method,
        "max_position_pct": meta.max_position_pct,
        "max_utilization": meta.max_utilization,
        "max_positions": meta.max_positions,
        "risk_pct": meta.risk_pct,
        "stop_loss_pct": meta.stop_loss_pct,
        "lot_size": meta.lot_size,
        "min_holding_days": meta.min_holding_days,
        "max_holding_days": meta.max_holding_days,
        "trailing_stop_atr": meta.trailing_stop_atr,
        "scope_mode": meta.scope_mode,
    }
    params_json = json.dumps(params, ensure_ascii=False)

    scope_codes_json = (
        json.dumps(meta.scope_codes, ensure_ascii=False)
        if meta.scope_codes is not None
        else None
    )

    conn.execute("BEGIN")
    try:
        # backtest_runs: 1 行 INSERT
        conn.execute(
            """
            INSERT INTO backtest_runs (
                run_id, start_date, end_date, initial_cash,
                scope_mode, scope_codes_json, params_json,
                cagr, sharpe, max_drawdown, win_rate, payoff_ratio,
                profit_factor, annual_volatility, calmar_ratio,
                avg_holding_days, total_trades, effective_universe_size
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                run_id,
                meta.start_date,
                meta.end_date,
                meta.initial_cash,
                meta.scope_mode,
                scope_codes_json,
                params_json,
                m.cagr,
                m.sharpe_ratio,
                m.max_drawdown,
                m.win_rate,
                m.payoff_ratio,
                m.profit_factor,
                m.annual_volatility,
                m.calmar_ratio,
                m.avg_holding_days,
                m.total_trades,
                meta.effective_universe_size,
            ],
        )

        # backtest_trades: TradeRecord を一括 INSERT
        if result.trades:
            conn.executemany(
                """
                INSERT INTO backtest_trades
                    (run_id, date, code, side, shares, price, commission, realized_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    [
                        run_id,
                        t.date,
                        t.code,
                        t.side,
                        t.shares,
                        t.price,
                        t.commission,
                        t.realized_pnl,
                    ]
                    for t in result.trades
                ],
            )

        # backtest_daily_equity: DailySnapshot を一括 INSERT
        if result.history:
            conn.executemany(
                """
                INSERT INTO backtest_daily_equity (run_id, date, portfolio_value, cash)
                VALUES (?, ?, ?, ?)
                """,
                [[run_id, s.date, s.portfolio_value, s.cash] for s in result.history],
            )

        conn.execute("COMMIT")
    except Exception:
        try:
            conn.execute("ROLLBACK")
        except Exception as rb_exc:
            logger.warning("save_backtest_to_db: ROLLBACK failed: %s", rb_exc)
        raise
