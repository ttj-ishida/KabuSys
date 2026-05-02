"""tests/test_time_exit.py — max_holding_days（時間決済）パラメータ化テスト"""

from __future__ import annotations

import inspect
from datetime import date

import pytest

from kabusys.backtest.engine import run_backtest
from kabusys.data.schema import init_schema
from kabusys.strategy.signal_generator import generate_signals

TARGET_DATE = date(2026, 4, 6)  # 月曜日（weekday-based fallback で営業日と判定）


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _insert_regime(c, d: date, label: str = "bull") -> None:
    score = 0.5 if label == "bull" else -0.5
    c.execute(
        "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
        [d, score, label],
    )


def _insert_breadth(c, d: date, stop: bool = False) -> None:
    c.execute(
        "INSERT INTO market_breadth (date, adv_decline_ratio, ma25_above_pct, breadth_stop) "
        "VALUES (?, ?, ?, ?)",
        [d, 100.0, 0.5, stop],
    )


def _insert_feature_low_score(c, code: str, d: date) -> None:
    c.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, ?, -3.0, -3.0, 3.0, -3.0, -3.0, -3.0)",
        [d, code],
    )


def _insert_feature_high_score(c, code: str, d: date) -> None:
    c.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, ?, 3.0, 3.0, 0.5, 3.0, 3.0, 3.0)",
        [d, code],
    )


def _insert_price(c, code: str, d: date, close: float, open_: float = 100.0) -> None:
    c.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d, code, open_, close * 1.05, close * 0.95, close, 1_000_000],
    )


def _insert_position(c, code: str, d: date, avg_price: float = 1000.0) -> None:
    c.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, ?, ?)",
        [d, code, 100, avg_price],
    )


def _insert_position_entry(c, code: str, entry_date: date) -> None:
    c.execute(
        "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, NULL)",
        [code, entry_date],
    )


def _setup_holding_env(
    c,
    code: str,
    target_date: date,
    entry_date: date,
    avg_price: float = 1000.0,
    high_score: bool = False,
) -> None:
    """時間決済判定に必要なデータを一括挿入（close > avg_price → ストップロスなし）。"""
    _insert_regime(c, target_date, label="bull")
    _insert_breadth(c, target_date, stop=False)
    if high_score:
        _insert_feature_high_score(c, code, target_date)
    else:
        _insert_feature_low_score(c, code, target_date)
    _insert_price(c, code, target_date, close=avg_price * 1.05)
    _insert_position(c, code, target_date, avg_price=avg_price)
    _insert_position_entry(c, code, entry_date=entry_date)


def _sell_codes(c, d: date) -> set[str]:
    rows = c.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'", [d]
    ).fetchall()
    return {r[0] for r in rows}


# ---------------------------------------------------------------------------
# time_exit が発火する基本ケース
# ---------------------------------------------------------------------------


class TestTimeExitFires:
    def test_sell_generated_when_held_equals_max(self, conn):
        """held == max_holding_days のとき time_exit SELL が発生する（境界値）。"""
        # entry=月(6) target=火(7) → held=1、max=1
        entry_date = date(2026, 4, 6)
        target_date = date(2026, 4, 7)
        code = "1001"
        _setup_holding_env(
            conn, code, target_date, entry_date=entry_date, high_score=True
        )

        generate_signals(conn, target_date, max_holding_days=1)

        assert code in _sell_codes(conn, target_date), (
            "held=1==max のとき SELL が発生すべき"
        )

    def test_sell_generated_when_held_exceeds_max(self, conn):
        """held > max_holding_days のときも time_exit SELL が発生する。"""
        # entry=月(6) target=水(8) → held=2、max=1
        entry_date = date(2026, 4, 6)
        target_date = date(2026, 4, 8)
        code = "1002"
        _setup_holding_env(
            conn, code, target_date, entry_date=entry_date, high_score=True
        )

        generate_signals(conn, target_date, max_holding_days=1)

        assert code in _sell_codes(conn, target_date), (
            "held=2 > max=1 のとき SELL が発生すべき"
        )


# ---------------------------------------------------------------------------
# time_exit が抑制されるケース
# ---------------------------------------------------------------------------


class TestTimeExitSuppressed:
    def test_no_sell_when_held_less_than_max(self, conn):
        """held < max_holding_days かつ score 高のとき SELL は発生しない。"""
        # entry=月(6) target=火(7) → held=1、max=5
        entry_date = date(2026, 4, 6)
        target_date = date(2026, 4, 7)
        code = "2001"
        _setup_holding_env(
            conn, code, target_date, entry_date=entry_date, high_score=True
        )

        generate_signals(conn, target_date, max_holding_days=5)

        assert code not in _sell_codes(conn, target_date), (
            "held=1 < max=5 かつ score 高のとき SELL は発生しないべき"
        )


# ---------------------------------------------------------------------------
# time_exit は min_holding_days を無視する
# ---------------------------------------------------------------------------


class TestTimeExitBypassesMinHolding:
    def test_time_exit_fires_even_if_held_less_than_min_holding_days(self, conn):
        """held >= max のとき、held < min_holding_days であっても time_exit SELL が発生する。"""
        # entry=月(6) target=火(7) → held=1
        # min_holding_days=10（通常なら抑制）、max_holding_days=1（時間超過）
        entry_date = date(2026, 4, 6)
        target_date = date(2026, 4, 7)
        code = "3001"
        _setup_holding_env(
            conn, code, target_date, entry_date=entry_date, high_score=True
        )

        generate_signals(conn, target_date, min_holding_days=10, max_holding_days=1)

        assert code in _sell_codes(conn, target_date), (
            "max_holding_days=1 のとき min_holding_days=10 でも time_exit SELL が発生すべき"
        )


# ---------------------------------------------------------------------------
# ストップロスは time_exit より先に処理される
# ---------------------------------------------------------------------------


class TestTimeExitPriority:
    def test_stop_loss_fires_alongside_time_exit_conditions(self, conn):
        """ストップロスと時間超過が同時に成立するとき SELL シグナルが生成される。"""
        # ストップロスが優先処理されシグナルは1件（signals PK: date, code, side）
        entry_date = date(2026, 4, 6)
        target_date = date(2026, 4, 7)
        code = "4001"
        avg_price = 1000.0
        _insert_regime(conn, target_date, label="bull")
        _insert_breadth(conn, target_date, stop=False)
        _insert_feature_low_score(conn, code, target_date)
        # close が -10% → ストップロス発動
        _insert_price(conn, code, target_date, close=avg_price * 0.90)
        _insert_position(conn, code, target_date, avg_price=avg_price)
        _insert_position_entry(conn, code, entry_date=entry_date)

        generate_signals(conn, target_date, max_holding_days=1)

        # ストップロスで SELL が発生し、重複は PK により排除される
        assert code in _sell_codes(conn, target_date)
        count = conn.execute(
            "SELECT COUNT(*) FROM signals WHERE date=? AND code=? AND side='sell'",
            [target_date, code],
        ).fetchone()[0]
        assert count == 1, "同一銘柄の SELL シグナルは1件のみ"


# ---------------------------------------------------------------------------
# Bear レジームでも time_exit は発火する
# ---------------------------------------------------------------------------


class TestTimeExitInBearRegime:
    def test_time_exit_fires_in_bear_regime(self, conn):
        """Bear レジームであっても held >= max_holding_days のとき time_exit SELL が発生する。"""
        # Bear レジームでは min_holding_days チェックがスキップされるが
        # time_exit（max_holding_days）は Bear 中でも発火することを確認
        entry_date = date(2026, 4, 6)
        target_date = date(2026, 4, 7)
        code = "5001"
        conn.execute(
            "INSERT INTO market_regime (date, regime_score, regime_label) VALUES (?, ?, ?)",
            [target_date, -0.8, "bear"],
        )
        _insert_breadth(conn, target_date, stop=False)
        _insert_feature_high_score(conn, code, target_date)
        _insert_price(conn, code, target_date, close=1050.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        _insert_position_entry(conn, code, entry_date=entry_date)

        generate_signals(conn, target_date, max_holding_days=1)

        assert code in _sell_codes(conn, target_date), (
            "Bear レジームでも held >= max_holding_days のとき time_exit SELL が発生すべき"
        )


# ---------------------------------------------------------------------------
# バリデーション
# ---------------------------------------------------------------------------


class TestMaxHoldingDaysValidation:
    def test_generate_signals_raises_on_zero(self, conn):
        """generate_signals に max_holding_days=0 を渡すと ValueError が発生する。"""
        with pytest.raises(ValueError, match="1 以上"):
            generate_signals(conn, TARGET_DATE, max_holding_days=0)

    def test_generate_signals_raises_on_negative(self, conn):
        """generate_signals に負数を渡すと ValueError が発生する。"""
        with pytest.raises(ValueError, match="1 以上"):
            generate_signals(conn, TARGET_DATE, max_holding_days=-1)

    def test_run_backtest_raises_on_zero(self):
        """run_backtest に max_holding_days=0 を渡すと ValueError が発生する。"""
        conn = init_schema(":memory:")
        try:
            with pytest.raises(ValueError, match="1 以上"):
                run_backtest(
                    conn,
                    start_date=date(2025, 1, 6),
                    end_date=date(2025, 1, 7),
                    max_holding_days=0,
                )
        finally:
            conn.close()


# ---------------------------------------------------------------------------
# シグネチャ・デフォルト値
# ---------------------------------------------------------------------------


class TestMaxHoldingDaysDefault:
    def test_generate_signals_has_max_holding_days_param(self):
        sig = inspect.signature(generate_signals)
        assert "max_holding_days" in sig.parameters

    def test_run_backtest_has_max_holding_days_param(self):
        sig = inspect.signature(run_backtest)
        assert "max_holding_days" in sig.parameters

    def test_generate_signals_default_is_60(self):
        sig = inspect.signature(generate_signals)
        assert sig.parameters["max_holding_days"].default == 60

    def test_run_backtest_default_is_60(self):
        sig = inspect.signature(run_backtest)
        assert sig.parameters["max_holding_days"].default == 60

    def test_run_backtest_accepts_max_holding_days(self):
        conn = init_schema(":memory:")
        try:
            result = run_backtest(
                conn,
                start_date=date(2025, 1, 6),
                end_date=date(2025, 1, 7),
                max_holding_days=60,
            )
        finally:
            conn.close()
        assert result is not None
