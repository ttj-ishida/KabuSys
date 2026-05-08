"""strategy_lab_data.py — Strategy Lab ページ（AI Addon）専用のデータロード関数。

各関数は DuckDB コネクションを受け取り DataFrame を返す。
Streamlit に依存しないため単体テスト可能。
"""

from __future__ import annotations

from datetime import date, timedelta

import duckdb
import pandas as pd


def load_market_regime(conn: duckdb.DuckDBPyConnection, days: int = 30) -> pd.DataFrame:
    """直近 N 日分の market_regime を返す。"""
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return conn.execute(
        """SELECT date, regime_score, regime_label, ma200_ratio, macro_sentiment
           FROM market_regime
           WHERE date >= ?::DATE
           ORDER BY date ASC""",
        [cutoff],
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
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return conn.execute(
        """SELECT date,
                  COUNT(*) FILTER (WHERE side='buy')  AS buy_count,
                  COUNT(*) FILTER (WHERE side='sell') AS sell_count
           FROM signals
           WHERE date >= ?::DATE
           GROUP BY date
           ORDER BY date ASC""",
        [cutoff],
    ).df()
