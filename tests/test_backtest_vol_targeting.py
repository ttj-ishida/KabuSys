"""tests/test_backtest_vol_targeting.py

Unit tests for _calc_realized_vol() volatility helper.
"""
import math

import numpy as np
import pytest


def test_calc_realized_vol_too_short():
    """履歴が 2 未満のとき 0.0 を返す"""
    from kabusys.backtest.engine import _calc_realized_vol

    assert _calc_realized_vol([], 20) == 0.0
    assert _calc_realized_vol([1_000_000.0], 20) == 0.0


def test_calc_realized_vol_constant_equity():
    """全日同額のとき標準偏差 0 → 0.0 を返す"""
    from kabusys.backtest.engine import _calc_realized_vol

    equity = [1_000_000.0] * 25
    assert _calc_realized_vol(equity, 20) == 0.0


def test_calc_realized_vol_known_value():
    """既知の日次リターン列から計算値を検証する"""
    from kabusys.backtest.engine import _calc_realized_vol

    # 日次リターン 1% 固定 × 21 日 → 20 リターン
    base = 1_000_000.0
    equity = [base * (1.01 ** i) for i in range(21)]
    vol = _calc_realized_vol(equity, 20)
    # 全リターンが同値なら std(ddof=1) = 0 → 0.0
    assert vol == 0.0


def test_calc_realized_vol_varying_returns():
    """変動リターンで正のボラティリティが返ること"""
    from kabusys.backtest.engine import _calc_realized_vol

    # 交互に +2% / -2% → 標準偏差は正
    base = 1_000_000.0
    equity = [base]
    for i in range(25):
        factor = 1.02 if i % 2 == 0 else 0.98
        equity.append(equity[-1] * factor)
    vol = _calc_realized_vol(equity, 20)
    assert vol > 0.0
    # 年次換算で現実的な範囲（> 0.1 かつ < 2.0）
    assert 0.1 < vol < 2.0


def test_calc_realized_vol_uses_last_n_plus_1():
    """window=5 のとき末尾 6 要素（5リターン）だけ使う"""
    from kabusys.backtest.engine import _calc_realized_vol

    # 先頭 20 要素は大変動（無視されるべき）
    big = [1_000_000.0 * (1.5 ** i) for i in range(20)]
    # 末尾 6 要素は定常（std=0）
    tail = [big[-1]] * 6
    equity = big + tail
    assert _calc_realized_vol(equity, 5) == 0.0


def test_run_backtest_vol_target_none_is_unchanged():
    """vol_target=None のとき既存動作と同一シグネチャで呼び出せること"""
    import inspect
    from kabusys.backtest.engine import run_backtest

    sig = inspect.signature(run_backtest)
    assert "vol_target" in sig.parameters
    assert "vol_floor" in sig.parameters
    assert sig.parameters["vol_target"].default is None
    assert sig.parameters["vol_floor"].default == 0.10
