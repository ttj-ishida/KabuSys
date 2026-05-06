"""tests/test_trailing_stop.py — トレーリングストップ（ATR×2）テスト"""

from __future__ import annotations

import inspect
from datetime import date, timedelta

import pytest

from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from kabusys.strategy.signal_generator import _atr_20d, _peak_close, generate_signals


def _weekdays_before(d: date, n: int) -> list[date]:
    """d の前の n 営業日（月〜金）を昇順で返す。"""
    result: list[date] = []
    cur = d - timedelta(days=1)
    while len(result) < n:
        if cur.weekday() < 5:
            result.insert(0, cur)
        cur -= timedelta(days=1)
    return result


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# _atr_20d ヘルパー
# ---------------------------------------------------------------------------


class TestAtr20d:
    def test_returns_correct_average(self, conn):
        """20営業日の履歴 + target_date の計 21 行があるとき ATR_20d を正しく計算する。

        high=1010, low=990, close=1000（前日 close も 1000）のとき
        TR = GREATEST(20, |1010-1000|, |990-1000|) = 20 → ATR = 20.0
        """
        code = "ATR1"
        target = date(2026, 4, 6)
        for d in _weekdays_before(target, 20) + [target]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, 1000.0, 1010.0, 990.0, 1000.0, 1000000)",
                [d, code],
            )
        result = _atr_20d(conn, code, target)
        assert result == pytest.approx(20.0)

    def test_returns_none_when_insufficient_data(self, conn):
        """履歴が 20 日未満（TR < 20 本）のとき None を返す。"""
        code = "ATR2"
        target = date(2026, 4, 6)
        # 10 days before + target = 11 rows → 10 TR values → None
        for d in _weekdays_before(target, 10) + [target]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, 1000.0, 1010.0, 990.0, 1000.0, 1000000)",
                [d, code],
            )
        result = _atr_20d(conn, code, target)
        assert result is None

    def test_returns_none_at_boundary_19_tr_values(self, conn):
        """TR が 19 本（境界値 -1）のとき None を返す。"""
        code = "ATR3"
        target = date(2026, 4, 6)
        # 19 days before + target = 20 rows → 19 TR values (oldest has NULL prev_close) → None
        for d in _weekdays_before(target, 19) + [target]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, 1000.0, 1010.0, 990.0, 1000.0, 1000000)",
                [d, code],
            )
        result = _atr_20d(conn, code, target)
        assert result is None


# ---------------------------------------------------------------------------
# _peak_close ヘルパー
# ---------------------------------------------------------------------------


class TestPeakClose:
    def test_returns_max_close_since_entry(self, conn):
        """エントリー日以降の最高 close を返す。"""
        code = "PEAK1"
        entry = date(2026, 4, 6)
        target = date(2026, 4, 8)
        conn.execute(
            "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, NULL)",
            [code, entry],
        )
        for d, c in [
            (date(2026, 4, 6), 100.0),
            (date(2026, 4, 7), 120.0),
            (date(2026, 4, 8), 110.0),
        ]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
                [d, code, c, c * 1.05, c * 0.95, c],
            )
        result = _peak_close(conn, code, target)
        assert result == pytest.approx(120.0)

    def test_returns_none_when_no_open_entry(self, conn):
        """オープンなエントリーが存在しない場合 None を返す。"""
        code = "PEAK2"
        target = date(2026, 4, 8)
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, ?, 100.0, 110.0, 90.0, 100.0, 1000000)",
            [target, code],
        )
        result = _peak_close(conn, code, target)
        assert result is None


# ---------------------------------------------------------------------------
# 統合テスト用ヘルパー
# ---------------------------------------------------------------------------

TARGET_DATE = date(2026, 4, 6)  # Monday


def _insert_prices_history(
    conn,
    code: str,
    base_close: float = 1000.0,
    spread: float = 20.0,
    n_history: int = 20,
) -> date:
    """TARGET_DATE の前 n_history 営業日分の価格を挿入し、最古の日付を返す。

    spread=20 (high=base+10, low=base-10) のとき、close が一定なら
    TR = GREATEST(20, 10, 10) = 20 → ATR_20d ≈ 20.0
    """
    history_dates = _weekdays_before(TARGET_DATE, n_history)
    for d in history_dates:
        c = base_close
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
            [d, code, c, c + spread / 2, c - spread / 2, c],
        )
    return history_dates[0]


def _insert_target_price(conn, code: str, close: float) -> None:
    """TARGET_DATE の価格を挿入する（高値 = close+10, 安値 = close-10）。"""
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
        [TARGET_DATE, code, close, close + 10, close - 10, close],
    )


def _setup_env(conn, code: str, close: float, avg_price: float = 850.0) -> None:
    """trailing_stop テストの共通セットアップ。

    - 20 日分の履歴（close=1000, spread=20 → ATR≈20, peak_close=1000）
    - TARGET_DATE の価格: close=close
    - avg_price=avg_price（850 < 1000=peak → 含み益条件を満たす）
    """
    entry_date = _insert_prices_history(conn, code)
    _insert_target_price(conn, code, close)
    conn.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, 0.5, 'bull')",
        [TARGET_DATE],
    )
    conn.execute(
        "INSERT INTO market_breadth "
        "(date, adv_decline_ratio, ma25_above_pct, breadth_stop) VALUES (?, 100.0, 0.5, false)",
        [TARGET_DATE],
    )
    conn.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, ?, 3.0, 3.0, 0.5, 3.0, 3.0, 3.0)",
        [TARGET_DATE, code],
    )
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, 100, ?)",
        [TARGET_DATE, code, avg_price],
    )
    conn.execute(
        "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, NULL)",
        [code, entry_date],
    )


def _sell_codes(conn, d: date) -> set[str]:
    rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'", [d]
    ).fetchall()
    return {r[0] for r in rows}


# ---------------------------------------------------------------------------
# trailing_stop 発動テスト
# ---------------------------------------------------------------------------


class TestTrailingStopFires:
    def test_fires_when_close_below_threshold(self, conn):
        """close < peak - 2×ATR のとき trailing_stop SELL が発生する。

        peak=1000, ATR≈24（target_date の大きな TR を含む）, threshold≈951
        close=900 < threshold → SELL が発生すること。
        """
        code = "TS_FIRE1"
        _setup_env(conn, code, close=900.0)
        generate_signals(conn, TARGET_DATE, trailing_stop_atr=2.0)
        assert code in _sell_codes(conn, TARGET_DATE)


class TestTrailingStopSuppressed:
    def test_no_sell_when_close_above_threshold(self, conn):
        """close が peak - 2×ATR より大きいとき SELL が発生しない。

        peak=1000, ATR≈20, threshold≈960
        close=995 > threshold → SELL が発生しないこと。
        """
        code = "TS_SUPP1"
        _setup_env(conn, code, close=995.0)
        generate_signals(conn, TARGET_DATE, trailing_stop_atr=2.0)
        assert code not in _sell_codes(conn, TARGET_DATE)


class TestTrailingStopNoProfitNoFire:
    def test_no_fire_when_peak_not_above_avg_price(self, conn):
        """peak_close <= avg_price のとき（含み益なし）trailing_stop は発動しない。

        avg_price=1001 > peak_close=1000 → 含み益条件を満たさないため trailing_stop スキップ。
        close=950: pnl_rate ≈ -5.1% → stop_loss 発動せず（>-8%）
                   close < peak - 2×ATR (≈960) → 含み益条件がなければ trailing_stop も発動せず
        スコアは features に存在するため score_drop も発動しない。
        """
        code = "TS_NOPROFIT"
        _setup_env(conn, code, close=950.0, avg_price=1001.0)
        generate_signals(conn, TARGET_DATE, trailing_stop_atr=2.0)
        assert code not in _sell_codes(conn, TARGET_DATE)


class TestTrailingStopBypassesMinHolding:
    def test_fires_despite_min_holding_days(self, conn):
        """held < min_holding_days であっても trailing_stop は発動する。"""
        code = "TS_BYPASS"
        _setup_env(conn, code, close=900.0)
        generate_signals(conn, TARGET_DATE, min_holding_days=30, trailing_stop_atr=2.0)
        assert code in _sell_codes(conn, TARGET_DATE)


class TestTrailingStopInBearRegime:
    def test_fires_in_bear_regime(self, conn):
        """Bear レジームでも trailing_stop が発動する。"""
        code = "TS_BEAR"
        entry_date = _insert_prices_history(conn, code)
        _insert_target_price(conn, code, 900.0)
        conn.execute(
            "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, -0.8, 'bear')",
            [TARGET_DATE],
        )
        conn.execute(
            "INSERT INTO market_breadth "
            "(date, adv_decline_ratio, ma25_above_pct, breadth_stop) VALUES (?, 100.0, 0.5, false)",
            [TARGET_DATE],
        )
        conn.execute(
            "INSERT INTO features "
            "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
            "VALUES (?, ?, 3.0, 3.0, 0.5, 3.0, 3.0, 3.0)",
            [TARGET_DATE, code],
        )
        conn.execute(
            "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, 100, 850.0)",
            [TARGET_DATE, code],
        )
        conn.execute(
            "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, NULL)",
            [code, entry_date],
        )
        generate_signals(conn, TARGET_DATE, trailing_stop_atr=2.0)
        assert code in _sell_codes(conn, TARGET_DATE)


# ---------------------------------------------------------------------------
# バリデーション
# ---------------------------------------------------------------------------


class TestTrailingStopValidation:
    def test_generate_signals_raises_on_zero(self, conn):
        with pytest.raises(ValueError, match="正の値"):
            generate_signals(conn, TARGET_DATE, trailing_stop_atr=0.0)

    def test_generate_signals_raises_on_negative(self, conn):
        with pytest.raises(ValueError, match="正の値"):
            generate_signals(conn, TARGET_DATE, trailing_stop_atr=-1.0)

    def test_run_backtest_raises_on_zero(self):
        c = init_schema(":memory:")
        try:
            with pytest.raises(ValueError, match="正の値"):
                run_backtest(
                    c,
                    start_date=date(2025, 1, 6),
                    end_date=date(2025, 1, 7),
                    trailing_stop_atr=0.0,
                )
        finally:
            c.close()


# ---------------------------------------------------------------------------
# シグネチャ・デフォルト値
# ---------------------------------------------------------------------------


class TestTrailingStopDefault:
    def test_generate_signals_has_trailing_stop_atr_param(self):
        sig = inspect.signature(generate_signals)
        assert "trailing_stop_atr" in sig.parameters

    def test_run_backtest_has_trailing_stop_atr_param(self):
        sig = inspect.signature(run_backtest)
        assert "trailing_stop_atr" in sig.parameters

    def test_generate_signals_default_is_none_sentinel(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["trailing_stop_atr"].default is None

    def test_run_backtest_default_is_2_0(self):
        sig = inspect.signature(run_backtest)
        assert sig.parameters["trailing_stop_atr"].default == pytest.approx(2.0)
