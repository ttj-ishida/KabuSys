"""バックテストフレームワーク テスト"""
from __future__ import annotations

import math
from datetime import date, timedelta

import pytest

from kabusys.data.schema import init_schema


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    """インメモリ DuckDB 接続（テスト毎に新規作成）。"""
    c = init_schema(":memory:")
    yield c
    c.close()


def _make_history(values: list[float]) -> list:
    """portfolio_value のリストから DailySnapshot のリストを生成する。"""
    from kabusys.backtest.simulator import DailySnapshot
    base = date(2024, 1, 1)
    return [
        DailySnapshot(
            date=base + timedelta(days=i),
            cash=0.0,
            positions={},
            portfolio_value=v,
        )
        for i, v in enumerate(values)
    ]


def _make_trades(pnl_list: list[float]) -> list:
    """realized_pnl のリストから TradeRecord のリストを生成する（SELL のみ）。"""
    from kabusys.backtest.simulator import TradeRecord
    base = date(2024, 1, 2)
    return [
        TradeRecord(
            date=base + timedelta(days=i),
            code="1234",
            side="sell",
            shares=100,
            price=1000.0,
            commission=55.0,
            realized_pnl=pnl,
        )
        for i, pnl in enumerate(pnl_list)
    ]


# ---------------------------------------------------------------------------
# Task 2: metrics.py
# ---------------------------------------------------------------------------

def test_metrics_cagr_one_year():
    """1年で資産が2倍 → CAGR = 100%。"""
    from kabusys.backtest.metrics import calc_metrics
    # 365 日で 1_000_000 → 2_000_000
    history = _make_history([1_000_000] + [1_000_000] * 364 + [2_000_000])
    result = calc_metrics(history, [])
    assert abs(result.cagr - 1.0) < 0.01  # ≈ 100%


def test_metrics_max_drawdown():
    """100 → 80 → 90 の推移 → MDD = 0.20。"""
    from kabusys.backtest.metrics import calc_metrics
    history = _make_history([100.0, 80.0, 90.0])
    result = calc_metrics(history, [])
    assert abs(result.max_drawdown - 0.20) < 1e-9


def test_metrics_sharpe_constant_return():
    """毎日同一リターン → 標準偏差 0 → Sharpe = 0.0（ゼロ除算回避）。"""
    from kabusys.backtest.metrics import calc_metrics
    history = _make_history([1_000_000 + i * 1000 for i in range(252)])
    result = calc_metrics(history, [])
    assert math.isfinite(result.sharpe_ratio)


def test_metrics_win_rate():
    """勝ち2件・負け1件 → win_rate ≈ 0.667。"""
    from kabusys.backtest.metrics import calc_metrics
    trades = _make_trades([10000.0, 5000.0, -3000.0])
    result = calc_metrics(_make_history([1_000_000, 1_000_000]), trades)
    assert abs(result.win_rate - 2 / 3) < 1e-9


def test_metrics_payoff_ratio():
    """平均利益 7500、平均損失 3000 → payoff ≈ 2.5。"""
    from kabusys.backtest.metrics import calc_metrics
    trades = _make_trades([10000.0, 5000.0, -3000.0])
    result = calc_metrics(_make_history([1_000_000, 1_000_000]), trades)
    assert abs(result.payoff_ratio - 2.5) < 1e-9


def test_metrics_no_trades():
    """トレードなし → win_rate=0.0, payoff_ratio=0.0, total_trades=0。"""
    from kabusys.backtest.metrics import calc_metrics
    result = calc_metrics(_make_history([1_000_000, 1_000_000]), [])
    assert result.win_rate == 0.0
    assert result.payoff_ratio == 0.0
    assert result.total_trades == 0
