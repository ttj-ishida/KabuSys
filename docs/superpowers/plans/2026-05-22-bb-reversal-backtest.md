# BB逆張り戦略バックテスト 実装プラン

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ボリンジャーバンド逆張り戦略の有効性を検証するスタンドアロンバックテストスクリプトを実装する

**Architecture:** DuckDB の prices_daily を SQL ウィンドウ関数で直接参照して BB バンドを計算し、PortfolioSimulator でシミュレーションを実行する。generate_signals() には一切手を加えず、universe フィルタのみ features テーブルを参照する。ポジション保有日数は trading day カウンタ（held_trading_days dict）でメモリ管理する。

**Tech Stack:** Python 3.10+, DuckDB (read_only=True), kabusys.backtest.simulator.PortfolioSimulator, kabusys.backtest.metrics.calc_metrics, kabusys.portfolio (calc_equal_weights / calc_position_sizes / select_candidates), kabusys.data.calendar_management.get_trading_days

---

## ファイル構成

| 操作 | パス | 役割 |
|------|------|------|
| 新規作成 | `backtest/backtest_improvement_plan/run_bb_reversal.py` | 全ヘルパー関数・シミュレーション・CLI |
| 新規作成 | `tests/test_bb_reversal.py` | 純粋ロジック単体テスト |

既存コードへの変更: **なし**

---

### Task 1: BBバンド計算関数テストと実装

**Files:**
- Create: `tests/test_bb_reversal.py`
- Create: `backtest/backtest_improvement_plan/run_bb_reversal.py`（冒頭部 + `_compute_bb_rows`）

- [ ] **Step 1: 失敗テストを書く**

`tests/test_bb_reversal.py` を新規作成する:

```python
"""tests/test_bb_reversal.py - BB逆張り戦略ヘルパー単体テスト"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backtest" / "backtest_improvement_plan"))
from run_bb_reversal import (
    _compute_bb_rows,
    _generate_buy_signals,
    _generate_sell_signals,
    _is_buy_blocked_by_regime,
)


def _price_db(prices: list[tuple]) -> duckdb.DuckDBPyConnection:
    """(date, code, close) のリストから prices_daily を持つ in-memory DB を返す。"""
    conn = duckdb.connect(":memory:")
    conn.execute(
        "CREATE TABLE prices_daily "
        "(date DATE, code VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)"
    )
    for d, code, close in prices:
        conn.execute(
            "INSERT INTO prices_daily VALUES (?, ?, ?, ?, ?, ?, 1000000)",
            [d, code, close, close, close, close],
        )
    return conn


def _dates(n: int, start: date = date(2024, 1, 2)) -> list[date]:
    return [start + timedelta(days=i) for i in range(n)]


# ----- _compute_bb_rows -----

def test_bb_rows_basic_structure():
    prices = [(_dates(25)[i], "1001", 1000.0 + i * 2) for i in range(25)]
    conn = _price_db(prices)
    rows = _compute_bb_rows(conn, _dates(25)[-1], period=20, sigma=2.0)
    assert len(rows) == 1
    code, close, lower_band, middle_band = rows[0]
    assert code == "1001"
    assert lower_band < middle_band


def test_bb_rows_insufficient_history_excluded():
    prices = [(_dates(10)[i], "1001", 1000.0 + i) for i in range(10)]
    conn = _price_db(prices)
    rows = _compute_bb_rows(conn, _dates(10)[-1], period=20, sigma=2.0)
    assert rows == []


def test_bb_rows_zero_std_excluded():
    # 全期間同一価格 → std=0 → 除外
    prices = [(_dates(25)[i], "1001", 1000.0) for i in range(25)]
    conn = _price_db(prices)
    rows = _compute_bb_rows(conn, _dates(25)[-1], period=20, sigma=2.0)
    assert rows == []
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
python -m pytest tests/test_bb_reversal.py -v
```

Expected: `ModuleNotFoundError: No module named 'run_bb_reversal'`

- [ ] **Step 3: run_bb_reversal.py のスケルトンと _compute_bb_rows を実装**

`backtest/backtest_improvement_plan/run_bb_reversal.py` を新規作成する:

```python
"""BB逆張り戦略バックテスト調査スクリプト

Close < Lower Band でエントリー、Close >= Middle Band で利確。
generate_signals() / 既存戦略コードへの変更なし。

Usage:
    python backtest/backtest_improvement_plan/run_bb_reversal.py \
        --db data/kabusys.duckdb \
        --start 2017-01-01 --end 2025-12-31
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

import duckdb

_REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_REPO_ROOT / "src"))

from kabusys.backtest.metrics import BacktestMetrics, calc_metrics
from kabusys.backtest.simulator import PortfolioSimulator
from kabusys.data.calendar_management import get_trading_days
from kabusys.portfolio import calc_equal_weights, calc_position_sizes, select_candidates

logger = logging.getLogger(__name__)

SCENARIOS: list[dict] = [
    {"id": "BB1_base",          "period": 20, "sigma": 2.0, "regime_filter": False},
    {"id": "BB2_tight",         "period": 20, "sigma": 1.5, "regime_filter": False},
    {"id": "BB3_wide",          "period": 20, "sigma": 2.5, "regime_filter": False},
    {"id": "BB4_base_regime",   "period": 20, "sigma": 2.0, "regime_filter": True},
    {"id": "BB5_tight_regime",  "period": 20, "sigma": 1.5, "regime_filter": True},
]


def _compute_bb_rows(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
    period: int,
    sigma: float,
) -> list[tuple[str, float, float, float]]:
    """指定日の全銘柄について BB バンド値を計算して返す。

    Returns: [(code, close, lower_band, middle_band), ...]
    period 日分の履歴が不足する銘柄、std=0 の銘柄は除外する。
    """
    lookback_start = trading_day - timedelta(days=period * 5)
    rows = conn.execute(
        f"""
        WITH filtered AS (
            SELECT code, date, CAST(close AS DOUBLE) AS close
            FROM prices_daily
            WHERE date >= ? AND date <= ?
        ),
        bb AS (
            SELECT
                code, date, close,
                AVG(close) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {period - 1} PRECEDING AND CURRENT ROW
                ) AS middle_band,
                STDDEV_POP(close) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {period - 1} PRECEDING AND CURRENT ROW
                ) AS std_close,
                COUNT(*) OVER (
                    PARTITION BY code ORDER BY date
                    ROWS BETWEEN {period - 1} PRECEDING AND CURRENT ROW
                ) AS row_cnt
            FROM filtered
        )
        SELECT code, close,
               middle_band - ? * std_close AS lower_band,
               middle_band
        FROM bb
        WHERE date = ?
          AND row_cnt >= ?
          AND std_close > 0
        """,
        [lookback_start, trading_day, sigma, trading_day, period],
    ).fetchall()
    return [(r[0], float(r[1]), float(r[2]), float(r[3])) for r in rows]
```

- [ ] **Step 4: テストを実行して PASS を確認**

```
python -m pytest tests/test_bb_reversal.py -v
```

Expected: 3 passed

- [ ] **Step 5: コミット**

```bash
git add backtest/backtest_improvement_plan/run_bb_reversal.py tests/test_bb_reversal.py
git commit -m "feat: BB逆張り - _compute_bb_rows 実装とテスト"
```

---

### Task 2: BUYシグナル生成テストと実装

**Files:**
- Modify: `tests/test_bb_reversal.py`
- Modify: `backtest/backtest_improvement_plan/run_bb_reversal.py`

- [ ] **Step 1: 失敗テストを追加**

`tests/test_bb_reversal.py` に追加する:

```python
# ----- _generate_buy_signals -----

def test_buy_signal_when_close_below_lower_band():
    bb_rows = [("1001", 800.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001"}, set())
    assert len(signals) == 1
    assert signals[0]["code"] == "1001"
    assert signals[0]["size_multiplier"] == 1.0


def test_buy_signal_not_generated_when_above_lower_band():
    bb_rows = [("1001", 1050.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001"}, set())
    assert signals == []


def test_buy_signal_not_generated_when_already_held():
    bb_rows = [("1001", 800.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001"}, {"1001"})
    assert signals == []


def test_buy_signal_not_generated_outside_universe():
    bb_rows = [("9999", 800.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001"}, set())
    assert signals == []


def test_buy_signals_have_sequential_rank():
    bb_rows = [("1001", 800.0, 900.0, 1000.0), ("1002", 750.0, 900.0, 1000.0)]
    signals = _generate_buy_signals(bb_rows, {"1001", "1002"}, set())
    assert len(signals) == 2
    assert {s["signal_rank"] for s in signals} == {1, 2}
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
python -m pytest tests/test_bb_reversal.py -k "buy_signal" -v
```

Expected: `AttributeError` (関数未定義)

- [ ] **Step 3: _generate_buy_signals を実装**

`run_bb_reversal.py` の `_compute_bb_rows` の直後に追加する:

```python
def _generate_buy_signals(
    bb_rows: list[tuple[str, float, float, float]],
    universe_codes: set[str],
    held_codes: set[str],
) -> list[dict]:
    """BB 下バンド下抜けで BUY シグナルを生成する。

    Args:
        bb_rows:       [(code, close, lower_band, middle_band), ...]
        universe_codes: features テーブルに存在する銘柄コードセット。
        held_codes:    現在保有中（SELL 対象除外後）の銘柄コードセット。

    Returns:
        [{"code", "score": 1.0, "signal_rank": int, "size_multiplier": 1.0}, ...]
    """
    candidates = [
        code
        for code, close, lower_band, _ in bb_rows
        if close < lower_band and code in universe_codes and code not in held_codes
    ]
    return [
        {"code": code, "score": 1.0, "signal_rank": rank, "size_multiplier": 1.0}
        for rank, code in enumerate(candidates, 1)
    ]
```

- [ ] **Step 4: テストを実行して PASS を確認**

```
python -m pytest tests/test_bb_reversal.py -k "buy_signal" -v
```

Expected: 5 passed

- [ ] **Step 5: コミット**

```bash
git add tests/test_bb_reversal.py backtest/backtest_improvement_plan/run_bb_reversal.py
git commit -m "feat: BB逆張り - _generate_buy_signals 実装とテスト"
```

---

### Task 3: SELLシグナル生成テストと実装

**Files:**
- Modify: `tests/test_bb_reversal.py`
- Modify: `backtest/backtest_improvement_plan/run_bb_reversal.py`

- [ ] **Step 1: 失敗テストを追加**

```python
# ----- _generate_sell_signals -----
# held_trading_days: 保有営業日数カウンタ（BUY 約定日を1日目として毎営業日インクリメント）

def test_sell_on_middle_band_return():
    signals = _generate_sell_signals(
        close_prices={"1001": 1010.0},
        positions={"1001": 100},
        cost_basis={"1001": 950.0},
        held_trading_days={"1001": 5},
        middle_bands={"1001": 1000.0},
        stop_loss_rate=0.08,
        max_holding_days=20,
    )
    assert any(s["code"] == "1001" for s in signals)


def test_sell_on_stop_loss():
    # pnl = (850 - 1000) / 1000 = -15% → -8% 超過
    signals = _generate_sell_signals(
        close_prices={"1001": 850.0},
        positions={"1001": 100},
        cost_basis={"1001": 1000.0},
        held_trading_days={"1001": 3},
        middle_bands={"1001": 1000.0},
        stop_loss_rate=0.08,
        max_holding_days=20,
    )
    assert any(s["code"] == "1001" for s in signals)


def test_no_sell_when_below_middle_and_above_stop():
    # close=950, middle=1000, cost=1000 → pnl=-5% (>-8%), close<middle → no SELL
    signals = _generate_sell_signals(
        close_prices={"1001": 950.0},
        positions={"1001": 100},
        cost_basis={"1001": 1000.0},
        held_trading_days={"1001": 5},
        middle_bands={"1001": 1000.0},
        stop_loss_rate=0.08,
        max_holding_days=20,
    )
    assert signals == []


def test_sell_on_max_holding_days():
    # 21 営業日 >= 20 → time_exit SELL
    signals = _generate_sell_signals(
        close_prices={"1001": 980.0},
        positions={"1001": 100},
        cost_basis={"1001": 1000.0},
        held_trading_days={"1001": 21},
        middle_bands={"1001": 1000.0},
        stop_loss_rate=0.08,
        max_holding_days=20,
    )
    assert any(s["code"] == "1001" for s in signals)
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
python -m pytest tests/test_bb_reversal.py -k "sell" -v
```

- [ ] **Step 3: _generate_sell_signals を実装**

`_generate_buy_signals` の直後に追加する:

```python
def _generate_sell_signals(
    close_prices: dict[str, float],
    positions: dict[str, int],
    cost_basis: dict[str, float],
    held_trading_days: dict[str, int],
    middle_bands: dict[str, float],
    stop_loss_rate: float,
    max_holding_days: int,
) -> list[dict]:
    """保有ポジションに対してエグジット条件を判定し SELL シグナルを返す。

    優先順位:
      1. ストップロス: pnl_rate <= -stop_loss_rate
      2. 時間決済: held_trading_days >= max_holding_days
      3. 利確（中心線回帰）: close >= middle_band
    """
    sell_signals: list[dict] = []
    for code, shares in positions.items():
        if shares <= 0:
            continue
        close = close_prices.get(code)
        if close is None:
            continue
        avg_price = cost_basis.get(code, 0.0)
        if avg_price <= 0:
            continue

        pnl_rate = (close - avg_price) / avg_price
        if pnl_rate <= -stop_loss_rate:
            sell_signals.append({"code": code})
            continue

        if held_trading_days.get(code, 0) >= max_holding_days:
            sell_signals.append({"code": code})
            continue

        middle = middle_bands.get(code)
        if middle is not None and close >= middle:
            sell_signals.append({"code": code})

    return sell_signals
```

- [ ] **Step 4: テストを実行して PASS を確認**

```
python -m pytest tests/test_bb_reversal.py -k "sell" -v
```

Expected: 4 passed

- [ ] **Step 5: コミット**

```bash
git add tests/test_bb_reversal.py backtest/backtest_improvement_plan/run_bb_reversal.py
git commit -m "feat: BB逆張り - _generate_sell_signals 実装とテスト"
```

---

### Task 4: Regimeフィルターテストと実装

**Files:**
- Modify: `tests/test_bb_reversal.py`
- Modify: `backtest/backtest_improvement_plan/run_bb_reversal.py`

- [ ] **Step 1: 失敗テストを追加**

```python
# ----- _is_buy_blocked_by_regime -----

def _regime_db(breadth_stop: bool, regime_label: str | None = None) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE market_breadth (date DATE, breadth_stop BOOLEAN)")
    conn.execute("CREATE TABLE market_regime (date DATE, label VARCHAR, created_at TIMESTAMP DEFAULT now())")
    conn.execute("INSERT INTO market_breadth VALUES (?, ?)", [date(2024, 1, 10), breadth_stop])
    if regime_label:
        conn.execute("INSERT INTO market_regime (date, label) VALUES (?, ?)", [date(2024, 1, 10), regime_label])
    return conn


def test_regime_blocks_on_breadth_stop():
    conn = _regime_db(breadth_stop=True)
    assert _is_buy_blocked_by_regime(conn, date(2024, 1, 10)) is True


def test_regime_blocks_on_bear():
    conn = _regime_db(breadth_stop=False, regime_label="bear")
    assert _is_buy_blocked_by_regime(conn, date(2024, 1, 10)) is True


def test_regime_allows_on_bull():
    conn = _regime_db(breadth_stop=False, regime_label="bull")
    assert _is_buy_blocked_by_regime(conn, date(2024, 1, 10)) is False


def test_regime_allows_when_no_data():
    conn = duckdb.connect(":memory:")
    conn.execute("CREATE TABLE market_breadth (date DATE, breadth_stop BOOLEAN)")
    conn.execute("CREATE TABLE market_regime (date DATE, label VARCHAR)")
    assert _is_buy_blocked_by_regime(conn, date(2024, 1, 10)) is False
```

- [ ] **Step 2: テストを実行して FAIL を確認**

```
python -m pytest tests/test_bb_reversal.py -k "regime" -v
```

- [ ] **Step 3: _is_buy_blocked_by_regime を実装**

`_generate_sell_signals` の直後に追加する:

```python
def _is_buy_blocked_by_regime(
    conn: duckdb.DuckDBPyConnection,
    trading_day: date,
) -> bool:
    """market_breadth.breadth_stop=True または market_regime='bear' の場合 True を返す。

    データが存在しない場合は False（安全側: BUY 許可）。
    """
    try:
        row = conn.execute(
            "SELECT breadth_stop FROM market_breadth WHERE date = ?", [trading_day]
        ).fetchone()
        if row and bool(row[0]):
            return True
    except Exception:
        pass
    try:
        row = conn.execute(
            "SELECT label FROM market_regime WHERE date = ? ORDER BY created_at DESC LIMIT 1",
            [trading_day],
        ).fetchone()
        if row and row[0] == "bear":
            return True
    except Exception:
        pass
    return False
```

- [ ] **Step 4: テストを実行して PASS を確認**

```
python -m pytest tests/test_bb_reversal.py -k "regime" -v
```

Expected: 4 passed

- [ ] **Step 5: 全テストが通ることを確認**

```
python -m pytest tests/test_bb_reversal.py -v
```

Expected: 16 passed

- [ ] **Step 6: コミット**

```bash
git add tests/test_bb_reversal.py backtest/backtest_improvement_plan/run_bb_reversal.py
git commit -m "feat: BB逆張り - _is_buy_blocked_by_regime 実装とテスト"
```

---

### Task 5: シミュレーションループ run_bb_scenario 実装

**Files:**
- Modify: `backtest/backtest_improvement_plan/run_bb_reversal.py`

- [ ] **Step 1: run_bb_scenario を実装**

`_is_buy_blocked_by_regime` の直後に追加する:

```python
def run_bb_scenario(
    conn: duckdb.DuckDBPyConnection,
    start_date: date,
    end_date: date,
    period: int,
    sigma: float,
    use_regime_filter: bool,
    initial_cash: float = 10_000_000,
    max_positions: int = 5,
    max_position_pct: float = 0.20,
    max_utilization: float = 0.70,
    stop_loss_rate: float = 0.08,
    max_holding_days: int = 20,
    lot_size: int = 100,
    slippage_rate: float = 0.001,
    commission_rate: float = 0.00055,
) -> BacktestMetrics:
    """BB 逆張りバックテストを実行し BacktestMetrics を返す。

    シミュレーションループ（1 日ごと）:
      1. 前日オーダーを当日 open で約定 → held_trading_days を更新
      2. 当日 close を取得 → mark_to_market でスナップショット記録
      3. BB バンド計算・universe 取得
      4. SELL シグナル生成（ストップ / 時間 / 利確）
      5. BUY シグナル生成（BB 下抜け・未保有・regime チェック）
      6. equal 配分でポジションサイズ計算
      7. 翌日発注リスト生成
    """
    sim = PortfolioSimulator(initial_cash=initial_cash)
    held_trading_days: dict[str, int] = {}  # code → 保有営業日数（BUY 約定日を 1 日目）
    next_day_orders: list[dict] = []

    trading_days = get_trading_days(conn, start_date, end_date)
    logger.info(
        "run_bb_scenario: start=%s end=%s period=%d sigma=%.1f regime=%s days=%d",
        start_date, end_date, period, sigma, use_regime_filter, len(trading_days),
    )

    for trading_day in trading_days:
        # Step 1: 前日オーダーを当日 open で約定
        open_rows = conn.execute(
            "SELECT code, CAST(open AS DOUBLE) FROM prices_daily WHERE date = ?",
            [trading_day],
        ).fetchall()
        open_prices = {code: p for code, p in open_rows if p is not None}

        prev_positions = set(sim.positions)
        sim.execute_orders(
            next_day_orders, open_prices, slippage_rate, commission_rate,
            trading_day, lot_size=lot_size,
        )
        # 新規 BUY 約定の held_trading_days を初期化、SELL 約定は削除
        new_holdings = set(sim.positions) - prev_positions
        closed_holdings = prev_positions - set(sim.positions)
        for code in new_holdings:
            held_trading_days[code] = 1
        for code in closed_holdings:
            held_trading_days.pop(code, None)
        # 既存保有の日数をインクリメント（今日新規取得分を除く）
        for code in sim.positions:
            if code not in new_holdings:
                held_trading_days[code] = held_trading_days.get(code, 0) + 1

        # Step 2: 当日終値 → mark_to_market
        close_rows = conn.execute(
            "SELECT code, CAST(close AS DOUBLE) FROM prices_daily WHERE date = ?",
            [trading_day],
        ).fetchall()
        close_prices = {code: p for code, p in close_rows if p is not None}
        sim.mark_to_market(trading_day, close_prices)

        # Step 3: BB バンド計算 + universe 取得
        bb_rows = _compute_bb_rows(conn, trading_day, period, sigma)
        universe_rows = conn.execute(
            "SELECT DISTINCT code FROM features WHERE date = ?", [trading_day]
        ).fetchall()
        universe_codes = {r[0] for r in universe_rows}
        middle_bands = {code: middle for code, close, lower, middle in bb_rows}

        # Step 4: SELL シグナル
        sell_signals = _generate_sell_signals(
            close_prices=close_prices,
            positions=dict(sim.positions),
            cost_basis=dict(sim.cost_basis),
            held_trading_days=held_trading_days,
            middle_bands=middle_bands,
            stop_loss_rate=stop_loss_rate,
            max_holding_days=max_holding_days,
        )
        sell_codes = {s["code"] for s in sell_signals}

        # Step 5: BUY シグナル（regime フィルター適用時はブロック判定）
        buy_blocked = use_regime_filter and _is_buy_blocked_by_regime(conn, trading_day)
        if buy_blocked:
            buy_signals: list[dict] = []
        else:
            held_codes = set(sim.positions) - sell_codes
            buy_signals = _generate_buy_signals(bb_rows, universe_codes, held_codes)

        # Step 6: equal 配分でポジションサイズ計算
        current_pv = sim.history[-1].portfolio_value
        candidates = select_candidates(buy_signals, max_positions=max_positions)
        weights = calc_equal_weights(candidates)
        available_cash = min(sim.cash, current_pv * max_utilization)
        sized = calc_position_sizes(
            weights=weights,
            candidates=candidates,
            portfolio_value=current_pv,
            available_cash=available_cash,
            current_positions=sim.positions,
            open_prices=close_prices,
            allocation_method="equal",
            risk_pct=0.005,
            stop_loss_pct=stop_loss_rate,
            max_position_pct=max_position_pct,
            max_utilization=max_utilization,
            cost_buffer=slippage_rate + commission_rate,
            lot_size=lot_size,
        )

        # Step 7: 翌日発注リスト
        next_day_orders = [
            {"code": code, "side": "buy", "shares": (int(shares) // lot_size) * lot_size}
            for code, shares in sized.items()
            if shares > 0 and code not in sell_codes
        ]
        next_day_orders = [o for o in next_day_orders if o["shares"] > 0]
        next_day_orders += [{"code": s["code"], "side": "sell"} for s in sell_signals]

    return calc_metrics(sim.history, sim.trades)
```

- [ ] **Step 2: インポートチェック**

```
python -c "import sys; sys.path.insert(0,'src'); sys.path.insert(0,'backtest/backtest_improvement_plan'); from run_bb_reversal import run_bb_scenario; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add backtest/backtest_improvement_plan/run_bb_reversal.py
git commit -m "feat: BB逆張り - run_bb_scenario シミュレーションループ実装"
```

---

### Task 6: 出力・CLI実装

**Files:**
- Modify: `backtest/backtest_improvement_plan/run_bb_reversal.py`

- [ ] **Step 1: _print_results_table / _save_csv / main を実装**

`run_bb_scenario` の直後（ファイル末尾）に追加する:

```python
# ---------------------------------------------------------------------------
# 出力・CLI
# ---------------------------------------------------------------------------


def _print_results_table(results: list[dict]) -> None:
    header = (
        f"{'scenario':<22} {'CAGR':>7} {'Sharpe':>7} {'MaxDD':>7}"
        f" {'WinRate':>8} {'PF':>6} {'Trades':>7} {'AvgHold':>8}"
    )
    print(header)
    print("-" * len(header))
    for r in results:
        m: BacktestMetrics = r["metrics"]
        print(
            f"{r['id']:<22}"
            f" {m.cagr*100:>+6.1f}%"
            f" {m.sharpe_ratio:>7.3f}"
            f" {m.max_drawdown*100:>6.1f}%"
            f" {m.win_rate*100:>7.1f}%"
            f" {m.profit_factor:>6.2f}"
            f" {m.total_trades:>7d}"
            f" {m.avg_holding_days:>7.1f}d"
        )


def _save_csv(results: list[dict], output_dir: Path) -> Path:
    from datetime import datetime

    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = output_dir / f"bb_reversal_{ts}.csv"
    fieldnames = [
        "scenario", "period", "sigma", "regime_filter",
        "cagr", "sharpe_ratio", "max_drawdown", "win_rate",
        "payoff_ratio", "profit_factor", "total_trades",
        "annual_volatility", "calmar_ratio", "avg_holding_days",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            m: BacktestMetrics = r["metrics"]
            writer.writerow({
                "scenario": r["id"],
                "period": r["period"],
                "sigma": r["sigma"],
                "regime_filter": r["regime_filter"],
                "cagr": round(m.cagr, 6),
                "sharpe_ratio": round(m.sharpe_ratio, 6),
                "max_drawdown": round(m.max_drawdown, 6),
                "win_rate": round(m.win_rate, 6),
                "payoff_ratio": round(m.payoff_ratio, 6),
                "profit_factor": round(m.profit_factor, 6),
                "total_trades": m.total_trades,
                "annual_volatility": round(m.annual_volatility, 6),
                "calmar_ratio": round(m.calmar_ratio, 6),
                "avg_holding_days": round(m.avg_holding_days, 2),
            })
    return path


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="BB逆張り戦略バックテスト調査")
    parser.add_argument("--db", required=True, help="DuckDB ファイルパス")
    parser.add_argument("--start", required=True, help="開始日 YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="終了日 YYYY-MM-DD")
    parser.add_argument("--cash", type=float, default=10_000_000)
    parser.add_argument("--max-positions", type=int, default=5)
    parser.add_argument("--output-dir", default="artifacts")
    args = parser.parse_args()

    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    conn = duckdb.connect(args.db, read_only=True)
    try:
        results = []
        for scenario in SCENARIOS:
            print(f"\n▶ Running {scenario['id']} ...")
            metrics = run_bb_scenario(
                conn=conn,
                start_date=start_date,
                end_date=end_date,
                period=scenario["period"],
                sigma=scenario["sigma"],
                use_regime_filter=scenario["regime_filter"],
                initial_cash=args.cash,
                max_positions=args.max_positions,
            )
            results.append({**scenario, "metrics": metrics})
        print("\n" + "=" * 70)
        _print_results_table(results)
        csv_path = _save_csv(results, Path(args.output_dir))
        print(f"\nCSV 保存: {csv_path}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 構文チェック**

```
python -m py_compile backtest/backtest_improvement_plan/run_bb_reversal.py && echo OK
```

Expected: `OK`

- [ ] **Step 3: コミット**

```bash
git add backtest/backtest_improvement_plan/run_bb_reversal.py
git commit -m "feat: BB逆張り - 出力・CLIエントリポイント実装"
```

---

### Task 7: 全テスト実行・スモークテスト

**Files:** 変更なし

- [ ] **Step 1: ユニットテスト全件実行**

```
python -m pytest tests/test_bb_reversal.py -v
```

Expected: 16 passed

- [ ] **Step 2: 既存テストへの影響確認**

```
python -m pytest tests/ -x --ignore=tests/test_bb_reversal.py -q
```

Expected: all passed（既存コード無変更のため）

- [ ] **Step 3: ヘルプ表示確認**

```
python backtest/backtest_improvement_plan/run_bb_reversal.py --help
```

Expected: usage メッセージ表示

- [ ] **Step 4: DB が存在する場合のスモークテスト（短期間）**

```
python backtest/backtest_improvement_plan/run_bb_reversal.py \
    --db data/kabusys.duckdb \
    --start 2024-01-01 --end 2024-06-30 \
    --output-dir artifacts
```

Expected: 5 シナリオが順番に実行され、コンソールにテーブルが表示され `artifacts/bb_reversal_*.csv` が保存される

- [ ] **Step 5: 最終コミット**

```bash
git add .
git commit -m "feat: BB逆張り戦略バックテストスクリプト完成"
```
