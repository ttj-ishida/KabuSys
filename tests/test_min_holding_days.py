"""tests/test_min_holding_days.py — min_holding_days パラメータ化テスト"""

from __future__ import annotations

import argparse
import contextlib
import inspect
import io
import sys
from datetime import date

import pytest

from kabusys.data.schema import init_schema
from kabusys.backtest.engine import run_backtest
from kabusys.strategy.signal_generator import generate_signals

# 月曜日を target_date として使用（weekday-based fallbackで営業日と判定される）
TARGET_DATE = date(2026, 4, 6)  # 月曜日


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


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
    """スコアが threshold 未満になる特徴量（score_drop SELL を誘発）を挿入する。"""
    c.execute(
        "INSERT INTO features "
        "(date, code, momentum_20, momentum_60, volatility_20, volume_ratio, per, ma200_dev) "
        "VALUES (?, ?, -3.0, -3.0, 3.0, -3.0, -3.0, -3.0)",
        [d, code],
    )


def _insert_price(c, code: str, d: date, close: float, open_: float = 100.0) -> None:
    c.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d, code, open_, close * 1.05, close * 0.95, close, 1000000],
    )


def _insert_position(
    c, code: str, d: date, avg_price: float = 1000.0, size: int = 100
) -> None:
    c.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, ?, ?, ?)",
        [d, code, size, avg_price],
    )


def _insert_position_entry(c, code: str, entry_date: date) -> None:
    c.execute(
        "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, NULL)",
        [code, entry_date],
    )


def _setup_sell_env(
    c, code: str, d: date, entry_date: date, avg_price: float = 1000.0
) -> None:
    """score_drop SELL 判定に必要なデータを一括挿入する（close > avg_price → ストップロスなし）。"""
    _insert_regime(c, d, label="bull")
    _insert_breadth(c, d, stop=False)
    _insert_feature_low_score(c, code, d)
    _insert_price(c, code, d, close=avg_price * 1.05)
    _insert_position(c, code, d, avg_price=avg_price)
    _insert_position_entry(c, code, entry_date=entry_date)


class TestMinHoldingDaysZero:
    def test_sell_generated_when_min_holding_days_0(self, conn):
        """min_holding_days=0 のとき、entry 当日でも score_drop SELL が生成される。"""
        code = "1111"
        _setup_sell_env(conn, code, TARGET_DATE, entry_date=TARGET_DATE)

        generate_signals(conn, TARGET_DATE, min_holding_days=0)

        rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [TARGET_DATE],
        ).fetchall()
        sell_codes = {r[0] for r in rows}
        assert code in sell_codes, (
            f"min_holding_days=0 のとき held=0 でも SELL が生成されるべき (got {sell_codes})"
        )


class TestMinHoldingDaysSuppressSell:
    def test_sell_suppressed_when_held_less_than_min(self, conn):
        """min_holding_days=5 のとき、entry 当日（held=0）の score_drop SELL は抑制される。"""
        code = "2222"
        _setup_sell_env(conn, code, TARGET_DATE, entry_date=TARGET_DATE)

        generate_signals(conn, TARGET_DATE, min_holding_days=5)

        rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [TARGET_DATE],
        ).fetchall()
        sell_codes = {r[0] for r in rows}
        assert code not in sell_codes, (
            f"min_holding_days=5 のとき held=0 では SELL が抑制されるべき (got {sell_codes})"
        )


class TestMinHoldingDaysBoundary:
    def test_sell_fires_when_held_equals_min_holding_days(self, conn):
        """held == min_holding_days のとき（境界値）、SELL が発生する（抑制されない）。"""
        # entry_date=月曜, target_date=火曜 → 連続する2営業日 → held=1
        entry_date = date(2026, 4, 6)  # 月曜
        target_date = date(2026, 4, 7)  # 火曜
        code = "5555"
        _insert_regime(conn, target_date, label="bull")
        _insert_breadth(conn, target_date, stop=False)
        _insert_feature_low_score(conn, code, target_date)
        _insert_price(conn, code, target_date, close=1050.0)
        _insert_position(conn, code, target_date, avg_price=1000.0)
        _insert_position_entry(conn, code, entry_date=entry_date)

        generate_signals(conn, target_date, min_holding_days=1)

        rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [target_date],
        ).fetchall()
        sell_codes = {r[0] for r in rows}
        assert code in sell_codes, (
            f"held=1 == min_holding_days=1 のとき SELL が発生すべき (got {sell_codes})"
        )


class TestMinHoldingDaysExceptions:
    def test_stop_loss_fires_regardless_of_min_holding_days(self, conn):
        """ストップロス条件を満たすとき、min_holding_days=5 でも entry 当日に SELL が発生する。"""
        code = "3333"
        avg_price = 1000.0
        _insert_regime(conn, TARGET_DATE, label="bull")
        _insert_breadth(conn, TARGET_DATE, stop=False)
        _insert_feature_low_score(conn, code, TARGET_DATE)
        # close が avg_price の -10% → ストップロス発動
        _insert_price(conn, code, TARGET_DATE, close=avg_price * 0.90)
        _insert_position(conn, code, TARGET_DATE, avg_price=avg_price)
        _insert_position_entry(conn, code, entry_date=TARGET_DATE)

        generate_signals(conn, TARGET_DATE, min_holding_days=5)

        rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [TARGET_DATE],
        ).fetchall()
        sell_codes = {r[0] for r in rows}
        assert code in sell_codes, (
            f"ストップロス条件のとき min_holding_days=5 でも SELL が発生すべき (got {sell_codes})"
        )

    def test_bear_regime_bypasses_min_holding_days(self, conn):
        """Bear レジームのとき、min_holding_days=5 でも entry 当日に score_drop SELL が発生する。"""
        code = "4444"
        avg_price = 1000.0
        _insert_regime(conn, TARGET_DATE, label="bear")
        _insert_breadth(conn, TARGET_DATE, stop=False)
        _insert_feature_low_score(conn, code, TARGET_DATE)
        _insert_price(conn, code, TARGET_DATE, close=avg_price * 1.05)
        _insert_position(conn, code, TARGET_DATE, avg_price=avg_price)
        _insert_position_entry(conn, code, entry_date=TARGET_DATE)

        generate_signals(conn, TARGET_DATE, min_holding_days=5)

        rows = conn.execute(
            "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
            [TARGET_DATE],
        ).fetchall()
        sell_codes = {r[0] for r in rows}
        assert code in sell_codes, (
            f"Bear レジームでは min_holding_days=5 でも SELL が発生すべき (got {sell_codes})"
        )


class TestMinHoldingDaysValidation:
    def test_generate_signals_raises_on_negative(self, conn):
        """generate_signals に負数を渡すと ValueError が発生する。"""
        with pytest.raises(ValueError, match="0 以上"):
            generate_signals(conn, TARGET_DATE, min_holding_days=-1)

    def test_run_backtest_raises_on_negative(self):
        """`run_backtest` に負数を渡すと ValueError が発生する。"""
        conn = init_schema(":memory:")
        try:
            with pytest.raises(ValueError, match="0 以上"):
                run_backtest(
                    conn,
                    start_date=date(2025, 1, 6),
                    end_date=date(2025, 1, 7),
                    min_holding_days=-1,
                )
        finally:
            conn.close()

    def test_cli_rejects_negative_min_holding_days(self):
        """CLI で --min-holding-days -1 を渡すと argparse エラーになる。"""
        from kabusys.backtest.run import _non_negative_int

        with pytest.raises(argparse.ArgumentTypeError):
            _non_negative_int("-1")

    def test_cli_accepts_zero(self):
        """CLI で --min-holding-days 0 は有効な値として受け付ける。"""
        from kabusys.backtest.run import _non_negative_int

        assert _non_negative_int("0") == 0


class TestRunBacktestMinHoldingDaysParam:
    def test_run_backtest_has_min_holding_days_param(self):
        """`run_backtest()` が `min_holding_days` 引数を持つ。"""
        sig = inspect.signature(run_backtest)
        assert "min_holding_days" in sig.parameters

    def test_run_backtest_accepts_min_holding_days_0(self):
        """`min_holding_days=0` を渡して BacktestResult が返る。"""
        conn = init_schema(":memory:")
        try:
            result = run_backtest(
                conn,
                start_date=date(2025, 1, 6),
                end_date=date(2025, 1, 7),
                min_holding_days=0,
            )
        finally:
            conn.close()
        assert result is not None
        assert hasattr(result, "metrics")


class TestCliMinHoldingDaysArgument:
    def test_help_contains_min_holding_days(self):
        """--help 出力に '--min-holding-days' が含まれる。"""
        import kabusys.backtest.run as run_module

        orig_argv = sys.argv[:]
        try:
            sys.argv = ["prog", "--help"]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                try:
                    run_module.main()
                except SystemExit:
                    pass
            output = buf.getvalue()
        finally:
            sys.argv = orig_argv

        assert "--min-holding-days" in output, (
            f"--min-holding-days が --help に含まれていない。出力: {output[:500]}"
        )

    def test_help_mentions_bear_regime(self):
        """--help 出力に Bear レジーム例外への言及が含まれる。"""
        import kabusys.backtest.run as run_module

        orig_argv = sys.argv[:]
        try:
            sys.argv = ["prog", "--help"]
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                try:
                    run_module.main()
                except SystemExit:
                    pass
            output = buf.getvalue()
        finally:
            sys.argv = orig_argv

        assert "bear" in output.lower(), (
            f"--help に bear regime への言及がない。出力: {output[:500]}"
        )


class TestMinHoldingDaysDefault:
    def test_run_backtest_default_is_5(self):
        """`run_backtest()` の min_holding_days デフォルト値が 5 であること。"""
        sig = inspect.signature(run_backtest)
        param = sig.parameters["min_holding_days"]
        assert param.default == 5, (
            f"run_backtest の min_holding_days デフォルト値は 5 であるべき (got {param.default})"
        )

    def test_generate_signals_uses_none_sentinel_for_min_holding_days(self):
        """`generate_signals` の min_holding_days デフォルト値は None（config-driven sentinel）であること。"""
        sig_gs = inspect.signature(generate_signals)
        default_gs = sig_gs.parameters["min_holding_days"].default
        assert default_gs is None, (
            f"generate_signals の min_holding_days デフォルト値は None (config-driven) であるべき (got {default_gs})"
        )
