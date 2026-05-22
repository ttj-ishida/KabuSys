"""tests/test_bb_reversal.py - BB逆張り戦略ヘルパー単体テスト"""

from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "backtest" / "backtest_improvement_plan")
)
from run_bb_reversal import (
    _compute_bb_rows,
    _generate_buy_signals,
    _generate_sell_signals,
    _is_buy_blocked_by_regime,
)


def _price_db(prices: list[tuple]) -> duckdb.DuckDBPyConnection:
    """(date, code, close) のリストから prices_daily を持つ in-memory DB を返す。"""
    conn = duckdb.connect(":memory:")
    conn.execute(
        "CREATE TABLE prices_daily "
        "(date DATE, code VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)"
    )
    for d, code, close in prices:
        conn.execute(
            "INSERT INTO prices_daily VALUES (?, ?, ?, ?, ?, ?, 1000000)",
            [d, code, close, close, close, close],
        )
    return conn


def _dates(n: int, start: date = date(2024, 1, 2)) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


# ----- _compute_bb_rows -----


def test_bb_rows_basic_structure():
    prices = [(_dates(25)[i], "1001", 1000.0 + i * 2) for i in range(25)]
    conn = _price_db(prices)
    rows = _compute_bb_rows(conn, _dates(25)[-1], period=20, sigma=2.0)
    assert len(rows) == 1
    code, close, lower_band, middle_band = rows[0]
    assert code == "1001"
    assert lower_band < middle_band


def test_bb_rows_insufficient_history_excluded():
    prices = [(_dates(10)[i], "1001", 1000.0 + i) for i in range(10)]
    conn = _price_db(prices)
    rows = _compute_bb_rows(conn, _dates(10)[-1], period=20, sigma=2.0)
    assert rows == []


def test_bb_rows_zero_std_excluded():
    # 全期間同一価格 → std=0 → 除外
    prices = [(_dates(25)[i], "1001", 1000.0) for i in range(25)]
    conn = _price_db(prices)
    rows = _compute_bb_rows(conn, _dates(25)[-1], period=20, sigma=2.0)
    assert rows == []


# ----- _generate_buy_signals -----


def test_buy_signal_when_close_below_lower_band():
    bb_rows = [("1001", 800.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001"}, set())
    assert len(signals) == 1
    assert signals[0]["code"] == "1001"
    assert signals[0]["size_multiplier"] == 1.0


def test_buy_signal_not_generated_when_above_lower_band():
    bb_rows = [("1001", 1050.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001"}, set())
    assert signals == []


def test_buy_signal_not_generated_when_already_held():
    bb_rows = [("1001", 800.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001"}, {"1001"})
    assert signals == []


def test_buy_signal_not_generated_outside_universe():
    bb_rows = [("9999", 800.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001"}, set())
    assert signals == []


def test_buy_signals_have_sequential_rank():
    bb_rows = [("1001", 800.0, 900.0, 1000.0), ("1002", 750.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001", "1002"}, set())
    assert len(signals) == 2
    assert {s["signal_rank"] for s in signals} == {1, 2}


# ----- _generate_sell_signals -----
# held_trading_days: 保有営業日数カウンタ（BUY 約定日を1日目として毎営業日インクリメント）


def test_sell_on_middle_band_return():
    signals = _generate_sell_signals(
        close_prices={"1001": 1010.0},
        positions={"1001": 100},
        cost_basis={"1001": 950.0},
        held_trading_days={"1001": 5},
        middle_bands={"1001": 1000.0},
        stop_loss_rate=0.08,
        max_holding_days=20,
    )
    assert any(s["code"] == "1001" for s in signals)


def test_sell_on_stop_loss():
    # pnl = (850 - 1000) / 1000 = -15% → -8% 超過
    signals = _generate_sell_signals(
        close_prices={"1001": 850.0},
        positions={"1001": 100},
        cost_basis={"1001": 1000.0},
        held_trading_days={"1001": 3},
        middle_bands={"1001": 1000.0},
        stop_loss_rate=0.08,
        max_holding_days=20,
    )
    assert any(s["code"] == "1001" for s in signals)


def test_no_sell_when_below_middle_and_above_stop():
    # close=950, middle=1000, cost=1000 → pnl=-5% (>-8%), close<middle → no SELL
    signals = _generate_sell_signals(
        close_prices={"1001": 950.0},
        positions={"1001": 100},
        cost_basis={"1001": 1000.0},
        held_trading_days={"1001": 5},
        middle_bands={"1001": 1000.0},
        stop_loss_rate=0.08,
        max_holding_days=20,
    )
    assert signals == []


def test_sell_on_max_holding_days():
    # 21 営業日 >= 20 → time_exit SELL
    signals = _generate_sell_signals(
        close_prices={"1001": 980.0},
        positions={"1001": 100},
        cost_basis={"1001": 1000.0},
        held_trading_days={"1001": 21},
        middle_bands={"1001": 1000.0},
        stop_loss_rate=0.08,
        max_holding_days=20,
    )
    assert any(s["code"] == "1001" for s in signals)


# ----- _is_buy_blocked_by_regime -----


class TestIsBuyBlockedByRegime:
    """_is_buy_blocked_by_regime の単体テスト。"""

    _DAY = date(2024, 6, 1)

    def test_no_regime_tables_returns_false(self):
        """テーブルが存在しない空の DB → False（BUY 許可）。"""
        conn = duckdb.connect(":memory:")
        assert _is_buy_blocked_by_regime(conn, self._DAY) is False

    def test_breadth_stop_true_blocks_buy(self):
        """market_breadth.breadth_stop = True → True（BUY ブロック）。"""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE market_breadth (date DATE, breadth_stop BOOLEAN)")
        conn.execute("INSERT INTO market_breadth VALUES (?, ?)", [self._DAY, True])
        assert _is_buy_blocked_by_regime(conn, self._DAY) is True

    def test_breadth_stop_false_allows_buy(self):
        """market_breadth.breadth_stop = False → False（BUY 許可）。"""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE market_breadth (date DATE, breadth_stop BOOLEAN)")
        conn.execute("INSERT INTO market_breadth VALUES (?, ?)", [self._DAY, False])
        assert _is_buy_blocked_by_regime(conn, self._DAY) is False

    def test_market_regime_bear_blocks_buy(self):
        """market_regime.label = 'bear' → True（BUY ブロック）。"""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE market_regime (date DATE, label VARCHAR)")
        conn.execute("INSERT INTO market_regime VALUES (?, ?)", [self._DAY, "bear"])
        assert _is_buy_blocked_by_regime(conn, self._DAY) is True

    def test_market_regime_bull_allows_buy(self):
        """market_regime.label = 'bull' → False（BUY 許可）。"""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE market_regime (date DATE, label VARCHAR)")
        conn.execute("INSERT INTO market_regime VALUES (?, ?)", [self._DAY, "bull"])
        assert _is_buy_blocked_by_regime(conn, self._DAY) is False

    def test_both_conditions_true_blocks_buy(self):
        """breadth_stop=True かつ label='bear' → True（BUY ブロック）。"""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE market_breadth (date DATE, breadth_stop BOOLEAN)")
        conn.execute("CREATE TABLE market_regime (date DATE, label VARCHAR)")
        conn.execute("INSERT INTO market_breadth VALUES (?, ?)", [self._DAY, True])
        conn.execute("INSERT INTO market_regime VALUES (?, ?)", [self._DAY, "bear"])
        assert _is_buy_blocked_by_regime(conn, self._DAY) is True

    def test_missing_date_returns_false(self):
        """テーブルは存在するが対象日の行がない → False（BUY 許可）。"""
        conn = duckdb.connect(":memory:")
        conn.execute("CREATE TABLE market_breadth (date DATE, breadth_stop BOOLEAN)")
        conn.execute("CREATE TABLE market_regime (date DATE, label VARCHAR)")
        other_day = date(2024, 1, 1)
        conn.execute("INSERT INTO market_breadth VALUES (?, ?)", [other_day, True])
        conn.execute("INSERT INTO market_regime VALUES (?, ?)", [other_day, "bear"])
        assert _is_buy_blocked_by_regime(conn, self._DAY) is False
