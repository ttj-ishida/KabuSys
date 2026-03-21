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
    """before_date の直前 days 日間を同一終値で挿入するヘルパー。

    挿入される日付は before_date - (days+1) から before_date - 2 までの days 日間。
    before_date - 1 は呼び出し側が別途 _insert_price で最終値をセットできるよう空けておく。
    """
    for i in range(days + 1, 1, -1):
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


# ---------------------------------------------------------------------------
# Task 2: _calc_ma200_ratio()
# ---------------------------------------------------------------------------

def test_bear_by_ma(conn):
    """1321 が 200MA を大きく下回る → ma200_ratio が 1.0 未満 → score が bear に十分低い。"""
    from kabusys.ai.regime_detector import _calc_ma200_ratio

    # 199 日は 100 円、最終日は 85 円（乖離 -15%）
    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 85.0)

    ratio = _calc_ma200_ratio(conn, TARGET_DATE)

    # avg ≈ (199*100 + 85)/200 = 99.925, latest=85 → ratio≈0.8506
    assert ratio < 1.0, f"ratio={ratio} が 1.0 以上"
    # regime_score = 0.7*(ratio-1)*10 が -0.2 以下になることを確認
    score = 0.7 * (ratio - 1.0) * 10
    assert score <= -0.2, f"score={score} が -0.2 より大きい"


def test_bull_by_ma(conn):
    """1321 が 200MA を大きく上回る → ma200_ratio が 1.0 超 → score が bull に十分高い。"""
    from kabusys.ai.regime_detector import _calc_ma200_ratio

    # 199 日は 100 円、最終日は 130 円（乖離 +30%）
    _insert_prices_uniform(conn, "1321", 199, 100.0, TARGET_DATE)
    _insert_price(conn, "1321", TARGET_DATE - timedelta(days=1), 130.0)

    ratio = _calc_ma200_ratio(conn, TARGET_DATE)

    assert ratio > 1.0, f"ratio={ratio} が 1.0 以下"
    score = 0.7 * (ratio - 1.0) * 10
    assert score >= 0.2, f"score={score} が 0.2 より小さい"


def test_insufficient_prices(conn):
    """1321 のデータが _MA_WINDOW 日未満 → ma200_ratio=1.0 フォールバック。"""
    from kabusys.ai.regime_detector import _calc_ma200_ratio, _MA_WINDOW

    # 100 日分のみ挿入
    _insert_prices_uniform(conn, "1321", 100, 100.0, TARGET_DATE)

    ratio = _calc_ma200_ratio(conn, TARGET_DATE)
    assert ratio == 1.0, f"ratio={ratio}（期待: 1.0 フォールバック）"


def test_no_prices(conn):
    """1321 のデータが 0 件 → ma200_ratio=1.0 フォールバック。"""
    from kabusys.ai.regime_detector import _calc_ma200_ratio

    ratio = _calc_ma200_ratio(conn, TARGET_DATE)
    assert ratio == 1.0
