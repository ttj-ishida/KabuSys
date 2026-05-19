"""tests/test_drawdown_stop_timeout.py

Issue #350: portfolio_drawdown_stop_timeout_days パラメータのテスト。
ドローダウンストップ発動後 N 日経過で自動リセットする機構。
"""

from __future__ import annotations

import inspect
from datetime import date, timedelta

import pytest

# ---------------------------------------------------------------------------
# ヘルパー: 最小限の DB セットアップ
# ---------------------------------------------------------------------------


def _make_conn_with_drawdown(initial_cash: float, drop_ratio: float, n_days: int):
    """
    n_days 分の取引日を持ち、初日から close が initial_cash * (1 - drop_ratio) 相当の
    価格に設定した最小 DB を返す。

    drawdown テスト用にシンプルな構造を用意する:
    - topix_daily: MA 不要（TOPIX ガード無効のまま）
    - market_calendar: n_days 分の取引日
    - features / signals: 空（シグナルなし → BUY は発生しない前提）
    """
    from kabusys.data.schema import init_schema

    conn = init_schema(":memory:")

    base = date(2025, 1, 6)
    for i in range(n_days):
        d = base + timedelta(days=i)
        conn.execute(
            "INSERT INTO market_calendar (date, is_trading_day) VALUES (?, ?)",
            [d, True],
        )
        conn.execute(
            "INSERT INTO topix_daily (date, open, high, low, close) VALUES (?, ?, ?, ?, ?)",
            [d, 2500.0, 2500.0, 2500.0, 2500.0],
        )

    return conn


# ---------------------------------------------------------------------------
# パラメータ受け入れ / バリデーションテスト
# ---------------------------------------------------------------------------


class TestPortfolioDrawdownStopTimeoutParam:
    def test_run_backtest_accepts_timeout_param(self):
        """`run_backtest()` が portfolio_drawdown_stop_timeout_days を受け取れること。"""
        from kabusys.backtest.engine import run_backtest

        assert "portfolio_drawdown_stop_timeout_days" in inspect.signature(run_backtest).parameters

    def test_timeout_param_default_is_none(self):
        """デフォルト値が None であること（タイムアウト無効）。"""
        from kabusys.backtest.engine import run_backtest

        param = inspect.signature(run_backtest).parameters["portfolio_drawdown_stop_timeout_days"]
        assert param.default is None

    def test_timeout_zero_raises(self):
        """timeout_days=0 は ValueError。"""
        from kabusys.backtest.engine import run_backtest

        with pytest.raises(ValueError, match="portfolio_drawdown_stop_timeout_days"):
            run_backtest(
                conn=None,  # type: ignore[arg-type]
                start_date=date(2025, 1, 6),
                end_date=date(2025, 1, 10),
                initial_cash=1_000_000,
                portfolio_drawdown_stop_timeout_days=0,
            )

    def test_timeout_negative_raises(self):
        """timeout_days=-1 は ValueError。"""
        from kabusys.backtest.engine import run_backtest

        with pytest.raises(ValueError, match="portfolio_drawdown_stop_timeout_days"):
            run_backtest(
                conn=None,  # type: ignore[arg-type]
                start_date=date(2025, 1, 6),
                end_date=date(2025, 1, 10),
                initial_cash=1_000_000,
                portfolio_drawdown_stop_timeout_days=-1,
            )

    def test_timeout_one_is_valid(self):
        """timeout_days=1 はバリデーションを通過する（ValueError が上がらないこと）。"""
        from kabusys.backtest.engine import run_backtest

        # timeout バリデーションエラーが発生しないことを確認する
        # （conn=None でもバリデーションは先に完了するため、ValueError(timeout) は発生しない）
        try:
            run_backtest(
                conn=None,  # type: ignore[arg-type]
                start_date=date(2025, 1, 6),
                end_date=date(2025, 1, 10),
                initial_cash=1_000_000,
                portfolio_drawdown_stop_timeout_days=1,
            )
        except Exception as e:
            assert "portfolio_drawdown_stop_timeout_days" not in str(e)


# ---------------------------------------------------------------------------
# CLI テスト
# ---------------------------------------------------------------------------


class TestCliHasTimeoutArg:
    def test_run_py_cli_has_timeout_arg(self):
        """kabusys.backtest.run の argparse に --portfolio-drawdown-stop-timeout が定義されていること。"""
        import argparse
        import importlib
        from unittest.mock import patch

        captured: list[argparse.ArgumentParser] = []

        def capturing_parse(self, args=None, namespace=None):
            captured.append(self)
            raise SystemExit(0)

        with patch.object(argparse.ArgumentParser, "parse_args", capturing_parse):
            try:
                import kabusys.backtest.run as run_module

                importlib.reload(run_module)
                run_module.main()
            except SystemExit:
                pass

        assert captured, "ArgumentParser が生成されなかった"
        actions = {a.dest for a in captured[0]._actions}
        assert "portfolio_drawdown_stop_timeout_days" in actions, (
            f"--portfolio-drawdown-stop-timeout が argparse に定義されていない: {actions}"
        )


# ---------------------------------------------------------------------------
# タイムアウトリセット機能テスト
# ---------------------------------------------------------------------------


class TestDrawdownStopTimeout:
    """タイムアウトリセット機能の挙動テスト。"""

    def _run_minimal(self, conn, timeout_days, stop_pct=0.05, n_days=10):
        """シグナルなし（BUY0件）でバックテストを実行し、BacktestResult を返す。"""
        from kabusys.backtest.engine import run_backtest

        base = date(2025, 1, 6)
        return run_backtest(
            conn=conn,
            start_date=base,
            end_date=base + timedelta(days=n_days - 1),
            initial_cash=1_000_000,
            portfolio_drawdown_stop_pct=stop_pct,
            portfolio_drawdown_stop_timeout_days=timeout_days,
        )

    def test_no_timeout_completes_without_error(self):
        """timeout=None のとき（デフォルト）エラーなく完了する。"""
        conn = _make_conn_with_drawdown(1_000_000, 0.0, 10)
        result = self._run_minimal(conn, timeout_days=None)
        assert result is not None

    def test_with_timeout_completes_without_error(self):
        """timeout=30 のとき（タイムアウト有）エラーなく完了する。"""
        conn = _make_conn_with_drawdown(1_000_000, 0.0, 10)
        result = self._run_minimal(conn, timeout_days=30)
        assert result is not None

    def test_timeout_param_recorded_in_params_json(self):
        """BacktestResult.params に portfolio_drawdown_stop_timeout_days が記録されること。"""
        from kabusys.backtest.engine import run_backtest

        conn = _make_conn_with_drawdown(1_000_000, 0.0, 5)
        base = date(2025, 1, 6)
        result = run_backtest(
            conn=conn,
            start_date=base,
            end_date=base + timedelta(days=4),
            initial_cash=1_000_000,
            portfolio_drawdown_stop_pct=0.10,
            portfolio_drawdown_stop_timeout_days=60,
        )
        assert result.params.get("portfolio_drawdown_stop_timeout_days") == 60
