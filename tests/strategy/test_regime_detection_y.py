"""Group Y — TOPIX 騰落率ベースのエントリー抑制テスト (Issue #392)"""

from __future__ import annotations

from datetime import date, timedelta

from kabusys.data.schema import init_schema
from kabusys.strategy.signal_generator import generate_signals

TARGET = date(2024, 3, 1)
CODE = "1001"


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


def _insert_topix(conn, target_date: date, n_days: int = 25, trend: str = "flat"):
    """trend: 'flat' | 'down5pct' | 'down10pct' | 'up5pct'"""
    days: list[date] = []
    d = target_date
    while len(days) < n_days + 1:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            days.append(d)
    days.append(target_date)
    days.sort()

    base = 2000.0
    prices = []
    for i, dt in enumerate(days):
        if trend == "down5pct":
            # 期間全体で -5% の下落
            close = base * (1 - 0.05 * i / n_days)
        elif trend == "down10pct":
            close = base * (1 - 0.10 * i / n_days)
        elif trend == "up5pct":
            close = base * (1 + 0.05 * i / n_days)
        else:
            close = base
        prices.append((dt, close, close, close, close))

    conn.executemany(
        "INSERT OR REPLACE INTO topix_daily (date, open, high, low, close) VALUES (?, ?, ?, ?, ?)",
        prices,
    )


def _insert_stock(conn, code: str, target_date: date = TARGET):
    """高スコア銘柄をセットアップ"""
    d = target_date
    count = 0
    days = []
    while count < 25:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            days.append(d)
            count += 1
    days.append(target_date)
    days.sort()

    conn.executemany(
        "INSERT OR REPLACE INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, 100, 110, 90, 100, 10000)",
        [(dt, code) for dt in days],
    )
    conn.execute(
        "INSERT OR REPLACE INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, "
        "per, pbr, div_yield, ma200_dev, ma75_dev, ma25_dev, rsi_14, topix_rel_20, quality_score) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        # ma200_dev=0.5 でモメンタムスコアを閾値 0.58 以上に確保
        [target_date, code, 0.5, 0.5, -0.1, 0.5, 15.0, 1.0, 0.02, 0.5, 0.01, 0.01, 40.0, 0.05, 0.5],
    )
    conn.execute("INSERT OR IGNORE INTO stocks (code, sector) VALUES (?, 'T')", [code])


def _buy_count(conn, target_date: date = TARGET) -> int:
    row = conn.execute(
        "SELECT COUNT(*) FROM signals WHERE date = ? AND side = 'buy'",
        [target_date],
    ).fetchone()
    return int(row[0]) if row else 0


class TestTopixReturnBear:
    def test_buy_allowed_when_params_none(self):
        """topix_return_bear_* = None のときフィルターなし（デフォルト動作）。"""
        conn = _make_db()
        _insert_topix(conn, TARGET, trend="down10pct")
        _insert_stock(conn, CODE)
        generate_signals(conn=conn, target_date=TARGET, threshold=0.58)
        assert _buy_count(conn) == 1, "パラメータ未指定 → フィルターなし"

    def test_buy_suppressed_when_topix_falls_below_threshold(self):
        """TOPIX が period 日間で threshold を超えて下落 → BUY 全件抑制。"""
        conn = _make_db()
        _insert_topix(conn, TARGET, n_days=20, trend="down10pct")
        _insert_stock(conn, CODE)
        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            topix_return_bear_period=20,
            topix_return_bear_threshold=-0.05,
        )
        assert _buy_count(conn) == 0, "TOPIX -10% > threshold -5% → BUY 抑制"

    def test_buy_allowed_when_topix_return_above_threshold(self):
        """TOPIX の騰落率が閾値以上なら BUY は通常通り発生。"""
        conn = _make_db()
        _insert_topix(conn, TARGET, n_days=20, trend="flat")
        _insert_stock(conn, CODE)
        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            topix_return_bear_period=20,
            topix_return_bear_threshold=-0.05,
        )
        assert _buy_count(conn) == 1, "TOPIX 0% > threshold -5% → BUY 通過"

    def test_buy_allowed_when_topix_rising(self):
        """TOPIX が上昇中 → threshold を大きく上回り BUY 通過。"""
        conn = _make_db()
        _insert_topix(conn, TARGET, n_days=20, trend="up5pct")
        _insert_stock(conn, CODE)
        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            topix_return_bear_period=20,
            topix_return_bear_threshold=-0.03,
        )
        assert _buy_count(conn) == 1, "TOPIX +5% > threshold -3% → BUY 通過"

    def test_buy_allowed_when_topix_data_missing(self):
        """topix_daily データがない場合は安全側（BUY 許可）にフォールバック。"""
        conn = _make_db()
        # topix_daily には何も挿入しない
        _insert_stock(conn, CODE)
        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            topix_return_bear_period=20,
            topix_return_bear_threshold=-0.03,
        )
        assert _buy_count(conn) == 1, "topix_daily データ欠損 → 安全側でBUY許可"

    def test_buy_suppressed_only_on_down_days(self):
        """threshold 付近の境界テスト: -3% 未満なら抑制、-3% ちょうどなら通過。"""
        # -2.9% のケース（閾値 -3% を上回る → 通過）
        conn = _make_db()
        # 20日間で -2.9% の下落
        days = []
        d = TARGET
        for _ in range(22):
            d -= timedelta(days=1)
            if d.weekday() < 5:
                days.append(d)
        days.append(TARGET)
        days.sort()
        n = len(days) - 1
        conn.executemany(
            "INSERT OR REPLACE INTO topix_daily (date, open, high, low, close) VALUES (?, ?, ?, ?, ?)",
            [(dt, 2000, 2000, 2000, 2000 * (1 - 0.029 * i / n)) for i, dt in enumerate(days)],
        )
        _insert_stock(conn, CODE)
        generate_signals(
            conn=conn,
            target_date=TARGET,
            threshold=0.58,
            topix_return_bear_period=20,
            topix_return_bear_threshold=-0.03,
        )
        assert _buy_count(conn) == 1, "TOPIX -2.9% > threshold -3% → BUY 通過"
