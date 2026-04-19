"""
market_breadth テーブルおよび breadth 計算モジュールのテスト
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from kabusys.data.schema import init_schema

# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


TARGET_DATE = date(2026, 4, 1)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _insert_price(conn, code: str, d: date, close: float) -> None:
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
        [d, code, close, close, close, close, 1_000_000],
    )


def _make_dates(n: int, before: date = TARGET_DATE) -> list[date]:
    """before より前の n 日分の日付リスト（昇順）。"""
    return [before - timedelta(days=n - i) for i in range(n)]


# ---------------------------------------------------------------------------
# Task 1: market_breadth テーブル存在確認
# ---------------------------------------------------------------------------


def test_market_breadth_table_exists(conn):
    """init_schema() 後に market_breadth テーブルが存在する。"""
    row = conn.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_name = 'market_breadth'"
    ).fetchone()
    assert row is not None, "market_breadth テーブルが存在しない"


def test_market_breadth_columns(conn):
    """market_breadth テーブルが必要なカラムを持ち INSERT できる。"""
    conn.execute(
        "INSERT INTO market_breadth "
        "(date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, breadth_stop) "
        "VALUES (?, ?, ?, ?, ?)",
        [date(2026, 1, 1), 100.0, 0.5, 2.0, False],
    )
    row = conn.execute(
        "SELECT date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, "
        "breadth_stop, created_at FROM market_breadth WHERE date = ?",
        [date(2026, 1, 1)],
    ).fetchone()
    assert row is not None
    assert abs(row[1] - 100.0) < 1e-9
    assert abs(row[2] - 0.5) < 1e-9
    assert abs(row[3] - 2.0) < 1e-9
    assert row[4] == False
    assert row[5] is not None  # created_at は自動設定


def test_market_breadth_null_new_high_low(conn):
    """new_high_low_ratio は NULL を許容する（新安値=0 のケース）。"""
    conn.execute(
        "INSERT INTO market_breadth "
        "(date, adv_decline_ratio, ma25_above_pct, new_high_low_ratio, breadth_stop) "
        "VALUES (?, ?, ?, ?, ?)",
        [date(2026, 1, 2), 80.0, 0.4, None, True],
    )
    row = conn.execute(
        "SELECT new_high_low_ratio FROM market_breadth WHERE date = ?",
        [date(2026, 1, 2)],
    ).fetchone()
    assert row is not None
    assert row[0] is None
