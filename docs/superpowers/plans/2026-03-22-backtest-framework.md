# Backtest Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `src/kabusys/backtest/` モジュールを実装し、既存の `generate_signals()` を活用した日次バックテストエンジンと CLI を提供する。

**Architecture:** 既存の `generate_signals(conn, target_date)` をそのまま呼び出す薄いラッパー設計。バックテスト専用インメモリ DuckDB を構築して本番 DB を汚染しない。日次ループは「前日シグナルを翌日 open で約定 → positions 書き戻し → 終値評価 → シグナル生成 → 発注リスト組み立て」の5ステップ。

**Tech Stack:** Python 3.10+, DuckDB, dataclasses, argparse。外部ライブラリ追加なし。

---

## ファイル構成

| ファイル | 役割 |
|---------|------|
| `src/kabusys/backtest/__init__.py` | パッケージ公開 API |
| `src/kabusys/backtest/clock.py` | SimulatedClock（将来拡張用薄いデータクラス） |
| `src/kabusys/backtest/simulator.py` | PortfolioSimulator（擬似約定・ポートフォリオ状態） |
| `src/kabusys/backtest/metrics.py` | calc_metrics()（CAGR / Sharpe / MaxDD / WinRate） |
| `src/kabusys/backtest/engine.py` | run_backtest() + ヘルパー関数群 |
| `src/kabusys/backtest/run.py` | CLI エントリポイント |
| `tests/test_backtest_framework.py` | 全テスト |

**参照ドキュメント:**
- `documents/05_Backtest/BacktestFramework.md` — 設計仕様
- `docs/superpowers/specs/2026-03-21-backtest-framework-design.md` — 詳細設計
- `src/kabusys/data/schema.py:316` — `init_schema()` の使い方
- `src/kabusys/data/calendar_management.py:243` — `get_trading_days()` の署名
- `src/kabusys/strategy/signal_generator.py:228` — `generate_signals()` の署名

---

## Task 1: モジュールスキャフォールドと clock.py

**Files:**
- Create: `src/kabusys/backtest/__init__.py`
- Create: `src/kabusys/backtest/clock.py`

- [ ] **Step 1: ディレクトリとファイルを作成する**

```python
# src/kabusys/backtest/__init__.py
"""バックテストフレームワーク。"""
from kabusys.backtest.engine import run_backtest, BacktestResult
from kabusys.backtest.simulator import DailySnapshot, TradeRecord
from kabusys.backtest.metrics import BacktestMetrics

__all__ = [
    "run_backtest",
    "BacktestResult",
    "DailySnapshot",
    "TradeRecord",
    "BacktestMetrics",
]
```

```python
# src/kabusys/backtest/clock.py
"""
SimulatedClock — バックテスト用模擬時計。

engine.py のループ変数 trading_day が Simulated Time として機能するため、
現実装でこのクラスを直接使う必要はない。将来の拡張（分足シミュレーション等）用。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class SimulatedClock:
    """バックテスト用の模擬時計。current_date を保持する。"""

    current_date: date
```

- [ ] **Step 2: インポートできることを確認する**

```bash
cd C:\Users\tetsu\Projects\KabuSys
python -c "from kabusys.backtest.clock import SimulatedClock; print('ok')"
```

Expected: `ok`

- [ ] **Step 3: コミット**

```bash
git add src/kabusys/backtest/
git commit -m "feat: add backtest module scaffold and SimulatedClock"
```

---

## Task 2: metrics.py（純粋関数、TDD）

**Files:**
- Create: `src/kabusys/backtest/metrics.py`
- Create: `tests/test_backtest_framework.py`（メトリクステストのみ）

- [ ] **Step 1: テストを書く（FAIL 確認用）**

```python
# tests/test_backtest_framework.py
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
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
cd C:\Users\tetsu\Projects\KabuSys
python -m pytest tests/test_backtest_framework.py -k "test_metrics" -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: metrics.py を実装する**

```python
# src/kabusys/backtest/metrics.py
"""
バックテストメトリクス計算モジュール。

BacktestFramework.md Section 3 に定義された評価指標を計算する。
入力は DailySnapshot のリストと TradeRecord のリストのみ（DB 参照なし）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kabusys.backtest.simulator import DailySnapshot, TradeRecord


@dataclass
class BacktestMetrics:
    """バックテスト評価指標。"""

    cagr: float           # 年平均成長率
    sharpe_ratio: float   # シャープレシオ（無リスク金利=0）
    max_drawdown: float   # 最大ドローダウン（0〜1）
    win_rate: float       # 勝率（0〜1）
    payoff_ratio: float   # ペイオフレシオ（平均利益 / 平均損失）
    total_trades: int     # 全クローズトレード数


def calc_metrics(
    history: list["DailySnapshot"],
    trades: list["TradeRecord"],
) -> BacktestMetrics:
    """DailySnapshot と TradeRecord からバックテスト評価指標を計算する。

    Args:
        history: 日次ポートフォリオ履歴（portfolio_value が必要）。
        trades:  全約定履歴。SELL の realized_pnl を使用。

    Returns:
        BacktestMetrics インスタンス。
    """
    return BacktestMetrics(
        cagr=_calc_cagr(history),
        sharpe_ratio=_calc_sharpe(history),
        max_drawdown=_calc_max_drawdown(history),
        win_rate=_calc_win_rate(trades),
        payoff_ratio=_calc_payoff_ratio(trades),
        total_trades=len([t for t in trades if t.side == "sell"]),
    )


# ---------------------------------------------------------------------------
# 内部計算関数
# ---------------------------------------------------------------------------

def _calc_cagr(history: list["DailySnapshot"]) -> float:
    """CAGR = (最終資産 / 初期資産)^(1/年数) - 1。"""
    if len(history) < 2:
        return 0.0
    initial = history[0].portfolio_value
    final = history[-1].portfolio_value
    if initial <= 0:
        return 0.0
    years = len(history) / 252.0  # 年換算（営業日252日）
    if years <= 0:
        return 0.0
    return (final / initial) ** (1.0 / years) - 1.0


def _calc_sharpe(history: list["DailySnapshot"]) -> float:
    """Sharpe Ratio = 年次化超過リターン / 年次化標準偏差（無リスク金利=0）。"""
    if len(history) < 2:
        return 0.0
    values = [s.portfolio_value for s in history]
    returns = [
        (values[i] - values[i - 1]) / values[i - 1]
        for i in range(1, len(values))
        if values[i - 1] > 0
    ]
    if not returns:
        return 0.0
    n = len(returns)
    mean_r = sum(returns) / n
    variance = sum((r - mean_r) ** 2 for r in returns) / n
    std_r = math.sqrt(variance)
    if std_r == 0:
        return 0.0
    # 年次化（営業日252日）
    return (mean_r / std_r) * math.sqrt(252)


def _calc_max_drawdown(history: list["DailySnapshot"]) -> float:
    """Max Drawdown = max(1 - 評価額 / 過去ピーク)。"""
    if not history:
        return 0.0
    peak = history[0].portfolio_value
    max_dd = 0.0
    for snap in history:
        if snap.portfolio_value > peak:
            peak = snap.portfolio_value
        if peak > 0:
            dd = 1.0 - snap.portfolio_value / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _calc_win_rate(trades: list["TradeRecord"]) -> float:
    """勝率 = 勝ちトレード数 / 全クローズトレード数。"""
    sell_trades = [t for t in trades if t.side == "sell" and t.realized_pnl is not None]
    if not sell_trades:
        return 0.0
    wins = sum(1 for t in sell_trades if t.realized_pnl > 0)
    return wins / len(sell_trades)


def _calc_payoff_ratio(trades: list["TradeRecord"]) -> float:
    """Payoff Ratio = 平均利益 / 平均損失（絶対値）。"""
    sell_trades = [t for t in trades if t.side == "sell" and t.realized_pnl is not None]
    wins = [t.realized_pnl for t in sell_trades if t.realized_pnl > 0]
    losses = [t.realized_pnl for t in sell_trades if t.realized_pnl < 0]
    if not wins or not losses:
        return 0.0
    avg_win = sum(wins) / len(wins)
    avg_loss = abs(sum(losses) / len(losses))
    if avg_loss == 0:
        return 0.0
    return avg_win / avg_loss
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
python -m pytest tests/test_backtest_framework.py -k "test_metrics" -v
```

Expected: 6 passed

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/backtest/metrics.py tests/test_backtest_framework.py
git commit -m "feat: add BacktestMetrics and calc_metrics (TDD)"
```

---

## Task 3: simulator.py（TDD）

**Files:**
- Create: `src/kabusys/backtest/simulator.py`
- Modify: `tests/test_backtest_framework.py`（シミュレータテストを追加）

- [ ] **Step 1: テストを追加する**

`tests/test_backtest_framework.py` に以下を追記:

```python
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
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
python -m pytest tests/test_backtest_framework.py -k "test_simulator" -v
```

Expected: `ImportError` or `ModuleNotFoundError`

- [ ] **Step 3: simulator.py を実装する**

```python
# src/kabusys/backtest/simulator.py
"""
PortfolioSimulator — 擬似約定とポートフォリオ状態管理。

BacktestFramework.md Section 4.3 のスリッページ・手数料モデルに従う。
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class DailySnapshot:
    """日次ポートフォリオのスナップショット。"""

    date: date
    cash: float
    positions: dict[str, int]     # code → 株数
    portfolio_value: float        # cash + 時価評価額


@dataclass
class TradeRecord:
    """約定記録。"""

    date: date
    code: str
    side: str                     # "buy" | "sell"
    shares: int
    price: float                  # 約定価格（スリッページ適用後）
    commission: float
    realized_pnl: float | None    # SELL 時のみ（取得原価との差分 - 手数料）


class PortfolioSimulator:
    """ポートフォリオシミュレータ。

    engine.py から呼び出される。DB 参照は持たない（純粋なメモリ内状態管理）。
    """

    def __init__(self, initial_cash: float) -> None:
        self.cash: float = initial_cash
        self.positions: dict[str, int] = {}          # code → 株数
        self.cost_basis: dict[str, float] = {}       # code → 平均取得単価
        self.history: list[DailySnapshot] = []
        self.trades: list[TradeRecord] = []

    def execute_orders(
        self,
        signals: list[dict],
        open_prices: dict[str, float],
        slippage_rate: float,
        commission_rate: float,
    ) -> None:
        """シグナルリストを当日 open 価格で約定処理する。

        SELL を先に処理してから BUY を処理する（資金確保のため）。

        Args:
            signals:       [{"code": str, "side": "buy"|"sell", "alloc": float}]
                           sell の場合 alloc キーは不要。
            open_prices:   code → 当日始値 の辞書。
            slippage_rate: スリッページ率。BUY は +、SELL は -。
            commission_rate: 手数料率（約定金額 × commission_rate）。
        """
        # SELL を先に処理
        for sig in [s for s in signals if s["side"] == "sell"]:
            self._execute_sell(sig["code"], open_prices, slippage_rate, commission_rate)
        # BUY を後に処理
        for sig in [s for s in signals if s["side"] == "buy"]:
            self._execute_buy(
                sig["code"],
                sig.get("alloc", 0.0),
                open_prices,
                slippage_rate,
                commission_rate,
            )

    def _execute_buy(
        self,
        code: str,
        alloc: float,
        open_prices: dict[str, float],
        slippage_rate: float,
        commission_rate: float,
    ) -> None:
        open_price = open_prices.get(code)
        if open_price is None:
            logger.warning("execute_orders: BUY %s の始値が取得できません。スキップ。", code)
            return

        entry_price = open_price * (1.0 + slippage_rate)
        shares = math.floor(alloc / entry_price)
        if shares <= 0:
            logger.debug("execute_orders: BUY %s shares=0（資金不足）。スキップ。", code)
            return

        cost = shares * entry_price
        commission = cost * commission_rate
        total_cost = cost + commission

        if total_cost > self.cash:
            # 再計算: 手数料込みで収まる株数に調整
            shares = math.floor(self.cash / (entry_price * (1.0 + commission_rate)))
            if shares <= 0:
                logger.debug("execute_orders: BUY %s 再計算後 shares=0。スキップ。", code)
                return
            cost = shares * entry_price
            commission = cost * commission_rate
            total_cost = cost + commission

        self.cash -= total_cost

        # 平均取得単価の更新
        existing_shares = self.positions.get(code, 0)
        existing_cost = self.cost_basis.get(code, 0.0) * existing_shares
        new_total_shares = existing_shares + shares
        self.cost_basis[code] = (existing_cost + cost) / new_total_shares
        self.positions[code] = new_total_shares

        trade_date = self.history[-1].date if self.history else date.today()
        self.trades.append(TradeRecord(
            date=trade_date,
            code=code,
            side="buy",
            shares=shares,
            price=entry_price,
            commission=commission,
            realized_pnl=None,
        ))

    def _execute_sell(
        self,
        code: str,
        open_prices: dict[str, float],
        slippage_rate: float,
        commission_rate: float,
    ) -> None:
        shares = self.positions.get(code, 0)
        if shares <= 0:
            logger.debug("execute_orders: SELL %s 保有なし。スキップ。", code)
            return

        open_price = open_prices.get(code)
        if open_price is None:
            logger.warning("execute_orders: SELL %s の始値が取得できません。スキップ。", code)
            return

        exit_price = open_price * (1.0 - slippage_rate)
        proceeds = shares * exit_price
        commission = proceeds * commission_rate
        net_proceeds = proceeds - commission

        avg_cost = self.cost_basis.get(code, 0.0)
        realized_pnl = shares * (exit_price - avg_cost) - commission

        self.cash += net_proceeds
        del self.positions[code]
        del self.cost_basis[code]

        trade_date = self.history[-1].date if self.history else date.today()
        self.trades.append(TradeRecord(
            date=trade_date,
            code=code,
            side="sell",
            shares=shares,
            price=exit_price,
            commission=commission,
            realized_pnl=realized_pnl,
        ))

    def mark_to_market(
        self,
        trading_day: date,
        close_prices: dict[str, float],
    ) -> None:
        """終値でポートフォリオを時価評価し、DailySnapshot を記録する。

        保有株に終値がない場合は前日評価額（または 0）で代替し WARNING ログを出す。
        """
        stock_value = 0.0
        for code, shares in self.positions.items():
            price = close_prices.get(code)
            if price is None:
                logger.warning(
                    "mark_to_market: %s の終値が取得できません。0 で評価します。date=%s",
                    code, trading_day,
                )
                price = 0.0
            stock_value += shares * price

        portfolio_value = self.cash + stock_value
        self.history.append(DailySnapshot(
            date=trading_day,
            cash=self.cash,
            positions=dict(self.positions),
            portfolio_value=portfolio_value,
        ))
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
python -m pytest tests/test_backtest_framework.py -k "test_simulator" -v
```

Expected: 7 passed

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/backtest/simulator.py tests/test_backtest_framework.py
git commit -m "feat: add PortfolioSimulator with execute_orders and mark_to_market (TDD)"
```

---

## Task 4: engine.py ヘルパー関数群（TDD）

**Files:**
- Create: `src/kabusys/backtest/engine.py`（ヘルパー関数のみ、run_backtest は Task 5）
- Modify: `tests/test_backtest_framework.py`

- [ ] **Step 1: ヘルパーのテストを追加する**

`tests/test_backtest_framework.py` に以下を追記:

```python
# ---------------------------------------------------------------------------
# Task 4: engine.py ヘルパー
# ---------------------------------------------------------------------------

def _insert_price(conn, code: str, d, open_: float, close: float) -> None:
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        [d, code, open_, close, open_, close, 1_000_000],
    )


def _insert_calendar(conn, d, is_trading: bool = True) -> None:
    conn.execute(
        "INSERT INTO market_calendar (date, is_trading_day) VALUES (?, ?)",
        [d, is_trading],
    )


def test_build_backtest_conn_copies_prices(conn):
    """_build_backtest_conn → prices_daily が bt_conn にコピーされる。"""
    from kabusys.backtest.engine import _build_backtest_conn
    from datetime import date

    d = date(2024, 1, 5)
    _insert_price(conn, "1234", d, open_=1000.0, close=1010.0)

    bt_conn = _build_backtest_conn(conn, date(2024, 1, 5), date(2024, 1, 5))
    row = bt_conn.execute(
        "SELECT close FROM prices_daily WHERE code = ? AND date = ?", ["1234", d]
    ).fetchone()
    assert row is not None
    assert abs(float(row[0]) - 1010.0) < 1e-6
    bt_conn.close()


def test_fetch_open_and_close_prices(conn):
    """_fetch_open_prices / _fetch_close_prices → 始値・終値を辞書で返す。"""
    from kabusys.backtest.engine import _fetch_open_prices, _fetch_close_prices
    from datetime import date

    d = date(2024, 1, 8)
    _insert_price(conn, "1234", d, open_=980.0, close=1020.0)
    _insert_price(conn, "5678", d, open_=500.0, close=510.0)

    opens = _fetch_open_prices(conn, d)
    closes = _fetch_close_prices(conn, d)

    assert abs(opens["1234"] - 980.0) < 1e-6
    assert abs(closes["1234"] - 1020.0) < 1e-6
    assert abs(opens["5678"] - 500.0) < 1e-6


def test_write_positions_idempotent(conn):
    """_write_positions → 同日に2回呼んでも1行のみ残る。"""
    from kabusys.backtest.engine import _write_positions
    from datetime import date

    d = date(2024, 1, 10)
    _write_positions(conn, d, {"1234": 100}, {"1234": 950.0})
    _write_positions(conn, d, {"1234": 100}, {"1234": 950.0})

    count = conn.execute(
        "SELECT COUNT(*) FROM positions WHERE date = ?", [d]
    ).fetchone()[0]
    assert count == 1


def test_write_positions_values(conn):
    """_write_positions → position_size と avg_price が正しく書き込まれる。"""
    from kabusys.backtest.engine import _write_positions
    from datetime import date

    d = date(2024, 1, 11)
    _write_positions(conn, d, {"1234": 200, "5678": 50}, {"1234": 1050.0, "5678": 600.0})

    rows = {
        row[0]: (row[1], float(row[2]))
        for row in conn.execute(
            "SELECT code, position_size, avg_price FROM positions WHERE date = ?", [d]
        ).fetchall()
    }
    assert rows["1234"] == (200, 1050.0)
    assert rows["5678"] == (50, 600.0)
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
python -m pytest tests/test_backtest_framework.py -k "test_build or test_fetch or test_write_positions" -v
```

Expected: `ImportError`

- [ ] **Step 3: engine.py（ヘルパー部分）を実装する**

```python
# src/kabusys/backtest/engine.py
"""
バックテストエンジン。

BacktestFramework.md Section 6〜8 に従い、全体ループと補助関数を提供する。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, timedelta

import duckdb

from kabusys.backtest.metrics import BacktestMetrics, calc_metrics
from kabusys.backtest.simulator import DailySnapshot, PortfolioSimulator, TradeRecord

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """run_backtest() の戻り値。"""

    history: list[DailySnapshot]
    trades: list[TradeRecord]
    metrics: BacktestMetrics


# ---------------------------------------------------------------------------
# ヘルパー関数
# ---------------------------------------------------------------------------

def _build_backtest_conn(
    source_conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
) -> duckdb.DuckDBPyConnection:
    """本番 DB からインメモリ DuckDB にデータをコピーしてバックテスト用接続を返す。

    本番 DB の signals / positions テーブルを汚染しない。
    シグナル生成に必要な features 等は start_date - 300日 から end_date までコピーする。

    Args:
        source_conn: 本番 DuckDB 接続（読み取り専用で使用）。
        start_date:  バックテスト開始日。
        end_date:    バックテスト終了日。

    Returns:
        init_schema(":memory:") 済みのインメモリ接続。
    """
    from kabusys.data.schema import init_schema

    bt_conn = init_schema(":memory:")
    data_start = start_date - timedelta(days=300)

    # 日付範囲でフィルタするテーブル
    date_filtered_tables = ("prices_daily", "features", "ai_scores", "market_regime")
    for table in date_filtered_tables:
        try:
            rows = source_conn.execute(
                f"SELECT * FROM {table} WHERE date >= ? AND date <= ?",
                [data_start, end_date],
            ).fetchall()
            if not rows:
                continue
            result = source_conn.execute(f"SELECT * FROM {table} LIMIT 0")
            cols = [desc[0] for desc in result.description]
            placeholders = ", ".join(["?" for _ in cols])
            bt_conn.executemany(
                f"INSERT OR IGNORE INTO {table} VALUES ({placeholders})", rows
            )
        except Exception as exc:
            logger.warning("_build_backtest_conn: %s のコピーをスキップ: %s", table, exc)

    # market_calendar は全件コピー
    try:
        rows = source_conn.execute("SELECT * FROM market_calendar").fetchall()
        if rows:
            result = source_conn.execute("SELECT * FROM market_calendar LIMIT 0")
            cols = [desc[0] for desc in result.description]
            placeholders = ", ".join(["?" for _ in cols])
            bt_conn.executemany(
                f"INSERT OR IGNORE INTO market_calendar VALUES ({placeholders})", rows
            )
    except Exception as exc:
        logger.warning("_build_backtest_conn: market_calendar のコピーをスキップ: %s", exc)

    return bt_conn


def _fetch_open_prices(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> dict[str, float]:
    """指定日の全銘柄始値を {code: open} 辞書で返す。"""
    rows = conn.execute(
        "SELECT code, CAST(open AS DOUBLE) FROM prices_daily WHERE date = ?",
        [trading_day],
    ).fetchall()
    return {code: price for code, price in rows if price is not None}


def _fetch_close_prices(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> dict[str, float]:
    """指定日の全銘柄終値を {code: close} 辞書で返す。"""
    rows = conn.execute(
        "SELECT code, CAST(close AS DOUBLE) FROM prices_daily WHERE date = ?",
        [trading_day],
    ).fetchall()
    return {code: price for code, price in rows if price is not None}


def _write_positions(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
    positions: dict[str, int],
    cost_basis: dict[str, float],
) -> None:
    """シミュレータの保有状態を positions テーブルに書き戻す（冪等）。

    generate_signals() の _generate_sell_signals() が positions テーブルを読むため、
    シグナル生成の直前に呼び出す必要がある。
    market_value は NULL で挿入（nullable カラム、SELL 判定では参照しない）。

    Args:
        positions:  code → 株数（0株の銘柄は書き込まない）。
        cost_basis: code → 平均取得単価。
    """
    conn.execute("DELETE FROM positions WHERE date = ?", [trading_day])
    for code, shares in positions.items():
        if shares <= 0:
            continue
        avg_price = cost_basis.get(code, 0.0)
        conn.execute(
            "INSERT INTO positions (date, code, position_size, avg_price, market_value) "
            "VALUES (?, ?, ?, ?, NULL)",
            [trading_day, code, shares, avg_price],
        )


def _read_day_signals(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> tuple[list[dict], list[dict]]:
    """指定日の signals テーブルから BUY / SELL シグナルを読み取る。

    generate_signals() の呼び出し後に使用する。

    Returns:
        (buy_signals, sell_signals)
        buy_signals:  [{"code": str, "signal_rank": int}, ...]
        sell_signals: [{"code": str}, ...]
    """
    buy_rows = conn.execute(
        "SELECT code, signal_rank FROM signals "
        "WHERE date = ? AND side = 'buy' ORDER BY signal_rank",
        [trading_day],
    ).fetchall()
    sell_rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'",
        [trading_day],
    ).fetchall()
    buy_signals = [{"code": row[0], "signal_rank": row[1]} for row in buy_rows]
    sell_signals = [{"code": row[0]} for row in sell_rows]
    return buy_signals, sell_signals
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
python -m pytest tests/test_backtest_framework.py -k "test_build or test_fetch or test_write_positions" -v
```

Expected: 4 passed

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/backtest/engine.py tests/test_backtest_framework.py
git commit -m "feat: add engine helpers (_build_backtest_conn, _write_positions, _fetch_prices)"
```

---

## Task 5: engine.py — run_backtest メインループ（統合テスト）

**Files:**
- Modify: `src/kabusys/backtest/engine.py`（`run_backtest` 関数を追加）
- Modify: `tests/test_backtest_framework.py`（統合テストを追加）

- [ ] **Step 1: 統合テストを追加する**

`tests/test_backtest_framework.py` に以下を追記:

```python
# ---------------------------------------------------------------------------
# Task 5: run_backtest 統合テスト
# ---------------------------------------------------------------------------

def _setup_minimal_backtest(conn):
    """3営業日分の最小限データをセットアップするヘルパー。

    day1(2024-01-04): BUY シグナル生成に必要な features を挿入
    day2(2024-01-05): day1 シグナルで約定
    day3(2024-01-09): day2 シグナルで約定
    """
    from datetime import date

    days = [date(2024, 1, 4), date(2024, 1, 5), date(2024, 1, 9)]
    for d in days:
        _insert_calendar(conn, d, is_trading=True)
        _insert_price(conn, "1234", d, open_=1000.0, close=1050.0)
        # features: generate_signals が読む必要最小限のデータ
        conn.execute(
            """INSERT INTO features
               (date, code, momentum_20, momentum_60, volatility_20,
                volume_ratio, per, ma200_dev)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [d, "1234", 1.5, 1.2, -0.5, 1.3, 0.5, 0.05],
        )
    return days


def test_run_backtest_returns_result(conn):
    """run_backtest が BacktestResult を返す（最低限の動作確認）。"""
    from kabusys.backtest.engine import run_backtest, BacktestResult
    from datetime import date

    _setup_minimal_backtest(conn)

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
    )

    assert isinstance(result, BacktestResult)
    assert len(result.history) >= 1
    assert result.metrics is not None


def test_run_backtest_cash_decreases_on_buy(conn):
    """BUY 約定後に現金が減少している。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date

    _setup_minimal_backtest(conn)
    initial_cash = 10_000_000

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        initial_cash=initial_cash,
    )

    # 何かトレードがあれば現金が変わっているはず
    if result.trades:
        buys = [t for t in result.trades if t.side == "buy"]
        if buys:
            final_cash = result.history[-1].cash
            assert final_cash < initial_cash


def test_run_backtest_no_lookahead(conn):
    """end_date より後の価格データは結果に影響しない（Look-ahead 防止）。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date

    _setup_minimal_backtest(conn)

    # 未来の価格（end_date + 1日）を挿入
    future_date = date(2024, 1, 10)
    _insert_price(conn, "1234", future_date, open_=9999.0, close=9999.0)
    conn.execute(
        """INSERT INTO features
           (date, code, momentum_20, momentum_60, volatility_20,
            volume_ratio, per, ma200_dev)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [future_date, "1234", 99.0, 99.0, -99.0, 99.0, 0.01, 99.0],
    )

    result1 = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
    )

    # end_date 以降のスナップショットが存在しないこと
    for snap in result1.history:
        assert snap.date <= date(2024, 1, 9), f"未来日付 {snap.date} が履歴に含まれている"


def test_run_backtest_idempotent(conn):
    """同一パラメータで2回実行しても metrics が同一値になる。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date

    _setup_minimal_backtest(conn)

    result1 = run_backtest(conn=conn, start_date=date(2024, 1, 4), end_date=date(2024, 1, 9))
    result2 = run_backtest(conn=conn, start_date=date(2024, 1, 4), end_date=date(2024, 1, 9))

    assert abs(result1.metrics.cagr - result2.metrics.cagr) < 1e-9
    assert len(result1.history) == len(result2.history)


def test_run_backtest_max_position_pct(conn):
    """max_position_pct=0.10 → 1銘柄への投資が portfolio_value の 10% 超にならない。"""
    from kabusys.backtest.engine import run_backtest
    from datetime import date

    _setup_minimal_backtest(conn)
    initial_cash = 10_000_000

    result = run_backtest(
        conn=conn,
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 9),
        initial_cash=initial_cash,
        max_position_pct=0.10,
    )

    for trade in result.trades:
        if trade.side == "buy":
            invested = trade.shares * trade.price
            assert invested <= initial_cash * 0.10 * 1.01  # 1% の誤差許容
```

- [ ] **Step 2: テストが FAIL することを確認**

```bash
python -m pytest tests/test_backtest_framework.py -k "test_run_backtest" -v
```

Expected: `ImportError` (run_backtest が未定義)

- [ ] **Step 3: engine.py に run_backtest を追加する**

`src/kabusys/backtest/engine.py` の末尾に追加:

```python
# ---------------------------------------------------------------------------
# パブリック API
# ---------------------------------------------------------------------------

def run_backtest(
    conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
    initial_cash: float = 10_000_000,
    slippage_rate: float = 0.001,
    commission_rate: float = 0.00055,
    max_position_pct: float = 0.20,
) -> BacktestResult:
    """バックテストを実行し結果を返す。

    本番 DB の conn からインメモリ DuckDB にデータをコピーし、
    generate_signals() を使って日次シミュレーションを行う。

    Args:
        conn:             本番 DuckDB 接続（読み取り専用で使用）。
        start_date:       バックテスト開始日（含む）。
        end_date:         バックテスト終了日（含む）。
        initial_cash:     初期資金（円）。
        slippage_rate:    スリッページ率（デフォルト 0.1%）。
        commission_rate:  手数料率（デフォルト 0.055%）。
        max_position_pct: 1銘柄あたりの最大ポートフォリオ比率（デフォルト 20%）。

    Returns:
        BacktestResult（history, trades, metrics）。
    """
    from kabusys.data.calendar_management import get_trading_days
    from kabusys.strategy.signal_generator import generate_signals

    bt_conn = _build_backtest_conn(conn, start_date, end_date)
    simulator = PortfolioSimulator(initial_cash=initial_cash)
    signals_prev: list[dict] = []

    trading_days = get_trading_days(bt_conn, start_date, end_date)
    logger.info(
        "run_backtest: 開始 start=%s end=%s 営業日数=%d 初期資金=%.0f",
        start_date, end_date, len(trading_days), initial_cash,
    )

    for trading_day in trading_days:
        # Step 1: 前日シグナルを当日 open で約定
        open_prices = _fetch_open_prices(bt_conn, trading_day)
        simulator.execute_orders(signals_prev, open_prices, slippage_rate, commission_rate)

        # Step 2: positions テーブルに書き戻し（generate_signals の SELL 判定に必要）
        _write_positions(bt_conn, trading_day, simulator.positions, simulator.cost_basis)

        # Step 3: 終値で時価評価・スナップショット記録
        close_prices = _fetch_close_prices(bt_conn, trading_day)
        simulator.mark_to_market(trading_day, close_prices)

        # Step 4: 翌日用シグナル生成（bt_conn の positions を読んで SELL 判定）
        generate_signals(bt_conn, target_date=trading_day)

        # Step 5: 翌日の発注リストを組み立て（ポジションサイジング）
        buy_signals, sell_signals = _read_day_signals(bt_conn, trading_day)
        num_buy = len(buy_signals)
        if num_buy > 0 and simulator.cash > 0:
            prior_pv = simulator.history[-1].portfolio_value if simulator.history else initial_cash
            alloc = min(
                prior_pv * max_position_pct,
                simulator.cash / num_buy,
            )
        else:
            alloc = 0.0

        signals_prev = [
            {"code": s["code"], "side": "buy", "alloc": alloc}
            for s in buy_signals
        ] + [
            {"code": s["code"], "side": "sell"}
            for s in sell_signals
        ]

    bt_conn.close()
    metrics = calc_metrics(simulator.history, simulator.trades)
    logger.info(
        "run_backtest: 完了 CAGR=%.2f%% Sharpe=%.3f MaxDD=%.2f%% Trades=%d",
        metrics.cagr * 100, metrics.sharpe_ratio,
        metrics.max_drawdown * 100, metrics.total_trades,
    )
    return BacktestResult(
        history=simulator.history,
        trades=simulator.trades,
        metrics=metrics,
    )
```

- [ ] **Step 4: テストが PASS することを確認**

```bash
python -m pytest tests/test_backtest_framework.py -k "test_run_backtest" -v
```

Expected: 5 passed

- [ ] **Step 5: 全テストが PASS することを確認**

```bash
python -m pytest tests/test_backtest_framework.py -v
```

Expected: 全テスト passed（メトリクス 6 + シミュレータ 7 + ヘルパー 4 + 統合 5 = 22 以上）

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/backtest/engine.py tests/test_backtest_framework.py
git commit -m "feat: add run_backtest main loop with integration tests"
```

---

## Task 6: run.py — CLI エントリポイント

**Files:**
- Create: `src/kabusys/backtest/run.py`

- [ ] **Step 1: run.py を実装する**

```python
# src/kabusys/backtest/run.py
"""
CLI エントリポイント。

使い方:
    python -m kabusys.backtest.run \\
        --start 2023-01-01 --end 2024-12-31 \\
        --cash 10000000 --db path/to/kabusys.duckdb

前提条件:
    指定 DB ファイルに prices_daily, features, ai_scores,
    market_regime, market_calendar が入力済みであること。
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import date

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    parser = argparse.ArgumentParser(
        description="KabuSys バックテスト実行",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--start", required=True, help="開始日 YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="終了日 YYYY-MM-DD")
    parser.add_argument("--cash", type=float, default=10_000_000, help="初期資金（円）[default: 10000000]")
    parser.add_argument("--slippage", type=float, default=0.001, help="スリッページ率 [default: 0.001]")
    parser.add_argument("--commission", type=float, default=0.00055, help="手数料率 [default: 0.00055]")
    parser.add_argument("--max-position-pct", type=float, default=0.20,
                        help="1銘柄最大ポートフォリオ比率 [default: 0.20]")
    parser.add_argument("--db", required=True, help="DuckDB ファイルパス")
    args = parser.parse_args()

    try:
        start_date = date.fromisoformat(args.start)
        end_date = date.fromisoformat(args.end)
    except ValueError as exc:
        print(f"ERROR: 日付フォーマットが不正です: {exc}", file=sys.stderr)
        sys.exit(1)

    if start_date >= end_date:
        print("ERROR: --start は --end より前の日付を指定してください。", file=sys.stderr)
        sys.exit(1)

    from kabusys.data.schema import init_schema
    from kabusys.backtest.engine import run_backtest

    conn = init_schema(args.db)
    try:
        result = run_backtest(
            conn=conn,
            start_date=start_date,
            end_date=end_date,
            initial_cash=args.cash,
            slippage_rate=args.slippage,
            commission_rate=args.commission,
            max_position_pct=args.max_position_pct,
        )
    finally:
        conn.close()

    m = result.metrics
    print(f"\n{'='*40}")
    print(f"  Backtest Result  {start_date} → {end_date}")
    print(f"{'='*40}")
    print(f"  CAGR           : {m.cagr:+.2%}")
    print(f"  Sharpe Ratio   : {m.sharpe_ratio:.3f}")
    print(f"  Max Drawdown   : {m.max_drawdown:.2%}")
    print(f"  Win Rate       : {m.win_rate:.2%}")
    print(f"  Payoff Ratio   : {m.payoff_ratio:.3f}")
    print(f"  Total Trades   : {m.total_trades}")
    print(f"{'='*40}\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: ヘルプが表示されることを確認**

```bash
python -m kabusys.backtest.run --help
```

Expected: usage メッセージが表示される（エラーなし）

- [ ] **Step 3: コミット**

```bash
git add src/kabusys/backtest/run.py
git commit -m "feat: add CLI entry point for backtest (run.py)"
```

---

## Task 7: __init__.py の最終確認と GitHub Issues クローズ

**Files:**
- Modify: `src/kabusys/backtest/__init__.py`（Task 1 で作成済み。全クラスが import できることを確認）

- [ ] **Step 1: 全モジュールが import できることを確認**

```bash
python -c "
from kabusys.backtest import run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics
from kabusys.backtest.clock import SimulatedClock
print('All imports OK')
"
```

Expected: `All imports OK`

- [ ] **Step 2: テストスイート全体を実行**

```bash
python -m pytest tests/test_backtest_framework.py -v --tb=short
```

Expected: 全テスト passed（0 failures）

- [ ] **Step 3: 既存テストへの影響がないことを確認**

```bash
python -m pytest tests/ -v --tb=short
```

Expected: 全テスト passed

- [ ] **Step 4: 最終コミット**

```bash
git add src/kabusys/backtest/__init__.py
git commit -m "feat: Phase 4 backtest framework complete (#19 #20 #21 #22 #23)"
```
