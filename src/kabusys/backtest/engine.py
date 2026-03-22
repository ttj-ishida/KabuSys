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
    """バックテストを実行する（Task 5 で実装予定）。"""
    raise NotImplementedError("run_backtest は Task 5 で実装")
