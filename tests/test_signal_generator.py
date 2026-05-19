"""
シグナル生成モジュール テスト

RegimeProvider 移行後（market_regime.regime_label 参照）および
breadth_stop による BUY 停止の動作検証。
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
# DatabaseRegimeProvider テスト（market_regime テーブル参照）
# ---------------------------------------------------------------------------


def test_is_bear_regime_from_market_regime(conn):
    """regime_label='bear' → 'bear' を返す（market_regime テーブルを正しく参照）。"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    _insert_regime(conn, TARGET_DATE, "bear")
    provider = DatabaseRegimeProvider(conn)
    assert provider.get_regime(TARGET_DATE) == "bear"


def test_is_bear_regime_bull_returns_false(conn):
    """regime_label='bull' → 'bull' を返す。"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    _insert_regime(conn, TARGET_DATE, "bull")
    provider = DatabaseRegimeProvider(conn)
    assert provider.get_regime(TARGET_DATE) == "bull"


def test_is_bear_regime_no_data_returns_false(conn):
    """market_regime にデータなし → 'bull' を返す（安全側）。"""
    from kabusys.core.interfaces import DatabaseRegimeProvider

    provider = DatabaseRegimeProvider(conn)
    assert provider.get_regime(TARGET_DATE) == "bull"


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

    rows = conn.execute("SELECT side FROM signals WHERE date = ?", [TARGET_DATE]).fetchall()
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

    rows = conn.execute("SELECT side FROM signals WHERE date = ?", [TARGET_DATE]).fetchall()
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

    rows = conn.execute("SELECT side FROM signals WHERE date = ?", [TARGET_DATE]).fetchall()
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


def _insert_position_entry(conn, code: str, entry_date: date, sell_date=None) -> None:
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

        entry_date = biz_days[0]  # 4/1
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

        sell_date = biz_days[0]  # 4/1 に SELL
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

        from kabusys.core.interfaces import DatabaseRegimeProvider
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

        generate_signals(conn, target_date, regime_provider=DatabaseRegimeProvider(conn))

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


# ---------------------------------------------------------------------------
# Feature Toggle: AI センチメント無効時の WARNING 抑制
# ---------------------------------------------------------------------------


def test_generate_signals_no_ai_warning_when_ai_disabled(conn, monkeypatch, caplog):
    """ENABLE_AI_SENTIMENT=false の場合、AI スコア未登録でも WARNING が出ない。"""
    import logging

    from kabusys.strategy.signal_generator import generate_signals

    monkeypatch.delenv("ENABLE_AI_SENTIMENT", raising=False)

    _insert_regime(conn, TARGET_DATE, "bull")
    _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
    _insert_feature(conn, "7203", TARGET_DATE, high_score=True)

    with caplog.at_level(logging.WARNING, logger="kabusys.strategy.signal_generator"):
        generate_signals(conn, TARGET_DATE)

    ai_warnings = [r for r in caplog.records if "AI スコアが見つかりません" in r.getMessage()]
    assert len(ai_warnings) == 0, (
        f"ENABLE_AI_SENTIMENT=false なのに AI 警告が {len(ai_warnings)} 件出力された"
    )


# ---------------------------------------------------------------------------
# Task 6: TOPIX MA クロスに基づく size_multiplier 縮小
# ---------------------------------------------------------------------------

from kabusys.strategy.signal_generator import _get_topix_size_multiplier  # noqa: E402


class TestGetTopixSizeMultiplier:
    """TOPIX MA25/MA75/MA200 クロスに基づく size_multiplier のテスト。"""

    def _insert_topix_with_ma(
        self,
        conn,
        target_date: date,
        ma25: float | None,
        ma75: float | None,
        ma200: float | None,
    ) -> None:
        """target_date に MA 列付きで topix_daily へ1行挿入する。"""
        conn.execute(
            "INSERT INTO topix_daily (date, open, high, low, close, ma25, ma75, ma200) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [target_date, 2000.0, 2000.0, 2000.0, 2000.0, ma25, ma75, ma200],
        )

    def test_returns_1_when_no_topix_data(self, conn):
        """topix_daily にデータがない場合は 1.0 を返す（エントリー規制なし）。"""
        assert _get_topix_size_multiplier(conn, TARGET_DATE) == 1.0

    def test_returns_1_when_all_ma_none(self, conn):
        """MA 列がすべて NULL（データ不足）のとき 1.0 を返す。"""
        self._insert_topix_with_ma(conn, TARGET_DATE, None, None, None)
        assert _get_topix_size_multiplier(conn, TARGET_DATE) == 1.0

    def test_returns_1_in_bull_market(self, conn):
        """MA25 > MA75 > MA200 のとき（強気相場）1.0 を返す。"""
        # MA25 > MA75 > MA200
        self._insert_topix_with_ma(conn, TARGET_DATE, 2100.0, 2050.0, 2000.0)
        assert _get_topix_size_multiplier(conn, TARGET_DATE) == 1.0

    def test_returns_weak_bear_when_ma25_below_ma75(self, conn):
        """MA25 < MA75 かつ MA75 > MA200 のとき（弱いベア）size_multiplier_weak_bear を返す。"""
        # MA25 < MA75、MA75 > MA200
        self._insert_topix_with_ma(conn, TARGET_DATE, 1950.0, 2000.0, 1980.0)
        result = _get_topix_size_multiplier(conn, TARGET_DATE)
        assert result == 0.5  # デフォルト weak_bear

    def test_returns_strong_bear_when_ma75_below_ma200(self, conn):
        """MA75 < MA200 のとき（強いベア）size_multiplier_strong_bear を返す。"""
        # MA75 < MA200（強いベア）
        self._insert_topix_with_ma(conn, TARGET_DATE, 1900.0, 1950.0, 2000.0)
        result = _get_topix_size_multiplier(conn, TARGET_DATE)
        assert result == 0.0  # デフォルト strong_bear

    def test_strong_bear_takes_priority_over_weak_bear(self, conn):
        """MA75 < MA200 のときは MA25 < MA75 でも strong_bear が優先される。"""
        # MA25 < MA75 < MA200（両条件成立）
        self._insert_topix_with_ma(conn, TARGET_DATE, 1800.0, 1900.0, 2000.0)
        result = _get_topix_size_multiplier(conn, TARGET_DATE)
        assert result == 0.0  # strong_bear 優先

    def test_custom_weak_bear_multiplier(self, conn):
        """カスタム size_multiplier_weak_bear が適用される。"""
        self._insert_topix_with_ma(conn, TARGET_DATE, 1950.0, 2000.0, 1980.0)
        result = _get_topix_size_multiplier(conn, TARGET_DATE, size_multiplier_weak_bear=0.3)
        assert result == 0.3

    def test_custom_strong_bear_multiplier(self, conn):
        """カスタム size_multiplier_strong_bear が適用される。"""
        self._insert_topix_with_ma(conn, TARGET_DATE, 1900.0, 1950.0, 2000.0)
        result = _get_topix_size_multiplier(conn, TARGET_DATE, size_multiplier_strong_bear=0.25)
        assert result == 0.25

    def test_uses_latest_date_not_after_target(self, conn):
        """target_date 以前の直近データを参照する（当日データがなくても OK）。"""
        yesterday = TARGET_DATE - timedelta(days=1)
        self._insert_topix_with_ma(conn, yesterday, 1900.0, 1950.0, 2000.0)
        # TARGET_DATE のレコードはなし
        result = _get_topix_size_multiplier(conn, TARGET_DATE)
        assert result == 0.0  # 昨日のデータ（strong_bear）を参照


# ---------------------------------------------------------------------------
# Task 1: _load_strategy_config() sector/regime セクション
# ---------------------------------------------------------------------------

import kabusys.strategy.signal_generator as _sg  # noqa: E402


def _load_cfg_with_yaml(yaml_text: str, tmp_path, monkeypatch) -> dict:
    """tmp_path に YAML ファイルを書き、モジュールのパスとキャッシュをパッチして _load_strategy_config() を呼ぶ。"""
    cfg_file = tmp_path / "strategy_config.yaml"
    cfg_file.write_text(yaml_text, encoding="utf-8")
    monkeypatch.setattr(_sg, "_STRATEGY_CONFIG_PATH", cfg_file)
    monkeypatch.setattr(_sg, "_strategy_config_cache", None)
    monkeypatch.setattr(_sg, "_strategy_config_mtime", -1.0)
    return _sg._load_strategy_config()


class TestLoadStrategyConfigSectorRegime:
    """_load_strategy_config() の sector/regime セクション解析テスト。"""

    def test_valid_sector_and_regime(self, tmp_path, monkeypatch):
        yaml_text = """
strategy:
  threshold: 0.60
sector:
  boost: 0.05
  quartile: 0.30
regime:
  topix_size_multiplier_weak_bear: 0.4
  topix_size_multiplier_strong_bear: 0.0
"""
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_boost"] == 0.05
        assert cfg["sector_quartile"] == 0.30
        assert cfg["topix_size_multiplier_weak_bear"] == 0.4
        assert cfg["topix_size_multiplier_strong_bear"] == 0.0

    def test_missing_sector_section_uses_defaults(self, tmp_path, monkeypatch):
        yaml_text = "strategy:\n  threshold: 0.60\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_boost"] == 0.03
        assert cfg["sector_quartile"] == 0.25

    def test_missing_regime_section_uses_defaults(self, tmp_path, monkeypatch):
        yaml_text = "strategy:\n  threshold: 0.60\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["topix_size_multiplier_weak_bear"] == 0.5
        assert cfg["topix_size_multiplier_strong_bear"] == 0.0

    def test_sector_boost_negative_falls_back(self, tmp_path, monkeypatch):
        yaml_text = "strategy:\n  threshold: 0.60\nsector:\n  boost: -0.01\n  quartile: 0.25\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_boost"] == 0.03  # default

    def test_sector_quartile_zero_falls_back(self, tmp_path, monkeypatch):
        yaml_text = "strategy:\n  threshold: 0.60\nsector:\n  boost: 0.03\n  quartile: 0.0\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_quartile"] == 0.25  # default

    def test_sector_quartile_one_falls_back(self, tmp_path, monkeypatch):
        yaml_text = "strategy:\n  threshold: 0.60\nsector:\n  boost: 0.03\n  quartile: 1.0\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["sector_quartile"] == 0.25  # default

    def test_topix_weak_bear_over_one_falls_back(self, tmp_path, monkeypatch):
        yaml_text = (
            "strategy:\n  threshold: 0.60\nregime:\n  topix_size_multiplier_weak_bear: 1.5\n"
        )
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["topix_size_multiplier_weak_bear"] == 0.5  # default

    def test_topix_weak_bear_exactly_one_accepted(self, tmp_path, monkeypatch):
        yaml_text = (
            "strategy:\n  threshold: 0.60\nregime:\n  topix_size_multiplier_weak_bear: 1.0\n"
        )
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["topix_size_multiplier_weak_bear"] == 1.0

    def test_topix_strong_bear_zero_accepted(self, tmp_path, monkeypatch):
        """strong_bear=0.0 は有効（エントリー完全停止を意味する）。"""
        yaml_text = (
            "strategy:\n  threshold: 0.60\nregime:\n  topix_size_multiplier_strong_bear: 0.0\n"
        )
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["topix_size_multiplier_strong_bear"] == 0.0


# ---------------------------------------------------------------------------
# Task 2: _calc_sector_strengths sector_quartile パラメータ
# ---------------------------------------------------------------------------

from kabusys.strategy.signal_generator import _calc_sector_strengths  # noqa: E402


class TestCalcSectorStrengthsQuartile:
    """_calc_sector_strengths の sector_quartile パラメータテスト。"""

    def _setup_4sectors(self, conn) -> None:
        """4セクター・4銘柄・21日分の価格データを挿入する。"""
        sectors = [
            ("1001", "製造業", 1.10),
            ("1002", "金融業", 1.05),
            ("1003", "情報通信", 1.02),
            ("1004", "小売業", 0.98),
        ]
        for code, sector, _ in sectors:
            conn.execute("INSERT INTO stocks (code, sector) VALUES (?, ?)", [code, sector])
        base = date(2026, 1, 1)
        for j in range(21):
            d = base + timedelta(days=j)
            for code, _, ret in sectors:
                c = 1000.0 * ret if j == 20 else 1000.0
                conn.execute(
                    "INSERT INTO prices_daily (date, code, open, high, low, close, volume)"
                    " VALUES (?, ?, 1000, 1000, 1000, ?, 1000)",
                    [d, code, c],
                )

    def test_default_quartile_gives_1_top_sector(self, conn):
        self._setup_4sectors(conn)
        top, _, _ = _calc_sector_strengths(conn, date(2026, 1, 21))
        assert len(top) == 1  # ceil(4 * 0.25) = 1

    def test_custom_quartile_50_gives_2_top_sectors(self, conn):
        self._setup_4sectors(conn)
        top, _, _ = _calc_sector_strengths(conn, date(2026, 1, 21), sector_quartile=0.50)
        assert len(top) == 2  # ceil(4 * 0.50) = 2


# ---------------------------------------------------------------------------
# RSI 過熱フィルタ テスト (Issue #338)
# ---------------------------------------------------------------------------

from kabusys.research.factor_research import calc_rsi  # noqa: E402


class TestCalcRsi:
    """calc_rsi の単体テスト。"""

    def test_returns_rsi_with_sufficient_data(self, conn):
        """15件以上の価格データで RSI が計算されること。"""
        base = date(2024, 1, 1)
        rows = [
            (
                base + timedelta(days=i),
                "1001",
                1000.0 + i,
                1010.0 + i,
                990.0 + i,
                1000.0 + i,
                100000,
            )
            for i in range(20)
        ]
        conn.executemany(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        result = calc_rsi(conn, base + timedelta(days=19))
        assert len(result) == 1
        rsi = result[0]["rsi_14"]
        assert rsi is not None
        assert 0.0 <= rsi <= 100.0

    def test_returns_empty_with_insufficient_data(self, conn):
        """14件以下の価格データでは結果が空または rsi_14=None になること。"""
        base = date(2024, 1, 1)
        rows = [
            (base + timedelta(days=i), "1001", 1000.0, 1010.0, 990.0, 1000.0, 100000)
            for i in range(10)
        ]
        conn.executemany(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        result = calc_rsi(conn, base + timedelta(days=9))
        # データ不足なら空リストか rsi_14=None
        assert all(r["rsi_14"] is None for r in result) or len(result) == 0

    def test_rsi_100_when_all_gains(self, conn):
        """終値が毎日上昇する場合、RSI は 100 に近づくこと。"""
        base = date(2024, 1, 1)
        rows = [
            (
                base + timedelta(days=i),
                "1001",
                1000.0 + i * 10,
                1010.0 + i * 10,
                990.0 + i * 10,
                1000.0 + i * 10,
                100000,
            )
            for i in range(20)
        ]
        conn.executemany(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        result = calc_rsi(conn, base + timedelta(days=19))
        assert len(result) == 1
        assert result[0]["rsi_14"] == 100.0

    def test_rsi_0_when_all_losses(self, conn):
        """終値が毎日下降する場合、RSI は 0 に近づくこと。"""
        base = date(2024, 1, 1)
        rows = [
            (
                base + timedelta(days=i),
                "1001",
                1000.0 - i * 10,
                1010.0 - i * 10,
                990.0 - i * 10,
                max(100.0, 1000.0 - i * 10),
                100000,
            )
            for i in range(20)
        ]
        conn.executemany(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        result = calc_rsi(conn, base + timedelta(days=19))
        assert len(result) == 1
        assert result[0]["rsi_14"] == 0.0


class TestRsiOverboughtConfig:
    """rsi_overbought_threshold の config 読み込みテスト。"""

    def test_default_is_65(self):
        from kabusys.strategy.signal_generator import _STRATEGY_CONFIG_DEFAULTS

        assert _STRATEGY_CONFIG_DEFAULTS["rsi_overbought_threshold"] == 65.0

    def test_valid_value_accepted(self, tmp_path, monkeypatch):
        yaml_text = "strategy:\n  rsi_overbought_threshold: 75.0\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["rsi_overbought_threshold"] == 75.0

    def test_value_50_rejected(self, tmp_path, monkeypatch):
        """50 以下は無効（50 < x <= 100 の範囲外）→ デフォルト 65.0 にフォールバック。"""
        yaml_text = "strategy:\n  rsi_overbought_threshold: 50.0\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["rsi_overbought_threshold"] == 65.0  # default

    def test_value_100_accepted(self, tmp_path, monkeypatch):
        """100 は有効（フィルタ実質オフ）。"""
        yaml_text = "strategy:\n  rsi_overbought_threshold: 100.0\n"
        cfg = _load_cfg_with_yaml(yaml_text, tmp_path, monkeypatch)
        assert cfg["rsi_overbought_threshold"] == 100.0


class TestRsiFilterInGenerateSignals:
    """generate_signals の RSI 過熱フィルタ動作テスト。"""

    def _insert_feature_with_rsi(self, conn, code: str, d: date, rsi: float | None) -> None:
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev, rsi_14) "
            "VALUES (?, ?, 3.0, 3.0, -3.0, 3.0, 5.0, 3.0, ?)",
            [d, code, rsi],
        )

    def test_rsi_over_threshold_suppresses_buy(self, conn):
        """RSI > 70 の銘柄が BUY 対象から除外されること。"""
        import sqlite3

        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        self._insert_feature_with_rsi(conn, "1001", TARGET_DATE, rsi=75.0)
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, '1001', 1000, 1010, 990, 1000, 100000)",
            [TARGET_DATE],
        )
        sqlite_conn = sqlite3.connect(":memory:")
        from kabusys.execution.order_repository import init_orders_db, init_position_entries_db

        init_orders_db(sqlite_conn)
        init_position_entries_db(sqlite_conn)
        generate_signals(conn, TARGET_DATE, sqlite_conn=sqlite_conn)
        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date=? AND side='buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "1001" not in buy_codes

    def test_rsi_below_threshold_allows_buy(self, conn):
        """RSI <= 70 の銘柄は BUY 対象になること。"""
        import sqlite3

        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        self._insert_feature_with_rsi(conn, "1001", TARGET_DATE, rsi=65.0)
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, '1001', 1000, 1010, 990, 1000, 100000)",
            [TARGET_DATE],
        )
        sqlite_conn = sqlite3.connect(":memory:")
        from kabusys.execution.order_repository import init_orders_db, init_position_entries_db

        init_orders_db(sqlite_conn)
        init_position_entries_db(sqlite_conn)
        generate_signals(conn, TARGET_DATE, sqlite_conn=sqlite_conn)
        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date=? AND side='buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "1001" in buy_codes

    def test_rsi_none_allows_buy(self, conn):
        """RSI が NULL（データ不足）の場合は安全側で BUY を許可すること。"""
        import sqlite3

        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        self._insert_feature_with_rsi(conn, "1001", TARGET_DATE, rsi=None)
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, '1001', 1000, 1010, 990, 1000, 100000)",
            [TARGET_DATE],
        )
        sqlite_conn = sqlite3.connect(":memory:")
        from kabusys.execution.order_repository import init_orders_db, init_position_entries_db

        init_orders_db(sqlite_conn)
        init_position_entries_db(sqlite_conn)
        generate_signals(conn, TARGET_DATE, sqlite_conn=sqlite_conn)
        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date=? AND side='buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "1001" in buy_codes

    def test_rsi_at_threshold_allows_buy(self, conn):
        """RSI がちょうど閾値（65.0）の場合は BUY を許可すること（> のため境界値は許可）。"""
        import sqlite3

        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        self._insert_feature_with_rsi(conn, "1001", TARGET_DATE, rsi=65.0)
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, '1001', 1000, 1010, 990, 1000, 100000)",
            [TARGET_DATE],
        )
        sqlite_conn = sqlite3.connect(":memory:")
        from kabusys.execution.order_repository import init_orders_db, init_position_entries_db

        init_orders_db(sqlite_conn)
        init_position_entries_db(sqlite_conn)
        generate_signals(conn, TARGET_DATE, sqlite_conn=sqlite_conn)
        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date=? AND side='buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "1001" in buy_codes, "RSI=65.0（閾値ちょうど）は BUY 許可（> 判定のため）"


# ---------------------------------------------------------------------------
# 200MA バイナリフィルター / 出来高ブレイクアウトフィルター テスト (Issue #346)
# ---------------------------------------------------------------------------


def _insert_feature_with_values(
    conn,
    code: str,
    d: date,
    *,
    momentum_20: float = 3.0,
    momentum_60: float = 3.0,
    volatility_20: float = -3.0,
    volume_ratio: float = 3.0,
    per: float = 5.0,
    ma200_dev: float = 3.0,
) -> None:
    conn.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        [d, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev],
    )


class TestMa200Filter:
    """use_ma200_filter=True のとき MA200 下の銘柄の BUY を抑制する。"""

    def test_below_ma200_suppressed(self, conn):
        """use_ma200_filter=True → ma200_dev < 0 の銘柄の BUY を抑制する。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        _insert_feature_with_values(conn, "8001", TARGET_DATE, ma200_dev=-0.05)

        generate_signals(conn, TARGET_DATE, use_ma200_filter=True)

        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "8001" not in buy_codes

    def test_above_ma200_allowed(self, conn):
        """use_ma200_filter=True → ma200_dev >= 0 の銘柄の BUY を許可する。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        _insert_feature_with_values(conn, "8002", TARGET_DATE, ma200_dev=0.05)

        generate_signals(conn, TARGET_DATE, use_ma200_filter=True)

        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "8002" in buy_codes

    def test_filter_disabled_by_default(self, conn):
        """use_ma200_filter=False（デフォルト）→ ma200_dev < 0 でも BUY を許可する。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        _insert_feature_with_values(conn, "8003", TARGET_DATE, ma200_dev=-0.05)

        generate_signals(conn, TARGET_DATE)

        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "8003" in buy_codes

    def test_ma200_dev_zero_allowed(self, conn):
        """ma200_dev == 0.0 は MA200 と同値 → BUY を許可する（>= 0 判定）。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        _insert_feature_with_values(conn, "8004", TARGET_DATE, ma200_dev=0.0)

        generate_signals(conn, TARGET_DATE, use_ma200_filter=True)

        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "8004" in buy_codes


class TestVolumeBreakoutFilter:
    """volume_breakout_threshold が指定されると出来高比率が低い銘柄の BUY を抑制する。"""

    def test_low_volume_suppressed(self, conn):
        """volume_breakout_threshold=1.5 → volume_ratio=1.2 の銘柄の BUY を抑制する。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        _insert_feature_with_values(conn, "9001", TARGET_DATE, volume_ratio=1.2)

        generate_signals(conn, TARGET_DATE, volume_breakout_threshold=1.5)

        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "9001" not in buy_codes

    def test_high_volume_allowed(self, conn):
        """volume_breakout_threshold=1.5 → volume_ratio=2.0 の銘柄の BUY を許可する。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        _insert_feature_with_values(conn, "9002", TARGET_DATE, volume_ratio=2.0)

        generate_signals(conn, TARGET_DATE, volume_breakout_threshold=1.5)

        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "9002" in buy_codes

    def test_threshold_none_disabled(self, conn):
        """volume_breakout_threshold=None（デフォルト）→ volume_ratio=1.0 でも BUY 許可。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        _insert_feature_with_values(conn, "9003", TARGET_DATE, volume_ratio=1.0)

        generate_signals(conn, TARGET_DATE)

        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "9003" in buy_codes

    def test_volume_exactly_at_threshold_allowed(self, conn):
        """volume_ratio がちょうど閾値の場合は BUY を許可する（>= 判定）。"""
        from kabusys.strategy.signal_generator import generate_signals

        _insert_regime(conn, TARGET_DATE, "bull")
        _insert_breadth(conn, TARGET_DATE, breadth_stop=False)
        _insert_feature_with_values(conn, "9004", TARGET_DATE, volume_ratio=1.5)

        generate_signals(conn, TARGET_DATE, volume_breakout_threshold=1.5)

        buy_codes = [
            r[0]
            for r in conn.execute(
                "SELECT code FROM signals WHERE date = ? AND side = 'buy'", [TARGET_DATE]
            ).fetchall()
        ]
        assert "9004" in buy_codes
