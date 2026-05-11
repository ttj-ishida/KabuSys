"""
Market Close Summary データ収集モジュール。

DuckDB（positions, portfolio_performance）と SQLite（signal_queue）を
read-only で参照し、MarketCloseData を返す。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class MarketCloseData:
    """collect_market_close_data() が返す生データ。"""

    signal_pending_count: int  # 当日 pending シグナル件数
    positions_updated: bool  # positions に当日分が存在するか
    performance_recorded: bool  # portfolio_performance に当日分が存在するか
    filled_count: int  # 当日 filled シグナル件数
    daily_return: float | None  # 当日日次リターン（未記録なら None）
    equity_today: float | None  # 当日期末資産（未記録なら None）
    equity_prev: float | None  # 前営業日期末資産（存在しなければ None）


def check_signal_pending(sqlite_conn, today: date) -> int:
    """当日の pending シグナル件数を返す。"""
    row = sqlite_conn.execute(
        "SELECT COUNT(*) FROM signal_queue WHERE status = 'pending' AND date = ?",
        (today.isoformat(),),
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def check_signal_filled(sqlite_conn, today: date) -> int:
    """当日の filled シグナル件数を返す。"""
    row = sqlite_conn.execute(
        "SELECT COUNT(*) FROM signal_queue WHERE status = 'filled' AND date = ?",
        (today.isoformat(),),
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def check_positions_updated(duckdb_conn, today: date) -> bool:
    """positions テーブルに当日分のレコードが存在すれば True。"""
    row = duckdb_conn.execute(
        "SELECT COUNT(*) FROM positions WHERE date = ?",
        [today.isoformat()],
    ).fetchone()
    return int(row[0] if row and row[0] is not None else 0) > 0


def check_performance_recorded(duckdb_conn, today: date) -> bool:
    """portfolio_performance テーブルに当日分のレコードが存在すれば True。"""
    row = duckdb_conn.execute(
        "SELECT COUNT(*) FROM portfolio_performance WHERE date = ?",
        [today.isoformat()],
    ).fetchone()
    return int(row[0] if row and row[0] is not None else 0) > 0


def get_performance_row(duckdb_conn, today: date) -> tuple[float | None, float | None]:
    """(daily_return, equity) を返す。当日レコードがなければ (None, None)。"""
    row = duckdb_conn.execute(
        "SELECT daily_return, equity FROM portfolio_performance WHERE date = ?",
        [today.isoformat()],
    ).fetchone()
    if row is None:
        return None, None
    return (
        float(row[0]) if row[0] is not None else None,
        float(row[1]) if row[1] is not None else None,
    )


def get_prev_equity(duckdb_conn, today: date) -> float | None:
    """today より前の最新 equity を返す。存在しなければ None。"""
    row = duckdb_conn.execute(
        "SELECT equity FROM portfolio_performance WHERE date < ? ORDER BY date DESC LIMIT 1",
        [today.isoformat()],
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def collect_market_close_data(duckdb_conn, sqlite_conn, today: date) -> MarketCloseData:
    """全チェック関数を呼び出して MarketCloseData を返す。"""
    daily_return, equity_today = get_performance_row(duckdb_conn, today)
    return MarketCloseData(
        signal_pending_count=check_signal_pending(sqlite_conn, today),
        positions_updated=check_positions_updated(duckdb_conn, today),
        performance_recorded=check_performance_recorded(duckdb_conn, today),
        filled_count=check_signal_filled(sqlite_conn, today),
        daily_return=daily_return,
        equity_today=equity_today,
        equity_prev=get_prev_equity(duckdb_conn, today),
    )
