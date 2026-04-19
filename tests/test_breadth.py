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
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
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
    assert not row[4]
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


# ---------------------------------------------------------------------------
# Task 2: calc_and_save_breadth() — 騰落レシオ
# ---------------------------------------------------------------------------


def test_adv_decline_ratio_normal(conn):
    """混在データで騰落レシオが正しく計算される。

    Stock A: 26日間で毎日 +1 円ずつ上昇 → advances=25
    Stock B: 26日間で毎日 -1 円ずつ下落 → declines=25
    adv_decline_ratio = 25/25*100 = 100.0
    """
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)

    for i, d in enumerate(dates):
        _insert_price(conn, "A", d, 100.0 + i)

    for i, d in enumerate(dates):
        _insert_price(conn, "B", d, 200.0 - i)

    # _MIN_STOCKS=10 を満たすためのダミー銘柄（横ばい）
    for s in ["C", "D", "E", "F", "G", "H", "I", "J"]:
        for d in dates:
            _insert_price(conn, s, d, 100.0)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT adv_decline_ratio FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert abs(row[0] - 100.0) < 0.1


def test_adv_decline_ratio_no_declines(conn):
    """値下がり銘柄が 0 件 → adv_decline_ratio = 200.0。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)
    for i, d in enumerate(dates):
        _insert_price(conn, "A", d, 100.0 + i)

    # _MIN_STOCKS=10 を満たすためのダミー銘柄（横ばい）
    for s in ["B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        for d in dates:
            _insert_price(conn, s, d, 100.0)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT adv_decline_ratio FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert abs(row[0] - 200.0) < 1e-9


def _insert_price_per_stock_trend(
    conn, code: str, dates: list, *, up: bool
) -> None:
    """up=True なら上昇トレンド、False なら下落トレンドで挿入。"""
    for i, d in enumerate(dates):
        close = 100.0 + i if up else max(100.0 - i * 0.5, 1.0)
        _insert_price(conn, code, d, close)


def test_ma25_above_pct(conn):
    """close > ma25 の銘柄比率が正しく計算される。

    10銘柄中: 上昇2銘柄（A, C）、下落1銘柄（B）、横ばい7銘柄（D-J: close==ma25）
    上昇銘柄のみ close > ma25 → 2/10 = 0.2
    """
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)

    for i, d in enumerate(dates):
        _insert_price(conn, "A", d, 100.0 + i * 0.6)

    for i, d in enumerate(dates):
        _insert_price(conn, "B", d, 100.0 - i * 0.6)

    for i, d in enumerate(dates):
        _insert_price(conn, "C", d, 100.0 + i * 0.8)

    for s in ["D", "E", "F", "G", "H", "I", "J"]:
        for d in dates:
            _insert_price(conn, s, d, 100.0)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT ma25_above_pct FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert row[0] < 0.5


def test_breadth_stop_true(conn):
    """ma25_above_pct < 0.35 → breadth_stop = True。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)

    _insert_price_per_stock_trend(conn, "A", dates, up=True)
    for s in ["B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        _insert_price_per_stock_trend(conn, s, dates, up=False)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT breadth_stop, ma25_above_pct FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert row[0]
    assert row[1] < 0.35


def test_breadth_stop_false(conn):
    """ma25_above_pct >= 0.35 → breadth_stop = False。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)

    for s in ["A", "B", "C", "D", "E", "F", "G", "H"]:
        _insert_price_per_stock_trend(conn, s, dates, up=True)
    for s in ["I", "J"]:
        _insert_price_per_stock_trend(conn, s, dates, up=False)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT breadth_stop FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert not row[0]


def test_new_high_low_ratio_normal(conn):
    """52週高値/安値比率が正しく計算される。

    Stock A, B: 最終日 close が 250日最高値 → new_high = 2
    Stock C: 最終日 close が 250日最安値 → new_low = 1
    ratio = 2.0
    """
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(260, TARGET_DATE)

    for d in dates[:-1]:
        _insert_price(conn, "A", d, 100.0)
    _insert_price(conn, "A", dates[-1], 200.0)

    for d in dates[:-1]:
        _insert_price(conn, "B", d, 100.0)
    _insert_price(conn, "B", dates[-1], 300.0)

    for d in dates[:-1]:
        _insert_price(conn, "C", d, 100.0)
    _insert_price(conn, "C", dates[-1], 50.0)

    for s in ["D", "E", "F", "G", "H", "I", "J"]:
        for d in dates[-26:]:
            _insert_price(conn, s, d, 100.0)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT new_high_low_ratio FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert row[0] is not None
    assert abs(row[0] - 2.0) < 0.1


def test_new_high_low_ratio_no_lows(conn):
    """新安値 0 件 → new_high_low_ratio = NULL。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)
    for s in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        for i, d in enumerate(dates):
            _insert_price(conn, s, d, 100.0 + i)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 1

    row = conn.execute(
        "SELECT new_high_low_ratio FROM market_breadth WHERE date = ?",
        [TARGET_DATE],
    ).fetchone()
    assert row is not None
    assert row[0] is None


def test_insufficient_data_returns_zero(conn):
    """25日分未満のデータ → 0 を返してスキップ。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(10, TARGET_DATE)
    for s in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        for d in dates:
            _insert_price(conn, s, d, 100.0)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 0

    row = conn.execute(
        "SELECT 1 FROM market_breadth WHERE date = ?", [TARGET_DATE]
    ).fetchone()
    assert row is None


def test_insufficient_stocks_returns_zero(conn):
    """計算対象銘柄数 < 10 件 → 0 を返してスキップ。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)
    for s in ["A", "B", "C"]:  # 3 stocks only (< 10)
        for d in dates:
            _insert_price(conn, s, d, 100.0 + 1)

    result = calc_and_save_breadth(conn, TARGET_DATE)
    assert result == 0

    row = conn.execute(
        "SELECT 1 FROM market_breadth WHERE date = ?", [TARGET_DATE]
    ).fetchone()
    assert row is None


def test_idempotent(conn):
    """同日を 2 回実行しても market_breadth の行が重複しない。"""
    from kabusys.data.breadth import calc_and_save_breadth

    dates = _make_dates(26, TARGET_DATE)
    for s in ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]:
        for i, d in enumerate(dates):
            _insert_price(conn, s, d, 100.0 + i)

    r1 = calc_and_save_breadth(conn, TARGET_DATE)
    r2 = calc_and_save_breadth(conn, TARGET_DATE)

    assert r1 == 1
    assert r2 == 0

    count = conn.execute(
        "SELECT COUNT(*) FROM market_breadth WHERE date = ?", [TARGET_DATE]
    ).fetchone()[0]
    assert count == 1
