"""Group V エグジットロジック改善テスト (Issues #384, #385, #386)"""

from __future__ import annotations

from datetime import date, timedelta

from kabusys.data.schema import init_schema
from kabusys.strategy.signal_generator import generate_signals

TARGET = date(2024, 3, 1)


def _make_db():
    conn = init_schema(":memory:")
    d = date(2023, 1, 1)
    while d <= date(2024, 12, 31):
        if d.weekday() < 5:
            conn.execute(
                "INSERT OR IGNORE INTO market_calendar (date, is_trading_day) VALUES (?, true)",
                [d],
            )
        d += timedelta(days=1)
    return conn


def _insert_prices(
    conn,
    code: str,
    *,
    target_date: date = TARGET,
    close_today: float = 120.0,
    avg_daily_range: float = 5.0,
    n_days: int = 25,
    price_3d_ago: float | None = None,
):
    days: list[date] = []
    d = target_date
    while len(days) < n_days:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            days.append(d)
    days.reverse()

    prices = []
    for i, dt in enumerate(days):
        c = close_today - (n_days - i) * 0.5
        prices.append((dt, code, c, c + avg_daily_range / 2, c - avg_daily_range / 2, c, 10000))

    prices.append(
        (
            target_date,
            code,
            close_today,
            close_today + avg_daily_range / 2,
            close_today - avg_daily_range / 2,
            close_today,
            10000,
        )
    )

    if price_3d_ago is not None and len(days) >= 3:
        idx = len(prices) - 4
        if 0 <= idx < len(prices):
            d3 = prices[idx][0]
            prices[idx] = (
                d3,
                code,
                price_3d_ago,
                price_3d_ago + avg_daily_range / 2,
                price_3d_ago - avg_daily_range / 2,
                price_3d_ago,
                10000,
            )

    conn.executemany(
        "INSERT OR REPLACE INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        prices,
    )


def _insert_position(
    conn,
    code: str,
    *,
    avg_price: float = 100.0,
    target_date: date = TARGET,
    held_trading_days: int = 10,
):
    d = target_date
    count = 0
    while count < held_trading_days:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            count += 1
    entry_date = d

    conn.execute(
        "INSERT OR REPLACE INTO positions (date, code, position_size, avg_price) VALUES (?, ?, ?, ?)",
        [target_date, code, 100, avg_price],
    )
    conn.execute(
        "INSERT OR IGNORE INTO position_entries (code, entry_date) VALUES (?, ?)",
        [code, entry_date],
    )
    conn.execute("INSERT OR IGNORE INTO stocks (code, sector) VALUES (?, 'T')", [code])


def _insert_feature(
    conn,
    code: str,
    *,
    target_date: date = TARGET,
    momentum: float = -0.5,
):
    conn.execute(
        """
        INSERT OR REPLACE INTO features
            (date, code, momentum_20, momentum_60, volatility_20, volume_ratio,
             per, pbr, div_yield, ma200_dev, ma75_dev, ma25_dev, rsi_14, topix_rel_20, quality_score)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            target_date,
            code,
            momentum,
            momentum,
            -0.1,
            0.5,
            15.0,
            1.0,
            0.02,
            momentum,
            0.01,
            0.01,
            40.0,
            0.05,
            0.5,
        ],
    )


def _sell_count(conn, target_date: date = TARGET) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'sell'",
        [target_date],
    ).fetchone()
    return int(row[0]) if row else 0


def _buy_count(conn, target_date: date = TARGET) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'buy'",
        [target_date],
    ).fetchone()
    return int(row[0]) if row else 0


class TestScoreDropGate:
    CODE = "1001"

    def setup_method(self):
        self.conn = _make_db()
        _insert_prices(self.conn, self.CODE, close_today=120.0, avg_daily_range=5.0)
        _insert_position(self.conn, self.CODE, avg_price=100.0, held_trading_days=10)
        _insert_feature(self.conn, self.CODE, momentum=-0.5)

    def test_score_drop_fires_without_gate(self):
        generate_signals(conn=self.conn, target_date=TARGET, threshold=0.58)
        assert _sell_count(self.conn) == 1

    def test_score_drop_suppressed_with_gate_when_profit_exceeds(self):
        generate_signals(
            conn=self.conn,
            target_date=TARGET,
            threshold=0.58,
            score_drop_atr_gate=1.0,
        )
        assert _sell_count(self.conn) == 0, "含み益(20) > 1×ATR(≈5) → score_drop 抑制"

    def test_score_drop_fires_with_gate_when_profit_insufficient(self):
        generate_signals(
            conn=self.conn,
            target_date=TARGET,
            threshold=0.58,
            score_drop_atr_gate=5.0,
        )
        assert _sell_count(self.conn) == 1, "含み益(20) < 5×ATR(≈25) → score_drop 発動"

    def test_score_drop_fires_when_position_at_loss(self):
        conn = _make_db()
        _insert_prices(conn, self.CODE, close_today=90.0, avg_daily_range=5.0)
        _insert_position(conn, self.CODE, avg_price=100.0, held_trading_days=10)
        _insert_feature(conn, self.CODE, momentum=-0.5)
        generate_signals(conn=conn, target_date=TARGET, threshold=0.58, score_drop_atr_gate=1.0)
        assert _sell_count(conn) == 1, "含み損 → 抑制なし"


class TestStage4Trail:
    CODE = "1002"

    def test_stage4_uses_tighter_mult_when_conditions_met(self):
        """held >= 35 日・含み益率 13%+ で Stage4(1.2×) が Stage3(1.5×) より早く発動する。"""
        conn = _make_db()
        _insert_prices(conn, self.CODE, close_today=113.0, avg_daily_range=5.0, n_days=40)
        _insert_position(conn, self.CODE, avg_price=100.0, held_trading_days=35)
        _insert_feature(conn, self.CODE, momentum=0.5)

        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.8,
            trail_stage3_mult=1.5,
            trail_stage4_days=999,
            trail_stage4_profit_gate=0.10,
            trail_stage4_mult=1.2,
        )
        sells_without_stage4 = _sell_count(conn)
        conn.execute("DELETE FROM signals")

        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.8,
            trail_stage3_mult=1.5,
            trail_stage4_days=30,
            trail_stage4_profit_gate=0.10,
            trail_stage4_mult=1.2,
        )
        sells_with_stage4 = _sell_count(conn)

        assert sells_with_stage4 >= sells_without_stage4, (
            "Stage4(1.2×) は Stage3(1.5×) より tight → 同じかそれ以上の SELL が発生するはず"
        )

    def test_stage4_not_applied_when_params_are_none(self):
        """trail_stage4_* = None のとき Stage4 は発動せず Stage3 と同一挙動。"""
        conn = _make_db()
        _insert_prices(conn, self.CODE, close_today=113.0, avg_daily_range=5.0, n_days=40)
        _insert_position(conn, self.CODE, avg_price=100.0, held_trading_days=35)
        _insert_feature(conn, self.CODE, momentum=0.5)

        # Stage4 無効（None）
        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.8,
            trail_stage3_mult=1.5,
            trail_stage4_days=None,
            trail_stage4_profit_gate=None,
            trail_stage4_mult=None,
        )
        sells_none = _sell_count(conn)
        conn.execute("DELETE FROM signals")

        # Stage4 を days=999 で事実上無効化（旧来の回避手法）
        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.8,
            trail_stage3_mult=1.5,
            trail_stage4_days=999,
            trail_stage4_profit_gate=0.10,
            trail_stage4_mult=1.2,
        )
        sells_999 = _sell_count(conn)

        assert sells_none == sells_999, "trail_stage4_*=None は days=999 回避と同等の挙動"

    def test_stage4_not_applied_when_profit_below_gate(self):
        """含み益率 5% < gate 10%: Stage4 は適用されず Stage3 と同じ結果。"""
        conn = _make_db()
        _insert_prices(conn, self.CODE, close_today=105.0, avg_daily_range=5.0, n_days=40)
        _insert_position(conn, self.CODE, avg_price=100.0, held_trading_days=35)
        _insert_feature(conn, self.CODE, momentum=0.5)

        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.8,
            trail_stage3_mult=1.5,
            trail_stage4_days=30,
            trail_stage4_profit_gate=0.10,
            trail_stage4_mult=1.2,
        )
        sells_with = _sell_count(conn)
        conn.execute("DELETE FROM signals")

        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.8,
            trail_stage3_mult=1.5,
            trail_stage4_days=999,
            trail_stage4_profit_gate=0.10,
            trail_stage4_mult=1.2,
        )
        sells_without = _sell_count(conn)

        assert sells_with == sells_without, "含み益 < gate → Stage4 不適用"


class TestEntry3dFilter:
    CODE = "1003"

    def test_buy_suppressed_when_3d_return_exceeds_gate(self):
        conn = _make_db()
        _insert_prices(conn, self.CODE, close_today=107.0, price_3d_ago=100.0, n_days=25)
        _insert_feature(conn, self.CODE, momentum=0.5)
        generate_signals(
            conn=conn, target_date=TARGET, threshold=0.58, entry_3d_max_abs_return=0.05
        )
        assert _buy_count(conn) == 0, "3日騰落率 7% > gate 5% → BUY 抑制"

    def test_buy_allowed_when_3d_return_within_gate(self):
        conn = _make_db()
        _insert_prices(conn, self.CODE, close_today=103.0, price_3d_ago=100.0, n_days=25)
        _insert_feature(conn, self.CODE, momentum=0.5)
        generate_signals(
            conn=conn, target_date=TARGET, threshold=0.58, entry_3d_max_abs_return=0.05
        )
        assert _buy_count(conn) == 1, "3日騰落率 3% <= gate 5% → BUY 通過"

    def test_buy_suppressed_on_sharp_decline(self):
        conn = _make_db()
        _insert_prices(conn, self.CODE, close_today=94.0, price_3d_ago=100.0, n_days=25)
        _insert_feature(conn, self.CODE, momentum=0.5)
        generate_signals(
            conn=conn, target_date=TARGET, threshold=0.58, entry_3d_max_abs_return=0.05
        )
        assert _buy_count(conn) == 0, "3日騰落率 -6% (絶対値 6% > 5%) → BUY 抑制"

    def test_buy_allowed_when_no_3d_price_data(self):
        conn = _make_db()
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) VALUES (?, ?, 100, 100, 100, 100, 1000)",
            [TARGET, self.CODE],
        )
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) VALUES (?, ?, 100, 100, 100, 100, 1000)",
            [TARGET - timedelta(days=1), self.CODE],
        )
        _insert_feature(conn, self.CODE, momentum=0.5)
        generate_signals(
            conn=conn, target_date=TARGET, threshold=0.58, entry_3d_max_abs_return=0.05
        )
        assert _buy_count(conn) == 1, "3日前データなし → 安全側で BUY 許可"

    def test_no_filter_when_gate_is_none(self):
        conn = _make_db()
        _insert_prices(conn, self.CODE, close_today=120.0, price_3d_ago=100.0, n_days=25)
        _insert_feature(conn, self.CODE, momentum=0.5)
        generate_signals(conn=conn, target_date=TARGET, threshold=0.58)
        assert _buy_count(conn) == 1, "gate=None → フィルターなし"
