"""tests/test_dynamic_trailing_stop.py — 多段階トレーリングストップ テスト"""

from __future__ import annotations

import inspect
from datetime import date, timedelta

import pytest

from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from kabusys.strategy.signal_generator import generate_signals


class TestDynamicTrailingStopSignature:
    def test_generate_signals_has_dynamic_trailing_stop(self):
        sig = inspect.signature(generate_signals)
        assert "dynamic_trailing_stop" in sig.parameters

    def test_generate_signals_dynamic_trailing_stop_default_false(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["dynamic_trailing_stop"].default is False

    def test_generate_signals_has_trail_profit_gate_atr(self):
        sig = inspect.signature(generate_signals)
        assert "trail_profit_gate_atr" in sig.parameters

    def test_generate_signals_trail_profit_gate_atr_default_1_5(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["trail_profit_gate_atr"].default == pytest.approx(1.5)

    def test_generate_signals_has_trail_stage2_mult(self):
        sig = inspect.signature(generate_signals)
        assert "trail_stage2_mult" in sig.parameters

    def test_generate_signals_trail_stage2_mult_default_1_5(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["trail_stage2_mult"].default == pytest.approx(1.5)

    def test_generate_signals_has_trail_stage3_mult(self):
        sig = inspect.signature(generate_signals)
        assert "trail_stage3_mult" in sig.parameters

    def test_generate_signals_trail_stage3_mult_default_1_0(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["trail_stage3_mult"].default == pytest.approx(1.0)

    def test_run_backtest_has_dynamic_trailing_stop(self):
        sig = inspect.signature(run_backtest)
        assert "dynamic_trailing_stop" in sig.parameters

    def test_run_backtest_dynamic_trailing_stop_default_false(self):
        sig = inspect.signature(run_backtest)
        assert sig.parameters["dynamic_trailing_stop"].default is False

    def test_run_backtest_has_trail_profit_gate_atr(self):
        sig = inspect.signature(run_backtest)
        assert "trail_profit_gate_atr" in sig.parameters

    def test_run_backtest_has_trail_stage2_mult(self):
        sig = inspect.signature(run_backtest)
        assert "trail_stage2_mult" in sig.parameters

    def test_run_backtest_has_trail_stage3_mult(self):
        sig = inspect.signature(run_backtest)
        assert "trail_stage3_mult" in sig.parameters


TARGET_DATE = date(2026, 4, 6)  # Monday


def _weekdays_before(d: date, n: int) -> list[date]:
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


def _setup_stage_env(
    conn,
    code: str,
    close_target: float,
    avg_price: float,
    held_days: int,
) -> None:
    """多段階トレーリングストップ テスト用セットアップ。

    - held_days 分だけ前の日を entry_date として position_entries に挿入
    - 20 日分の価格履歴（close=1000, high=1010, low=990 → ATR≈20）
    - peak_close ≈ 1000（history が一定のため）
    """
    history_dates = _weekdays_before(TARGET_DATE, 20)
    entry_date = _weekdays_before(TARGET_DATE, held_days)[0]

    for d in history_dates:
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, ?, 1000.0, 1010.0, 990.0, 1000.0, 1000000)",
            [d, code],
        )
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
        [TARGET_DATE, code, close_target, close_target + 10, close_target - 10, close_target],
    )
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
    rows = conn.execute("SELECT code FROM signals WHERE date = ? AND side = 'sell'", [d]).fetchall()
    return {r[0] for r in rows}


class TestDynamicTrailingStopDisabled:
    def test_disabled_uses_original_mult(self, conn):
        """dynamic_trailing_stop=False のとき Stage 2 条件を満たしても元の乗数 2.0 を使用する。

        peak=1000, ATR≈20, avg_price=850, close=965, held=10 (Stage 2)
        profit = 965-850=115 >= 1.5*20=30 → Stage 2 条件 MET
        Stage 2 mult=1.5: threshold=1000-1.5*20=970, 965<970 → fire
        Original mult=2.0: threshold=1000-2.0*20=960, 965>960 → no fire
        dynamic=False → mult stays 2.0 → does NOT fire
        """
        code = "DTS_DISABLED"
        _setup_stage_env(conn, code, close_target=965.0, avg_price=850.0, held_days=10)
        generate_signals(conn, TARGET_DATE, trailing_stop_atr=2.0, dynamic_trailing_stop=False)
        assert code not in _sell_codes(conn, TARGET_DATE)


class TestDynamicTrailingStopStage1:
    def test_stage1_uses_original_mult(self, conn):
        """Stage 1（held=3 日）では dynamic=True でも元の乗数 2.0 を維持する。

        peak=1000, ATR≈20, avg_price=850, close=965, held=3 (Stage 1: < 6)
        mult=2.0: threshold=960, 965>960 → does NOT fire
        """
        code = "DTS_STAGE1"
        _setup_stage_env(conn, code, close_target=965.0, avg_price=850.0, held_days=3)
        generate_signals(
            conn,
            TARGET_DATE,
            trailing_stop_atr=2.0,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.5,
            trail_stage3_mult=1.0,
        )
        assert code not in _sell_codes(conn, TARGET_DATE)


class TestDynamicTrailingStopStage2:
    def test_stage2_fires_when_profit_condition_met(self, conn):
        """Stage 2（held=10）・含み益条件 MET → 乗数 1.5 で発火する。

        peak=1000, ATR≈20, avg_price=850, close=965, held=10 (Stage 2: 6<=10<21)
        profit = 965-850=115 >= 1.5*20=30 → Stage 2 MET → mult=1.5
        threshold=1000-1.5*20=970, 965<970 → FIRES
        """
        code = "DTS_STAGE2_FIRE"
        _setup_stage_env(conn, code, close_target=965.0, avg_price=850.0, held_days=10)
        generate_signals(
            conn,
            TARGET_DATE,
            trailing_stop_atr=2.0,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.5,
            trail_stage3_mult=1.0,
        )
        assert code in _sell_codes(conn, TARGET_DATE)

    def test_stage2_no_fire_when_profit_condition_not_met(self, conn):
        """Stage 2（held=10）・含み益条件 NOT MET → 乗数 2.0 のまま発火しない。

        peak=1000, ATR≈20, avg_price=940, close=965, held=10 (Stage 2)
        profit = 965-940=25 < 1.5*20=30 → Stage 2 NOT MET → mult stays 2.0
        threshold=1000-2.0*20=960, 965>960 → does NOT fire
        """
        code = "DTS_STAGE2_NOFIRE"
        _setup_stage_env(conn, code, close_target=965.0, avg_price=940.0, held_days=10)
        generate_signals(
            conn,
            TARGET_DATE,
            trailing_stop_atr=2.0,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.5,
            trail_stage3_mult=1.0,
        )
        assert code not in _sell_codes(conn, TARGET_DATE)


class TestDynamicTrailingStopStage3:
    def test_stage3_fires_unconditionally(self, conn):
        """Stage 3（held=25 日）→ 含み益条件に関わらず乗数 1.0 で発火する。

        peak=1000, ATR≈20, avg_price=850, close=975, held=25 (Stage 3: >=21)
        mult=1.0: threshold=1000-1.0*20=980, 975<980 → FIRES
        mult=2.0 なら: threshold=960, 975>960 → fire しない
        """
        code = "DTS_STAGE3"
        _setup_stage_env(conn, code, close_target=975.0, avg_price=850.0, held_days=25)
        generate_signals(
            conn,
            TARGET_DATE,
            trailing_stop_atr=2.0,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.5,
            trail_stage3_mult=1.0,
        )
        assert code in _sell_codes(conn, TARGET_DATE)

    def test_stage3_fires_even_without_profit_condition(self, conn):
        """Stage 3 では profit_gate 条件を満たさなくても発火する。

        peak=1000, ATR≈20, avg_price=960, close=975, held=25 (Stage 3)
        profit = 975-960=15 < 1.5*20=30 → profit gate NOT met
        だが Stage 3 は無条件 → mult=1.0 → threshold=980, 975<980 → FIRES
        """
        code = "DTS_STAGE3_NO_PROFIT"
        _setup_stage_env(conn, code, close_target=975.0, avg_price=960.0, held_days=25)
        generate_signals(
            conn,
            TARGET_DATE,
            trailing_stop_atr=2.0,
            dynamic_trailing_stop=True,
            trail_profit_gate_atr=1.5,
            trail_stage2_mult=1.5,
            trail_stage3_mult=1.0,
        )
        assert code in _sell_codes(conn, TARGET_DATE)
