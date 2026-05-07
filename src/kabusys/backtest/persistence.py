"""
バックテスト結果 DB 永続化モジュール。

run.py（CLI）から呼び出され、BacktestResult と BacktestReport を
backtest_runs / backtest_trades / backtest_daily_equity の 3 テーブルに
単一トランザクションで書き込む。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict
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

    # params_json: ReportMeta の全フィールドから DB 専用カラムおよび識別子を除外した辞書を JSON 化
    _PARAMS_EXCLUDE = {
        "run_id",
        "generated_at",
        "report_type",
        "scope_codes",
        "effective_universe_size",
        "excluded_codes",
    }
    params = {k: v for k, v in asdict(meta).items() if k not in _PARAMS_EXCLUDE}
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

        # backtest_trades: TradeRecord を一括 INSERT（trade_seq で 1 始まり連番）
        if result.trades:
            conn.executemany(
                """
                INSERT INTO backtest_trades
                    (run_id, trade_seq, date, code, side, shares, price, commission, realized_pnl)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    [
                        run_id,
                        seq,
                        t.date,
                        t.code,
                        t.side,
                        t.shares,
                        t.price,
                        t.commission,
                        t.realized_pnl,
                    ]
                    for seq, t in enumerate(result.trades, start=1)
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
