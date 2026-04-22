"""
シグナル生成モジュール テスト

_is_bear_regime バグ修正（market_regime.regime_label 参照）および
breadth_stop による BUY 停止の動作検証。
"""

from __future__ import annotations

from datetime import date

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


def _insert_feature(conn, code: str, d: date, high_score: bool = True) -> None:
    """features テーブルに高スコア or 低スコアのデータを挿入する。"""
    if high_score:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, -3.0, 3.0, 5.0, 3.0)",
            [d, code],
        )
    else:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, -3.0, -3.0, 3.0, -3.0, 100.0, -3.0)",
            [d, code],
        )


def _insert_breadth(
    conn,
    d: date,
    breadth_stop: bool,
    adv_decline_ratio: float = 100.0,
    ma25_above_pct: float = 0.5,
) -> None:
    conn.execute(
        "INSERT INTO market_breadth "
        "(date, adv_decline_ratio, ma25_above_pct, breadth_stop) "
        "VALUES (?, ?, ?, ?)",
        [d, adv_decline_ratio, ma25_above_pct, breadth_stop],
    )


def _insert_regime(conn, d: date, regime_label: str) -> None:
    score = 0.5 if regime_label == "bull" else -0.5 if regime_label == "bear" else 0.0
    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [d, score, regime_label],
    )


# ---------------------------------------------------------------------------
# _is_bear_regime バグ修正テスト
# ---------------------------------------------------------------------------


def test_is_bear_regime_from_market_regime(conn):
    """regime_label='bear' → True を返す（market_regime テーブルを正しく参照）。"""
    from kabusys.strategy.signal_generator import _is_bear_regime

    _insert_regime(conn, TARGET_DATE, "bear")
    assert _is_bear_regime(conn, TARGET_DATE) is True


def test_is_bear_regime_bull_returns_false(conn):
    """regime_label='bull' → False を返す。"""
    from kabusys.strategy.signal_generator import _is_bear_regime

    _insert_regime(conn, TARGET_DATE, "bull")
    assert _is_bear_regime(conn, TARGET_DATE) is False


def test_is_bear_regime_no_data_returns_false(conn):
    """market_regime にデータなし → False を返す（安全側）。"""
    from kabusys.strategy.signal_generator import _is_bear_regime

    assert _is_bear_regime(conn, TARGET_DATE) is False


# ---------------------------------------------------------------------------
# breadth_stop テスト
# ---------------------------------------------------------------------------


def test_breadth_stop_skips_buy_signals(conn):
    """breadth_stop=True → BUY シグナルが生成されない。"""
    from kabusys.strategy.signal_generator import generate_signals

    _insert_regime(conn, TARGET_DATE, "bull")
    _insert_breadth(conn, TARGET_DATE, breadth_stop=True)

    for code in ["7203", "9984"]:
        _insert_feature(conn, code, TARGET_DATE, high_score=True)

    generate_signals(conn, TARGET_DATE)

    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ?", [TARGET_DATE]
    ).fetchall()
    buy_signals = [r for r in rows if r[0] == "buy"]
    assert len(buy_signals) == 0, (
        f"breadth_stop=True なのに BUY が生成された: {len(buy_signals)} 件"
    )


def test_breadth_stop_false_allows_buy(conn):
    """breadth_stop=False → BUY シグナルが通常通り生成される。"""
    from kabusys.strategy.signal_generator import generate_signals

    _insert_regime(conn, TARGET_DATE, "bull")
    _insert_breadth(conn, TARGET_DATE, breadth_stop=False)

    for code in ["7203", "9984"]:
        _insert_feature(conn, code, TARGET_DATE, high_score=True)

    generate_signals(conn, TARGET_DATE)

    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ?", [TARGET_DATE]
    ).fetchall()
    buy_signals = [r for r in rows if r[0] == "buy"]
    assert len(buy_signals) > 0, "breadth_stop=False なのに BUY が生成されなかった"


def test_breadth_stop_bear_regime_both_block_buy(conn):
    """breadth_stop=True かつ bear レジーム → BUY 停止（独立した動作）。"""
    from kabusys.strategy.signal_generator import generate_signals

    _insert_regime(conn, TARGET_DATE, "bear")
    _insert_breadth(conn, TARGET_DATE, breadth_stop=True)

    for code in ["7203", "9984"]:
        _insert_feature(conn, code, TARGET_DATE, high_score=True)

    generate_signals(conn, TARGET_DATE)

    rows = conn.execute(
        "SELECT side FROM signals WHERE date = ?", [TARGET_DATE]
    ).fetchall()
    buy_signals = [r for r in rows if r[0] == "buy"]
    assert len(buy_signals) == 0


# ---------------------------------------------------------------------------
# Task 2: 最低保有日数 / 再エントリー制限
# ---------------------------------------------------------------------------

def _insert_position(conn, code: str, d: date, avg_price: float = 1000.0) -> None:
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, 100, ?)",
        [d, code, avg_price],
    )


def _insert_position_entry(
    conn, code: str, entry_date: date, sell_date=None
) -> None:
    conn.execute(
        "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, ?)",
        [code, entry_date, sell_date],
    )


def _insert_price(conn, code: str, d: date, close: float = 1000.0, open_: float = 1000.0) -> None:
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
        [d, code, open_, close * 1.01, close * 0.99, close],
    )


def _insert_calendar_days(conn, days: list) -> None:
    for d in days:
        conn.execute(
            "INSERT OR IGNORE INTO market_calendar (date, is_trading_day, is_half_day) VALUES (?, TRUE, FALSE)",
            [d],
        )


class TestMinHoldingDays:
    """BUY 後 5営業日はストップロス以外の SELL を抑制する。"""

    def test_score_drop_sell_suppressed_within_5_biz_days(self, conn):
        """保有 3営業日では score_drop SELL が抑制される。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        # 4営業日分のカレンダー登録
        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(4)]  # 4/1〜4/4
        _insert_calendar_days(conn, biz_days)

        entry_date = biz_days[0]  # 4/1 にエントリー
        target_date = biz_days[3]  # 4/4 (3営業日後)

        code = "1001"
        # features を target_date に挿入（低スコア → score_drop SELL を誘発）
        _insert_feature(conn, code, target_date, high_score=False)
        # 保有ポジション
        _insert_price(conn, code, target_date, close=1000.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        # position_entries に entry_date を登録
        _insert_position_entry(conn, code, entry_date)

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert len(sell_rows) == 0, "保有 3日目は score_drop SELL が抑制されるべき"

    def test_score_drop_sell_allowed_after_5_biz_days(self, conn):
        """保有 5営業日後は score_drop SELL が許可される。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(7)]
        _insert_calendar_days(conn, biz_days)

        entry_date = biz_days[0]   # 4/1
        target_date = biz_days[5]  # 4/6 (5営業日後)

        code = "1002"
        _insert_feature(conn, code, target_date, high_score=False)
        _insert_price(conn, code, target_date, close=1000.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        _insert_position_entry(conn, code, entry_date)

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "5営業日後は SELL 許可されるべき"

    def test_stop_loss_bypasses_min_holding(self, conn):
        """ストップロス到達は保有日数チェックをスキップして即 SELL する。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        entry_date = biz_days[0]
        target_date = biz_days[1]  # 1営業日後

        code = "1003"
        avg_price = 1000.0
        stop_loss_price = avg_price * 0.85  # -15% → ストップロス (-8%) 確実に超える
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=stop_loss_price)
        _insert_position(conn, code, target_date, avg_price=avg_price)
        _insert_position_entry(conn, code, entry_date)

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "ストップロスは即 SELL されるべき"

    def test_no_position_entry_allows_sell(self, conn):
        """position_entries にレコードがない場合は安全側で SELL 許可する。"""
        from kabusys.strategy.signal_generator import generate_signals

        target_date = date(2026, 4, 1)
        code = "1004"
        _insert_feature(conn, code, target_date, high_score=False)
        _insert_price(conn, code, target_date, close=1000.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        # position_entries に何も挿入しない

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "レコードなしは SELL 許可"


class TestReentryRestriction:
    """SELL 後 5営業日は同一銘柄の再 BUY を禁止する。"""

    def test_buy_suppressed_within_5_biz_days_after_sell(self, conn):
        """SELL 後 3営業日は再 BUY が抑制される。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(5)]
        _insert_calendar_days(conn, biz_days)

        sell_date = biz_days[0]   # 4/1 に SELL
        target_date = biz_days[3]  # 4/4 (3営業日後)

        code = "2001"
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        # 前日終値（gap filter 用）
        prev = biz_days[2]
        _insert_price(conn, code, prev, close=1000.0)
        # sell_date を登録
        _insert_position_entry(conn, code, sell_date - timedelta(days=10), sell_date)

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert not any(r[0] == code for r in buy_rows), "SELL 後 3日目は再 BUY 抑制"

    def test_buy_allowed_after_5_biz_days_cooldown(self, conn):
        """SELL 後 5営業日後は再 BUY が許可される。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(8)]
        _insert_calendar_days(conn, biz_days)

        sell_date = biz_days[0]
        target_date = biz_days[6]  # 6営業日後（5日経過）

        code = "2002"
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        prev = biz_days[5]
        _insert_price(conn, code, prev, close=1000.0)
        _insert_position_entry(conn, code, sell_date - timedelta(days=10), sell_date)

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in buy_rows), "5日後は再 BUY 許可"

    def test_no_sell_date_allows_buy(self, conn):
        """sell_date が NULL（保有中）は再エントリー制限なし。"""
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[1]
        code = "2003"
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        prev = biz_days[0]
        _insert_price(conn, code, prev, close=1000.0)
        # sell_date=None → 保有中
        _insert_position_entry(conn, code, biz_days[0], None)

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in buy_rows), "sell_date=NULL は BUY 許可"


# ---------------------------------------------------------------------------
# Task 8: 決算回避・イベントサイズ縮小
# ---------------------------------------------------------------------------


def _insert_earnings(conn, code: str, ann_date: date) -> None:
    conn.execute(
        "INSERT INTO earnings_calendar (code, announcement_date) VALUES (?, ?)",
        [code, ann_date],
    )


class TestEarningsAvoidance:
    """翌営業日が決算日の銘柄は BUY 抑制 + 保有分は SELL 強制。"""

    def test_buy_suppressed_when_earnings_next_day(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        next_day = biz_days[1]
        code = "3001"

        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_price(conn, code, base - timedelta(days=1), close=1000.0)
        _insert_earnings(conn, code, next_day)  # 翌営業日が決算

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert not any(r[0] == code for r in buy_rows), "決算翌日の銘柄は BUY 抑制"

    def test_buy_allowed_when_no_upcoming_earnings(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        code = "3002"

        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_price(conn, code, base - timedelta(days=1), close=1000.0)
        # earnings_calendar に登録なし

        generate_signals(conn, target_date)

        buy_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'buy'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in buy_rows), "決算なしは BUY 許可"

    def test_sell_forced_when_earnings_next_day(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        next_day = biz_days[1]
        code = "3003"

        # 高スコア（score_drop SELL は発生しない）
        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_position(conn, code, target_date, avg_price=950.0)  # 保有中
        _insert_earnings(conn, code, next_day)

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "決算前は強制 SELL"


class TestMinHoldingDaysBearException:
    """Bear レジーム移行時は最低保有日数チェックをスキップして即 SELL する。"""

    def test_score_drop_sell_allowed_in_bear_regime_within_5_days(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(4)]
        _insert_calendar_days(conn, biz_days)

        entry_date = biz_days[0]
        target_date = biz_days[2]  # 2営業日後（通常は SELL 抑制されるはず）

        code = "5001"
        _insert_feature(conn, code, target_date, high_score=False)  # score_drop
        _insert_price(conn, code, target_date, close=1000.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        _insert_position_entry(conn, code, entry_date)

        # Bear レジームを設定
        conn.execute(
            "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, -1.0, 'bear')",
            [target_date],
        )

        generate_signals(conn, target_date)

        sell_rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        assert any(r[0] == code for r in sell_rows), "Bear レジームは保有日数スキップで SELL"


class TestEventSizeMultiplier:
    """主要イベント前は size_multiplier=0.5 が付与される。"""

    def test_size_multiplier_half_on_event_day(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        next_day = biz_days[1]
        code = "4001"

        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_price(conn, code, base - timedelta(days=1), close=1000.0)

        # イベント日を next_day に設定
        event_dates = {next_day: "FOMC"}

        generate_signals(conn, target_date, event_dates=event_dates)

        row = conn.execute(
            "SELECT size_multiplier FROM signals WHERE date = ? AND code = ? AND side = 'buy'",
            [target_date, code],
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 0.5) < 1e-9, f"size_multiplier は 0.5 のはず: {row[0]}"

    def test_size_multiplier_one_when_no_event(self, conn):
        from datetime import timedelta
        from kabusys.strategy.signal_generator import generate_signals

        base = date(2026, 4, 1)
        biz_days = [base + timedelta(days=i) for i in range(3)]
        _insert_calendar_days(conn, biz_days)

        target_date = biz_days[0]
        code = "4002"

        _insert_feature(conn, code, target_date, high_score=True)
        _insert_price(conn, code, target_date, close=1000.0, open_=1000.0)
        _insert_price(conn, code, base - timedelta(days=1), close=1000.0)

        generate_signals(conn, target_date, event_dates={})

        row = conn.execute(
            "SELECT size_multiplier FROM signals WHERE date = ? AND code = ? AND side = 'buy'",
            [target_date, code],
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 1.0) < 1e-9
