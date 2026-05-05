"""dashboard_data.py — Streamlit ダッシュボード各ページ共通のデータロード関数。

各関数は DuckDB / SQLite コネクションを受け取り DataFrame / list[dict] を返す。
Streamlit に依存しないため単体テスト可能。
"""

from __future__ import annotations

import sqlite3

import duckdb
import pandas as pd


# ---------------------------------------------------------------------------
# Home ページ（SQLite）
# ---------------------------------------------------------------------------


def load_error_logs(conn: sqlite3.Connection, limit: int = 20) -> list[dict]:
    """ERROR / CRITICAL レベルのリスクイベントを返す。"""
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        """SELECT * FROM risk_logs
           WHERE event_type IN ('CRITICAL', 'ORDER_ERROR', 'RISK_BREACH', 'KILL_SWITCH')
           ORDER BY logged_at DESC LIMIT ?""",
        (limit,),
    )
    return [dict(row) for row in cursor.fetchall()]


# ---------------------------------------------------------------------------
# Signal Queue ページ（DuckDB）
# ---------------------------------------------------------------------------


def load_signal_queue(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """signal_queue テーブルから全シグナルを返す。"""
    return conn.execute(
        """SELECT signal_id, date, code, side, size, order_type, price, status, created_at
           FROM signal_queue
           ORDER BY date DESC, created_at DESC
           LIMIT 200"""
    ).df()


def load_signals(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """直近7日分の signals テーブルを返す。"""
    return conn.execute(
        """SELECT date, code, side, score, signal_rank, size_multiplier
           FROM signals
           WHERE date >= current_date - INTERVAL 7 DAY
           ORDER BY date DESC, signal_rank ASC"""
    ).df()


def load_portfolio_targets(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """最新日付の portfolio_targets を返す。"""
    return conn.execute(
        """SELECT date, code, target_weight, target_size
           FROM portfolio_targets
           WHERE date = (SELECT MAX(date) FROM portfolio_targets)
           ORDER BY target_weight DESC NULLS LAST"""
    ).df()


# ---------------------------------------------------------------------------
# Performance ページ（DuckDB）
# ---------------------------------------------------------------------------


def load_portfolio_performance(
    conn: duckdb.DuckDBPyConnection, days: int = 90
) -> pd.DataFrame:
    """直近 N 日分の portfolio_performance を返す。"""
    return conn.execute(
        """SELECT date, env, equity, cash, drawdown, daily_return
           FROM portfolio_performance
           WHERE date >= current_date - INTERVAL (?) DAY
           ORDER BY date ASC""",
        [days],
    ).df()


def load_open_positions(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """最新日付のゼロ以外ポジションを返す。"""
    return conn.execute(
        """SELECT date, code, position_size, avg_price, market_value
           FROM positions
           WHERE date = (SELECT MAX(date) FROM positions)
             AND position_size != 0
           ORDER BY market_value DESC NULLS LAST"""
    ).df()


def load_recent_trades(
    conn: duckdb.DuckDBPyConnection, limit: int = 50
) -> pd.DataFrame:
    """直近 N 件の取引履歴を返す。"""
    return conn.execute(
        """SELECT trade_id, order_id, datetime, code, price, size
           FROM trades
           ORDER BY datetime DESC
           LIMIT ?""",
        [limit],
    ).df()


# ---------------------------------------------------------------------------
# Strategy Lab ページ（DuckDB）
# ---------------------------------------------------------------------------


def load_market_regime(conn: duckdb.DuckDBPyConnection, days: int = 30) -> pd.DataFrame:
    """直近 N 日分の market_regime を返す。"""
    return conn.execute(
        """SELECT date, regime_score, regime_label, ma200_ratio, macro_sentiment
           FROM market_regime
           WHERE date >= current_date - INTERVAL (?) DAY
           ORDER BY date ASC""",
        [days],
    ).df()


def load_ai_scores(conn: duckdb.DuckDBPyConnection) -> pd.DataFrame:
    """最新日付の AI スコアを返す。"""
    return conn.execute(
        """SELECT date, code, sentiment_score, regime_score, ai_score
           FROM ai_scores
           WHERE date = (SELECT MAX(date) FROM ai_scores)
           ORDER BY ai_score DESC NULLS LAST"""
    ).df()


def load_signal_summary(
    conn: duckdb.DuckDBPyConnection, days: int = 30
) -> pd.DataFrame:
    """直近 N 日のシグナル集計（日別 buy/sell 件数）を返す。"""
    return conn.execute(
        """SELECT date,
                  COUNT(*) FILTER (WHERE side='buy')  AS buy_count,
                  COUNT(*) FILTER (WHERE side='sell') AS sell_count
           FROM signals
           WHERE date >= current_date - INTERVAL (?) DAY
           GROUP BY date
           ORDER BY date ASC""",
        [days],
    ).df()
