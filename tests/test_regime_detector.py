"""
市場レジーム判定モジュール テスト
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest

from kabusys.data.schema import init_schema


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """インメモリ DuckDB 接続（テスト毎に新規作成）。"""
    c = init_schema(":memory:")
    yield c
    c.close()


TARGET_DATE = date(2026, 3, 21)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _insert_price(conn, code: str, d: date, close: float) -> None:
    """prices_daily に1行挿入するヘルパー。"""
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d, code, close, close, close, close, 1_000_000],
    )


def _insert_prices_uniform(conn, code: str, days: int, close: float, before_date: date) -> None:
    """before_date の直前 days 日間を同一終値で挿入するヘルパー。"""
    for i in range(days, 0, -1):
        d = before_date - timedelta(days=i)
        _insert_price(conn, code, d, close)


def _insert_raw_news(conn, news_id: str, dt, title: str) -> None:
    """raw_news に1件挿入するヘルパー。"""
    conn.execute(
        "INSERT INTO raw_news (id, datetime, source, title) VALUES (?, ?, 'test', ?)",
        [news_id, dt, title],
    )


def _make_macro_response(score: float) -> MagicMock:
    """OpenAI レスポンスのモックを生成するヘルパー。"""
    mock_resp = MagicMock()
    mock_resp.choices[0].message.content = json.dumps({"macro_sentiment": score})
    return mock_resp


# ---------------------------------------------------------------------------
# Task 1: market_regime テーブルの存在確認
# ---------------------------------------------------------------------------

def test_market_regime_table_exists(conn):
    """init_schema() 後に market_regime テーブルが存在する。"""
    row = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name = 'market_regime'"
    ).fetchone()
    assert row is not None, "market_regime テーブルが存在しない"


def test_market_regime_columns(conn):
    """market_regime テーブルが必要なカラムを持つ。"""
    conn.execute(
        """
        INSERT INTO market_regime (date, regime_score, regime_label, ma200_ratio, macro_sentiment)
        VALUES (?, ?, ?, ?, ?)
        """,
        [date(2026, 1, 1), 0.5, "bull", 1.05, 0.3],
    )
    row = conn.execute(
        "SELECT date, regime_score, regime_label, ma200_ratio, macro_sentiment, created_at "
        "FROM market_regime WHERE date = ?",
        [date(2026, 1, 1)],
    ).fetchone()
    assert row is not None
    assert row[2] == "bull"
    assert abs(row[1] - 0.5) < 1e-9
    assert row[5] is not None  # created_at は自動設定
