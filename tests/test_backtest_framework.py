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


# ---------------------------------------------------------------------------
# Task 3: simulator.py
# ---------------------------------------------------------------------------

def _make_simulator(initial_cash: float = 1_000_000):
    from kabusys.backtest.simulator import PortfolioSimulator
    return PortfolioSimulator(initial_cash=initial_cash)


def test_simulator_buy_reduces_cash():
    """BUY 約定 → 現金が (株数 × 約定価格 + 手数料) 分減る。"""
    sim = _make_simulator(1_000_000)
    signals = [{"code": "1234", "side": "buy", "alloc": 200_000}]
    open_prices = {"1234": 1000.0}
    slippage = 0.001
    commission = 0.00055

    sim.execute_orders(signals, open_prices, slippage, commission)

    entry_price = 1000.0 * (1 + slippage)  # 1001.0
    shares = int(200_000 // entry_price)     # 199
    cost = shares * entry_price
    comm = cost * commission
    expected_cash = 1_000_000 - cost - comm
    assert abs(sim.cash - expected_cash) < 0.01


def test_simulator_buy_slippage():
    """BUY 約定価格 = open * (1 + slippage_rate)。"""
    sim = _make_simulator()
    signals = [{"code": "1234", "side": "buy", "alloc": 500_000}]
    open_prices = {"1234": 2000.0}
    sim.execute_orders(signals, open_prices, slippage_rate=0.001, commission_rate=0.00055)

    assert len(sim.trades) == 1
    trade = sim.trades[0]
    assert abs(trade.price - 2000.0 * 1.001) < 1e-6


def test_simulator_sell_realized_pnl():
    """SELL → realized_pnl = shares * (exit_price - cost_basis) - commission。"""
    sim = _make_simulator()
    # まず BUY して cost_basis を確立
    sim.execute_orders(
        [{"code": "1234", "side": "buy", "alloc": 300_000}],
        {"1234": 1000.0},
        slippage_rate=0.0,   # スリッページなしで計算を単純化
        commission_rate=0.0,
    )
    buy_trade = sim.trades[0]
    shares = buy_trade.shares

    # SELL
    sim.execute_orders(
        [{"code": "1234", "side": "sell"}],
        {"1234": 1200.0},
        slippage_rate=0.0,
        commission_rate=0.0,
    )
    sell_trade = sim.trades[1]
    expected_pnl = shares * (1200.0 - 1000.0)
    assert abs(sell_trade.realized_pnl - expected_pnl) < 0.01


def test_simulator_sell_slippage():
    """SELL 約定価格 = open * (1 - slippage_rate)。"""
    sim = _make_simulator()
    # 強制的に保有状態を作る
    sim.positions["1234"] = 100
    sim.cost_basis["1234"] = 900.0
    sim.cash -= 90_000

    sim.execute_orders(
        [{"code": "1234", "side": "sell"}],
        {"1234": 1000.0},
        slippage_rate=0.001,
        commission_rate=0.0,
    )
    assert abs(sim.trades[0].price - 999.0) < 1e-6


def test_simulator_mark_to_market():
    """mark_to_market → portfolio_value = cash + sum(shares * close)。"""
    from kabusys.backtest.simulator import PortfolioSimulator
    sim = PortfolioSimulator(initial_cash=500_000)
    sim.positions = {"1234": 100, "5678": 200}
    sim.cost_basis = {"1234": 900.0, "5678": 500.0}
    sim.cash = 200_000

    close_prices = {"1234": 1000.0, "5678": 600.0}
    sim.mark_to_market(date(2024, 1, 5), close_prices)

    expected_pv = 200_000 + 100 * 1000.0 + 200 * 600.0
    assert len(sim.history) == 1
    assert abs(sim.history[0].portfolio_value - expected_pv) < 0.01


def test_simulator_no_price_skips_buy():
    """open_prices に code が存在しない BUY シグナルはスキップ（ログのみ）。"""
    sim = _make_simulator()
    sim.execute_orders(
        [{"code": "9999", "side": "buy", "alloc": 100_000}],
        {},  # 価格なし
        slippage_rate=0.001,
        commission_rate=0.00055,
    )
    assert sim.cash == 1_000_000  # 変化なし
    assert len(sim.trades) == 0


def test_simulator_insufficient_cash_skips_buy():
    """alloc > cash の場合、shares=0 になりスキップ。"""
    sim = _make_simulator(initial_cash=100)  # 現金が極端に少ない
    sim.execute_orders(
        [{"code": "1234", "side": "buy", "alloc": 100_000}],
        {"1234": 10_000.0},
        slippage_rate=0.0,
        commission_rate=0.0,
    )
    assert len(sim.trades) == 0
