# src/kabusys/backtest/engine.py
"""
バックテストエンジン。

BacktestFramework.md Section 6〜8 に従い、全体ループと補助関数を提供する。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import duckdb

from kabusys.backtest.metrics import BacktestMetrics, calc_metrics
from kabusys.backtest.simulator import DailySnapshot, PortfolioSimulator, TradeRecord

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """run_backtest() の戻り値。"""

    history: list[DailySnapshot]
    trades: list[TradeRecord]
    metrics: BacktestMetrics


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------

def _build_backtest_conn(
    source_conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
) -> duckdb.DuckDBPyConnection:
    """本番 DB からインメモリ DuckDB にデータをコピーしてバックテスト用接続を返す。

    本番 DB の signals / positions テーブルを汚染しない。
    シグナル生成に必要な features 等は start_date - 300日 から end_date までコピーする。

    Args:
        source_conn: 本番 DuckDB 接続（読み取り専用で使用）。
        start_date:  バックテスト開始日。
        end_date:    バックテスト終了日。

    Returns:
        init_schema(":memory:") 済みのインメモリ接続。
    """
    from kabusys.data.schema import init_schema

    bt_conn = init_schema(":memory:")
    data_start = start_date - timedelta(days=300)

    # 日付範囲でフィルタするテーブル
    date_filtered_tables = ("prices_daily", "features", "ai_scores", "market_regime")
    for table in date_filtered_tables:
        try:
            rows = source_conn.execute(
                f"SELECT * FROM {table} WHERE date >= ? AND date <= ?",
                [data_start, end_date],
            ).fetchall()
            if not rows:
                continue
            result = source_conn.execute(f"SELECT * FROM {table} LIMIT 0")
            cols = [desc[0] for desc in result.description]
            placeholders = ", ".join(["?" for _ in cols])
            bt_conn.executemany(
                f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})", rows
            )
        except Exception as exc:
            logger.warning("_build_backtest_conn: %s のコピーをスキップ: %s", table, exc)

    # market_calendar は全件コピー
    try:
        rows = source_conn.execute("SELECT * FROM market_calendar").fetchall()
        if rows:
            result = source_conn.execute("SELECT * FROM market_calendar LIMIT 0")
            cols = [desc[0] for desc in result.description]
            placeholders = ", ".join(["?" for _ in cols])
            bt_conn.executemany(
                f"INSERT OR IGNORE INTO market_calendar VALUES ({placeholders})", rows
            )
    except Exception as exc:
        logger.warning("_build_backtest_conn: market_calendar のコピーをスキップ: %s", exc)

    return bt_conn


def _fetch_open_prices(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> dict[str, float]:
    """指定日の全銘柄始値を {code: open} 辞書で返す。"""
    rows = conn.execute(
        "SELECT code, CAST(open AS DOUBLE) FROM prices_daily WHERE date = ?",
        [trading_day],
    ).fetchall()
    return {code: price for code, price in rows if price is not None}


def _fetch_close_prices(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> dict[str, float]:
    """指定日の全銘柄終値を {code: close} 辞書で返す。"""
    rows = conn.execute(
        "SELECT code, CAST(close AS DOUBLE) FROM prices_daily WHERE date = ?",
        [trading_day],
    ).fetchall()
    return {code: price for code, price in rows if price is not None}


def _write_positions(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
    positions: dict[str, int],
    cost_basis: dict[str, float],
) -> None:
    """シミュレータの保有状態を positions テーブルに書き戻す（冪等）。

    generate_signals() の _generate_sell_signals() が positions テーブルを読むため、
    シグナル生成の直前に呼び出す必要がある。
    market_value は NULL で挿入（nullable カラム、SELL 判定では参照しない）。

    Args:
        positions:  code → 株数（0株の銘柄は書き込まない）。
        cost_basis: code → 平均取得単価。
    """
    conn.execute("DELETE FROM positions WHERE date = ?", [trading_day])
    for code, shares in positions.items():
        if shares <= 0:
            continue
        avg_price = cost_basis.get(code, 0.0)
        conn.execute(
            "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
            "VALUES (?, ?, ?, ?, NULL)",
            [trading_day, code, shares, avg_price],
        )


def _read_day_signals(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> tuple[list[dict], list[dict]]:
    """指定日の signals テーブルから BUY / SELL シグナルを読み取る。

    generate_signals() の呼び出し後に使用する。

    Returns:
        (buy_signals, sell_signals)
        buy_signals:  [{"code": str, "signal_rank": int}, ...]
        sell_signals: [{"code": str}, ...]
    """
    buy_rows = conn.execute(
        "SELECT code, signal_rank FROM signals "
        "WHERE date = ? AND side = 'buy' ORDER BY signal_rank",
        [trading_day],
    ).fetchall()
    sell_rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
        [trading_day],
    ).fetchall()
    buy_signals = [{"code": row[0], "signal_rank": row[1]} for row in buy_rows]
    sell_signals = [{"code": row[0]} for row in sell_rows]
    return buy_signals, sell_signals


# ---------------------------------------------------------------------------
# パブリック API（run_backtest は Task 5 で実装）
# ---------------------------------------------------------------------------

def run_backtest(
    conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
    initial_cash: float = 10_000_000,
    slippage_rate: float = 0.001,
    commission_rate: float = 0.00055,
    max_position_pct: float = 0.20,
) -> BacktestResult:
    """バックテストを実行し結果を返す。

    本番 DB の conn からインメモリ DuckDB にデータをコピーし、
    generate_signals() を使って日次シミュレーションを行う。

    Args:
        conn:             本番 DuckDB 接続（読み取り専用で使用）。
        start_date:       バックテスト開始日（含む）。
        end_date:         バックテスト終了日（含む）。
        initial_cash:     初期資金（円）。
        slippage_rate:    スリッページ率（デフォルト 0.1%）。
        commission_rate:  手数料率（デフォルト 0.055%）。
        max_position_pct: 1銘柄あたりの最大ポートフォリオ比率（デフォルト 20%）。

    Returns:
        BacktestResult（history, trades, metrics）。
    """
    from kabusys.data.calendar_management import get_trading_days
    from kabusys.strategy.signal_generator import generate_signals

    bt_conn = _build_backtest_conn(conn, start_date, end_date)
    simulator = PortfolioSimulator(initial_cash=initial_cash)
    signals_prev: list[dict] = []

    trading_days = get_trading_days(bt_conn, start_date, end_date)
    logger.info(
        "run_backtest: 開始 start=%s end=%s 営業日数=%d 初期資金=%.0f",
        start_date, end_date, len(trading_days), initial_cash,
    )

    for trading_day in trading_days:
        # Step 1: 前日シグナルを当日 open で約定
        open_prices = _fetch_open_prices(bt_conn, trading_day)
        simulator.execute_orders(signals_prev, open_prices, slippage_rate, commission_rate)

        # Step 2: positions テーブルに書き戻し（generate_signals の SELL 判定に必要）
        _write_positions(bt_conn, trading_day, simulator.positions, simulator.cost_basis)

        # Step 3: 終値で時価評価・スナップショット記録
        close_prices = _fetch_close_prices(bt_conn, trading_day)
        simulator.mark_to_market(trading_day, close_prices)

        # Step 4: 翌日用シグナル生成（bt_conn の positions を読んで SELL 判定）
        generate_signals(bt_conn, target_date=trading_day)

        # Step 5: 翌日の発注リストを組み立て（ポジションサイジング）
        buy_signals, sell_signals = _read_day_signals(bt_conn, trading_day)
        num_buy = len(buy_signals)
        if num_buy > 0 and simulator.cash > 0:
            prior_pv = simulator.history[-1].portfolio_value if simulator.history else initial_cash
            alloc = min(
                prior_pv * max_position_pct,
                simulator.cash / num_buy,
            )
        else:
            alloc = 0.0

        signals_prev = [
            {"code": s["code"], "side": "buy", "alloc": alloc}
            for s in buy_signals
        ] + [
            {"code": s["code"], "side": "sell"}
            for s in sell_signals
        ]

    bt_conn.close()
    metrics = calc_metrics(simulator.history, simulator.trades)
    logger.info(
        "run_backtest: 完了 CAGR=%.2f%% Sharpe=%.3f MaxDD=%.2f%% Trades=%d",
        metrics.cagr * 100, metrics.sharpe_ratio,
        metrics.max_drawdown * 100, metrics.total_trades,
    )
    return BacktestResult(
        history=simulator.history,
        trades=simulator.trades,
        metrics=metrics,
    )
