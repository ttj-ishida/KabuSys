"""tests/test_backtest_engine_params.py

Issue #344: topix_daily が in-memory DB にコピーされない / threshold・topix_* が
run_backtest() に渡せないバグの回帰テスト。
"""

from datetime import date, timedelta

import pytest


@pytest.fixture
def source_conn():
    """topix_daily が揃ったソース DB。"""
    from kabusys.data.schema import init_schema

    conn = init_schema(":memory:")

    conn.executemany(
        "INSERT INTO market_calendar (date, is_trading_day) VALUES (?, ?)",
        [(date(2025, 1, 6) + timedelta(days=i), True) for i in range(5)],
    )

    for i in range(220):
        d = date(2024, 6, 10) + timedelta(days=i)
        conn.execute(
            "INSERT INTO topix_daily (date, open, high, low, close) VALUES (?, ?, ?, ?, ?)",
            [d, 2500.0, 2510.0, 2490.0, 2500.0],
        )

    yield conn
    conn.close()


def test_build_backtest_conn_copies_topix_daily(source_conn):
    """_build_backtest_conn() が topix_daily を in-memory DB にコピーすること。"""
    from kabusys.backtest.engine import _build_backtest_conn

    bt_conn = _build_backtest_conn(
        source_conn,
        start_date=date(2025, 1, 6),
        end_date=date(2025, 1, 10),
        ai_enabled=False,
    )
    try:
        row = bt_conn.execute("SELECT COUNT(*) FROM topix_daily").fetchone()
        assert row is not None
        assert row[0] > 0, "topix_daily が in-memory DB にコピーされていない"
    finally:
        bt_conn.close()


def test_run_backtest_accepts_threshold_param():
    """run_backtest() が threshold パラメータを受け取れること。"""
    import inspect

    from kabusys.backtest.engine import run_backtest

    sig = inspect.signature(run_backtest)
    assert "threshold" in sig.parameters, "run_backtest() に threshold パラメータが存在しない"


def test_run_backtest_accepts_topix_params():
    """run_backtest() が topix_size_multiplier_weak_bear / topix_size_multiplier_strong_bear を受け取れること。"""
    import inspect

    from kabusys.backtest.engine import run_backtest

    sig = inspect.signature(run_backtest)
    assert "topix_size_multiplier_weak_bear" in sig.parameters, (
        "run_backtest() に topix_size_multiplier_weak_bear パラメータが存在しない"
    )
    assert "topix_size_multiplier_strong_bear" in sig.parameters, (
        "run_backtest() に topix_size_multiplier_strong_bear パラメータが存在しない"
    )


def test_run_backtest_accepts_factor_filter_params():
    """run_backtest() が factor filter パラメータを受け取れること。"""
    import inspect

    from kabusys.backtest.engine import run_backtest

    sig = inspect.signature(run_backtest)
    assert "use_ma200_filter" in sig.parameters, (
        "run_backtest() に use_ma200_filter パラメータが存在しない"
    )
    assert "volume_breakout_threshold" in sig.parameters, (
        "run_backtest() に volume_breakout_threshold パラメータが存在しない"
    )
    assert "sector_rel_min" in sig.parameters, (
        "run_backtest() に sector_rel_min パラメータが存在しない"
    )


def test_run_py_cli_has_threshold_arg():
    """kabusys.backtest.run の argparse に --threshold が定義されていること。"""
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
    assert "threshold" in actions, f"--threshold が argparse に定義されていない: {actions}"


def test_run_py_cli_has_topix_args():
    """kabusys.backtest.run の argparse に --topix-size-multiplier-weak-bear / --topix-size-multiplier-strong-bear が定義されていること。"""
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

    assert captured
    actions = {a.dest for a in captured[0]._actions}
    assert "topix_size_multiplier_weak_bear" in actions, (
        f"--topix-size-multiplier-weak-bear が argparse に定義されていない: {actions}"
    )
    assert "topix_size_multiplier_strong_bear" in actions, (
        f"--topix-size-multiplier-strong-bear が argparse に定義されていない: {actions}"
    )


def test_run_py_cli_has_factor_filter_args():
    """kabusys.backtest.run の argparse に --ma200-filter / --volume-breakout-threshold が定義されていること。"""
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

    assert captured
    actions = {a.dest for a in captured[0]._actions}
    assert "ma200_filter" in actions, f"--ma200-filter が argparse に定義されていない: {actions}"
    assert "volume_breakout_threshold" in actions, (
        f"--volume-breakout-threshold が argparse に定義されていない: {actions}"
    )


# ── _is_entry_blocked ────────────────────────────────────────────────────────


def test_is_entry_blocked_returns_false_when_disabled():
    from kabusys.backtest.engine import _is_entry_blocked

    assert _is_entry_blocked(900_000.0, 1_000_000.0, None) is False


def test_is_entry_blocked_returns_false_when_within_threshold():
    from kabusys.backtest.engine import _is_entry_blocked

    # drawdown = -10%、threshold = 15% → ブロックしない
    assert _is_entry_blocked(900_000.0, 1_000_000.0, 0.15) is False


def test_is_entry_blocked_returns_true_when_exceeded():
    from kabusys.backtest.engine import _is_entry_blocked

    # drawdown = -20%、threshold = 15% → ブロック
    assert _is_entry_blocked(800_000.0, 1_000_000.0, 0.15) is True


def test_is_entry_blocked_at_exact_threshold_is_not_blocked():
    from kabusys.backtest.engine import _is_entry_blocked

    # drawdown = -15%（= threshold）→ 厳密に「未満」でないためブロックしない
    assert _is_entry_blocked(850_000.0, 1_000_000.0, 0.15) is False


def test_run_backtest_accepts_portfolio_drawdown_stop_pct():
    import inspect

    from kabusys.backtest.engine import run_backtest

    assert "portfolio_drawdown_stop_pct" in inspect.signature(run_backtest).parameters


def test_run_backtest_portfolio_drawdown_stop_pct_default_is_none():
    import inspect

    from kabusys.backtest.engine import run_backtest

    param = inspect.signature(run_backtest).parameters["portfolio_drawdown_stop_pct"]
    assert param.default is None


def test_strong_bear_greater_than_weak_bear_raises():
    """topix_size_multiplier_strong_bear > weak_bear のとき ValueError が上がること。"""
    from kabusys.backtest.engine import run_backtest

    with pytest.raises(ValueError, match="topix_size_multiplier_strong_bear"):
        run_backtest(
            conn=None,  # type: ignore[arg-type]
            start_date=date(2025, 1, 6),
            end_date=date(2025, 1, 10),
            initial_cash=1_000_000,
            topix_size_multiplier_weak_bear=0.5,
            topix_size_multiplier_strong_bear=0.8,
        )


def test_run_py_cli_has_portfolio_drawdown_stop_arg():
    import os
    import pathlib
    import subprocess
    import sys

    src_dir = str(pathlib.Path(__file__).parent.parent / "src")
    env = {**os.environ, "PYTHONPATH": src_dir, "PYTHONUTF8": "1"}
    result = subprocess.run(
        [sys.executable, "-m", "kabusys.backtest.run", "--help"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
    )
    assert "--portfolio-drawdown-stop" in result.stdout
