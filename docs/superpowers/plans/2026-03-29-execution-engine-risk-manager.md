# Execution Engine + Risk Manager Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Issue #30 + #31 — Signal Queue を寄付き前に読み込んで3段階リスクガードを通して発注し、WebSocket push で約定通知を受けてドローダウン監視する Execution Engine と Risk Manager を実装する。

**Architecture:** スレッドモデル — メインスレッドが DuckDB `signals` + `portfolio_targets` から今日の発注計画を読み込み RiskManager (Gate 1/2) を通して OrderManager 経由で発注。WebSocket スレッドが約定 push を受信してメインスレッドに `queue.Queue` で橋渡し。Gate 3 (ドローダウン) はこのキューを drain した後に評価。

**Tech Stack:** Python 3.10+, DuckDB, SQLite (OrderRepository), httpx (REST), websocket-client (WebSocket push), threading, queue

---

## ファイル構成

```
新規作成:
  src/kabusys/execution/risk_manager.py      — RiskConfig, RiskResult, RiskManager (#31)
  src/kabusys/execution/execution_engine.py  — EngineConfig, ExecutionEngine (#30)
  tests/test_risk_manager.py                 — RiskManager 単体テスト
  tests/test_execution_engine.py             — ExecutionEngine 統合テスト (#34 も対応)

変更:
  src/kabusys/execution/broker_api.py        — Position に current_price フィールド追加
  src/kabusys/execution/kabu_client.py       — get_positions() で CurrentPrice をマップ、stream_push() 追加
  src/kabusys/execution/mock_client.py       — Position に current_price を渡すよう更新
  src/kabusys/execution/__init__.py          — RiskManager, RiskConfig, ExecutionEngine, EngineConfig をエクスポート
```

### 依存関係

- `websocket-client>=1.7` は `requirements.txt` に既記載（追加不要）
- `RiskManager` → `BrokerAPIProtocol`, `OrderRepository`（注入）
- `ExecutionEngine` → `BrokerAPIProtocol`, `OrderRepository`, `RiskManager`, DuckDB 接続, `OrderManager`（注入）

---

## Task 1: Position に current_price を追加

**Files:**
- Modify: `src/kabusys/execution/broker_api.py`
- Modify: `src/kabusys/execution/kabu_client.py`
- Modify: `src/kabusys/execution/mock_client.py`

既存の `Position` dataclass は `(code, qty, avg_price)` のみ。ドローダウン計算に現在値が必要なため `current_price` を追加する。

- [ ] **Step 1: `broker_api.py` の `Position` に `current_price` を追加**

`src/kabusys/execution/broker_api.py` の `Position` dataclass を変更:

```python
@dataclass
class Position:
    code: str
    qty: int                         # 保有株数
    avg_price: float                 # 平均取得単価
    current_price: float | None = None  # 現在値（時価評価額計算用）
```

- [ ] **Step 2: `kabu_client.py` の `get_positions()` で `CurrentPrice` をマップ**

`kabu_client.py` の `get_positions()` 内の `positions.append(...)` 部分を変更:

```python
for p in self._json(resp) or []:
    raw_current = p.get("CurrentPrice")
    positions.append(
        Position(
            code=str(p.get("Symbol", "")),
            qty=int(p.get("LeavesQty", 0)),
            avg_price=float(p.get("Price", 0.0)),
            current_price=float(raw_current) if raw_current is not None else None,
        )
    )
```

- [ ] **Step 3: `mock_client.py` の `get_positions()` で `current_price` を返す**

`MockBrokerClient.__init__` の `initial_positions` パラメータはすでに `list[Position]` を受け取る。`_apply_fill` は `avg_price` のみ更新する（`current_price` は変えない設計）。`get_positions()` はそのまま `self._positions.values()` を返すので `current_price` が `None` として返る。

テストで市場価値を注入したい場合は `initial_positions` に `current_price` を設定するか、テスト中に `mock._positions["1234"] = Position(code="1234", qty=100, avg_price=1500.0, current_price=1600.0)` で上書きする。変更は不要。

- [ ] **Step 4: テストで確認**

```bash
# 既存テストが壊れていないことを確認
python -m pytest tests/test_order_state_machine.py -v
```

Expected: 37 passed

- [ ] **Step 5: Commit**

```bash
git add src/kabusys/execution/broker_api.py src/kabusys/execution/kabu_client.py
git commit -m "feat: add current_price field to Position for drawdown monitoring"
```

---

## Task 2: RiskManager — 骨格 + Gate 1 (シグナルレベル検査)

**Files:**
- Create: `src/kabusys/execution/risk_manager.py`
- Create: `tests/test_risk_manager.py`

- [ ] **Step 1: 失敗するテストを書く**

`tests/test_risk_manager.py` を新規作成:

```python
# tests/test_risk_manager.py
"""RiskManager 単体テスト"""
import sqlite3
import pytest
from kabusys.execution.broker_api import Position
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.risk_manager import RiskConfig, RiskManager


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return OrderRepository(conn)


def _make_manager(broker, repo) -> RiskManager:
    config = RiskConfig(initial_portfolio_value=10_000_000.0)
    return RiskManager(broker=broker, repo=repo, config=config)


class TestGate1CheckSignal:

    def test_passes_when_all_checks_ok(self, repo):
        broker = MockBrokerClient(available_cash=5_000_000.0)
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=100_000.0)
        assert result.passed

    def test_fails_when_insufficient_cash(self, repo):
        broker = MockBrokerClient(available_cash=50_000.0)
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=100_000.0)
        assert not result.passed
        assert "余力" in result.reason

    def test_fails_when_duplicate_active_order(self, repo):
        broker = MockBrokerClient(available_cash=5_000_000.0)
        from kabusys.execution.order_record import OrderRecord
        from datetime import datetime, timezone
        active = OrderRecord(
            client_order_id="test-dup",
            signal_id="2026-03-29_1234_buy",
            code="1234", side="buy", qty=100,
            order_type="market", price=0.0,
            state=OrderState.OrderAccepted,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(active)
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=100_000.0)
        assert not result.passed
        assert "重複" in result.reason

    def test_fails_when_position_limit_exceeded(self, repo):
        # 総資産 10,000,000 円、max_position_pct=0.10 → 1銘柄上限 1,000,000 円
        # 既存ポジション: 1234 @ current_price=2000, qty=400 → 800,000 円
        # 追加注文: 300,000 円 → 合計 1,100,000 円 > 1,000,000 円 → NG
        existing_pos = Position(code="1234", qty=400, avg_price=1800.0, current_price=2000.0)
        broker = MockBrokerClient(
            available_cash=5_000_000.0,
            initial_positions=[existing_pos],
        )
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=300_000.0)
        assert not result.passed
        assert "ポジション上限" in result.reason

    def test_fails_when_utilization_limit_exceeded(self, repo):
        # 総資産 10,000,000 円、max_utilization=0.80 → 全ポジション上限 8,000,000 円
        # 既存ポジション評価額: 7,800,000 円 (current_price あり)
        # 追加注文: 300,000 円 → 合計 8,100,000 円 > 8,000,000 円 → NG
        big_pos = Position(code="9999", qty=780, avg_price=9000.0, current_price=10000.0)
        broker = MockBrokerClient(
            available_cash=5_000_000.0,
            initial_positions=[big_pos],
        )
        rm = _make_manager(broker, repo)
        result = rm.check_signal("2026-03-29_1234_buy", "1234", order_value=300_000.0)
        assert not result.passed
        assert "全体上限" in result.reason
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_risk_manager.py -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.execution.risk_manager'`

- [ ] **Step 3: `risk_manager.py` の骨格と Gate 1 を実装**

`src/kabusys/execution/risk_manager.py` を新規作成:

```python
# src/kabusys/execution/risk_manager.py
"""RiskManager — 3段階リスクガード。

Gate 1: check_signal()    — 余力・重複・ポジション上限（発注前）
Gate 2: check_execution() — レート制限・サーキットブレーカー（API 送信前）
Gate 3: check_metrics()   — ドローダウン監視（約定後）
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from kabusys.execution.broker_api import BrokerAPIProtocol
from kabusys.execution.order_repository import OrderRepository

logger = logging.getLogger(__name__)


@dataclass
class RiskConfig:
    max_position_pct: float = 0.10        # 1銘柄最大投資比率
    max_utilization: float = 0.80         # 全ポジション投下上限（キャッシュ最低20%）
    rate_limit_per_sec: int = 5           # API レート制限（毎秒5回）
    circuit_breaker_errors: int = 10      # ウィンドウ内エラー上限
    circuit_breaker_window_sec: int = 60  # エラーカウントウィンドウ（秒）
    max_drawdown: float = 0.15            # キルスイッチ発動ドローダウン閾値
    initial_portfolio_value: float = 0.0  # セッション開始時の資産評価額


@dataclass
class RiskResult:
    passed: bool
    reason: str = ""


class RiskManager:
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
        config: RiskConfig,
    ) -> None:
        self._broker = broker
        self._repo = repo
        self._config = config

        # Gate 2: トークンバケツ
        self._tokens: float = float(config.rate_limit_per_sec)
        self._last_refill: float = time.monotonic()

        # Gate 2: サーキットブレーカー
        self._cb_state: str = "CLOSED"  # "CLOSED" | "OPEN" | "HALF_OPEN"
        self._cb_error_times: list[float] = []
        self._cb_open_at: float = 0.0

    # ------------------------------------------------------------------
    # Gate 1: シグナルレベル（発注前）
    # ------------------------------------------------------------------

    def check_signal(
        self,
        signal_id: str,
        code: str,
        order_value: float,
    ) -> RiskResult:
        """余力・重複・ポジション上限を検査する。"""
        # 1. 余力チェック
        cash = self._broker.get_available_cash()
        if cash < order_value:
            return RiskResult(False, f"余力不足: 余力={cash:.0f}円, 発注額={order_value:.0f}円")

        # 2. 重複チェック（active 注文が存在するか）
        existing = self._repo.get_by_signal(signal_id)
        from kabusys.execution.order_record import OrderState
        _TERMINAL = {OrderState.Closed, OrderState.Cancelled, OrderState.Rejected}
        active = [r for r in existing if r.state not in _TERMINAL]
        if active:
            return RiskResult(False, f"重複注文: signal_id={signal_id} の active 注文が存在します")

        # 3. ポジション上限チェック
        positions = self._broker.get_positions()
        total_market_value = sum(
            p.qty * p.current_price
            for p in positions
            if p.current_price is not None
        )
        # 同銘柄の現在評価額
        same_code_value = sum(
            p.qty * p.current_price
            for p in positions
            if p.code == code and p.current_price is not None
        )
        # 総資産 = キャッシュ + ポジション時価評価額（current_price が None のものは avg_price でフォールバック）
        total_fallback = sum(
            p.qty * (p.current_price if p.current_price is not None else p.avg_price)
            for p in positions
        )
        total_assets = cash + total_fallback

        # 3a. 1銘柄上限
        if total_assets > 0:
            new_position_value = same_code_value + order_value
            if new_position_value / total_assets > self._config.max_position_pct:
                return RiskResult(
                    False,
                    f"ポジション上限超過: 銘柄={code}, "
                    f"新規評価額={new_position_value:.0f}円 / 総資産={total_assets:.0f}円 "
                    f"> {self._config.max_position_pct:.0%}",
                )

        # 3b. 全体上限
        if total_assets > 0:
            new_total_market = total_market_value + order_value
            if new_total_market / total_assets > self._config.max_utilization:
                return RiskResult(
                    False,
                    f"全体上限超過: 全ポジション評価額+発注額={new_total_market:.0f}円 / 総資産={total_assets:.0f}円 "
                    f"> {self._config.max_utilization:.0%}",
                )

        return RiskResult(True)
```

- [ ] **Step 4: Gate 1 テストが通ることを確認**

```bash
python -m pytest tests/test_risk_manager.py::TestGate1CheckSignal -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add src/kabusys/execution/risk_manager.py tests/test_risk_manager.py
git commit -m "feat: RiskManager Gate 1 - signal-level risk check (#31)"
```

---

## Task 3: RiskManager — Gate 2 (レート制限 + サーキットブレーカー)

**Files:**
- Modify: `src/kabusys/execution/risk_manager.py`
- Modify: `tests/test_risk_manager.py`

- [ ] **Step 1: Gate 2 のテストを追加**

`tests/test_risk_manager.py` の末尾に追加:

```python
class TestGate2CheckExecution:

    def test_passes_initially(self, repo):
        broker = MockBrokerClient()
        rm = _make_manager(broker, repo)
        result = rm.check_execution()
        assert result.passed

    def test_rate_limit_rejects_after_burst(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(rate_limit_per_sec=3, initial_portfolio_value=10_000_000.0)
        rm = RiskManager(broker=broker, repo=repo, config=config)
        # 3回は通る
        for _ in range(3):
            r = rm.check_execution()
            assert r.passed
        # 4回目は reject
        r = rm.check_execution()
        assert not r.passed
        assert "レート制限" in r.reason

    def test_circuit_breaker_opens_after_n_errors(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(
            circuit_breaker_errors=3,
            circuit_breaker_window_sec=60,
            initial_portfolio_value=10_000_000.0,
        )
        rm = RiskManager(broker=broker, repo=repo, config=config)
        rm.record_api_error()
        rm.record_api_error()
        assert rm.check_execution().passed  # まだ CLOSED
        rm.record_api_error()
        result = rm.check_execution()
        assert not result.passed
        assert "サーキットブレーカー" in result.reason

    def test_circuit_breaker_half_open_after_window(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(
            circuit_breaker_errors=2,
            circuit_breaker_window_sec=0,  # ウィンドウ = 0秒 → 即 HALF_OPEN
            initial_portfolio_value=10_000_000.0,
        )
        rm = RiskManager(broker=broker, repo=repo, config=config)
        rm.record_api_error()
        rm.record_api_error()
        assert not rm.check_execution().passed  # OPEN
        # window=0 → 即 HALF_OPEN 遷移
        result = rm.check_execution()
        assert result.passed  # HALF_OPEN で1件許可

    def test_circuit_breaker_closes_on_success(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(
            circuit_breaker_errors=2,
            circuit_breaker_window_sec=0,
            initial_portfolio_value=10_000_000.0,
        )
        rm = RiskManager(broker=broker, repo=repo, config=config)
        rm.record_api_error()
        rm.record_api_error()
        rm.check_execution()        # OPEN → HALF_OPEN
        rm.check_execution()        # HALF_OPEN: 1件許可
        rm.record_api_success()     # CLOSED に遷移
        assert rm.check_execution().passed  # CLOSED で通過
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_risk_manager.py::TestGate2CheckExecution -v
```

Expected: `AttributeError: 'RiskManager' object has no attribute 'check_execution'`

- [ ] **Step 3: Gate 2 を `risk_manager.py` に実装**

`RiskManager` クラスに以下のメソッドを追加:

```python
    # ------------------------------------------------------------------
    # Gate 2: エグゼキューションレベル（API 送信前）
    # ------------------------------------------------------------------

    def check_execution(self) -> RiskResult:
        """レート制限・サーキットブレーカーを検査する。"""
        # サーキットブレーカー
        cb = self._check_circuit_breaker()
        if not cb.passed:
            return cb

        # レート制限（トークンバケツ）
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            float(self._config.rate_limit_per_sec),
            self._tokens + elapsed * self._config.rate_limit_per_sec,
        )
        self._last_refill = now

        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return RiskResult(True)

        return RiskResult(False, f"レート制限: {self._config.rate_limit_per_sec}回/秒を超過")

    def record_api_error(self) -> None:
        """API エラーを記録する（send_order 失敗時に呼ぶ）。"""
        now = time.monotonic()
        window = self._config.circuit_breaker_window_sec
        self._cb_error_times = [t for t in self._cb_error_times if now - t < window]
        self._cb_error_times.append(now)

        if (
            self._cb_state == "CLOSED"
            and len(self._cb_error_times) >= self._config.circuit_breaker_errors
        ):
            self._cb_state = "OPEN"
            self._cb_open_at = now
            logger.warning(
                "サーキットブレーカー OPEN: %d秒以内に%dエラー",
                window, len(self._cb_error_times),
            )

    def record_api_success(self) -> None:
        """API 成功を記録する（HALF_OPEN → CLOSED 遷移用）。"""
        self._cb_error_times.clear()
        if self._cb_state in ("HALF_OPEN", "OPEN"):
            self._cb_state = "CLOSED"
            logger.info("サーキットブレーカー CLOSED")

    def _check_circuit_breaker(self) -> RiskResult:
        now = time.monotonic()
        if self._cb_state == "CLOSED":
            return RiskResult(True)

        if self._cb_state == "OPEN":
            if now - self._cb_open_at >= self._config.circuit_breaker_window_sec:
                self._cb_state = "HALF_OPEN"
                logger.info("サーキットブレーカー HALF_OPEN")
                return RiskResult(True)  # 1件試行許可
            return RiskResult(False, "サーキットブレーカー OPEN: 発注停止中")

        # HALF_OPEN: 1件だけ許可して OPEN に戻す（成功なら record_api_success() で CLOSED へ）
        self._cb_state = "OPEN"
        self._cb_open_at = now
        return RiskResult(True)
```

- [ ] **Step 4: Gate 2 テストが通ることを確認**

```bash
python -m pytest tests/test_risk_manager.py::TestGate2CheckExecution -v
```

Expected: 5 passed

- [ ] **Step 5: 全テストが通ることを確認**

```bash
python -m pytest tests/test_risk_manager.py -v
```

Expected: 10 passed

- [ ] **Step 6: Commit**

```bash
git add src/kabusys/execution/risk_manager.py tests/test_risk_manager.py
git commit -m "feat: RiskManager Gate 2 - rate limit and circuit breaker (#31)"
```

---

## Task 4: RiskManager — Gate 3 (ドローダウン監視)

**Files:**
- Modify: `src/kabusys/execution/risk_manager.py`
- Modify: `tests/test_risk_manager.py`

- [ ] **Step 1: Gate 3 のテストを追加**

`tests/test_risk_manager.py` の末尾に追加:

```python
class TestGate3CheckMetrics:

    def test_passes_when_no_drawdown(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(
            initial_portfolio_value=10_000_000.0,
            max_drawdown=0.15,
        )
        rm = RiskManager(broker=broker, repo=repo, config=config)
        result = rm.check_metrics(current_portfolio_value=10_000_000.0)
        assert result.passed

    def test_passes_when_drawdown_below_threshold(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(
            initial_portfolio_value=10_000_000.0,
            max_drawdown=0.15,
        )
        rm = RiskManager(broker=broker, repo=repo, config=config)
        # 10% ドローダウン（< 15%）
        result = rm.check_metrics(current_portfolio_value=9_000_000.0)
        assert result.passed

    def test_fails_when_drawdown_exceeds_threshold(self, repo):
        broker = MockBrokerClient()
        config = RiskConfig(
            initial_portfolio_value=10_000_000.0,
            max_drawdown=0.15,
        )
        rm = RiskManager(broker=broker, repo=repo, config=config)
        # 20% ドローダウン（> 15%）→ NG
        result = rm.check_metrics(current_portfolio_value=8_000_000.0)
        assert not result.passed
        assert "ドローダウン" in result.reason

    def test_no_drawdown_when_initial_value_zero(self, repo):
        """initial_portfolio_value=0 の場合は常に passed（ゼロ除算防止）"""
        broker = MockBrokerClient()
        config = RiskConfig(initial_portfolio_value=0.0, max_drawdown=0.15)
        rm = RiskManager(broker=broker, repo=repo, config=config)
        result = rm.check_metrics(current_portfolio_value=0.0)
        assert result.passed
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_risk_manager.py::TestGate3CheckMetrics -v
```

Expected: `AttributeError: 'RiskManager' object has no attribute 'check_metrics'`

- [ ] **Step 3: Gate 3 を `risk_manager.py` に実装**

`RiskManager` クラスに追加:

```python
    # ------------------------------------------------------------------
    # Gate 3: メトリクスレベル（約定後監視）
    # ------------------------------------------------------------------

    def check_metrics(self, current_portfolio_value: float) -> RiskResult:
        """ドローダウンを検査する。initial_portfolio_value=0 の場合はスキップ。"""
        if self._config.initial_portfolio_value <= 0:
            return RiskResult(True)

        drawdown = (
            self._config.initial_portfolio_value - current_portfolio_value
        ) / self._config.initial_portfolio_value

        if drawdown > self._config.max_drawdown:
            return RiskResult(
                False,
                f"ドローダウン超過: {drawdown:.1%} > {self._config.max_drawdown:.1%} "
                f"(現在={current_portfolio_value:.0f}円, 開始={self._config.initial_portfolio_value:.0f}円)",
            )

        return RiskResult(True)
```

- [ ] **Step 4: 全テストが通ることを確認**

```bash
python -m pytest tests/test_risk_manager.py -v
```

Expected: 14 passed

- [ ] **Step 5: Commit**

```bash
git add src/kabusys/execution/risk_manager.py tests/test_risk_manager.py
git commit -m "feat: RiskManager Gate 3 - drawdown monitoring and kill switch trigger (#31)"
```

---

## Task 5: KabuStationClient に WebSocket push 受信を追加

**Files:**
- Modify: `src/kabusys/execution/kabu_client.py`

- [ ] **Step 1: `kabu_client.py` の先頭 import に追加**

```python
import json
import threading
from typing import Callable

import websocket
```

- [ ] **Step 2: `KabuStationClient` に `stream_push()` メソッドを追加**

```python
def stream_push(
    self,
    on_message: Callable[[dict], None],
    stop_event: threading.Event,
) -> None:
    """WebSocket で kabu station の push 通知を受信するブロッキングメソッド。

    stop_event が set されるまで接続を維持する。接続断時は1秒後に再接続。
    スレッド内で呼び出すことを想定。

    URL は base_url の http:// を ws:// に置換し末尾に /websocket を付加する。
    例: http://localhost:18080/kabusapi → ws://localhost:18080/kabusapi/websocket
    """
    ws_url = self._base_url.rstrip("/").replace("http://", "ws://") + "/websocket"

    def _on_message(_ws: websocket.WebSocketApp, message: str) -> None:
        try:
            payload = json.loads(message)
            on_message(payload)
        except json.JSONDecodeError as exc:
            logger.warning("WebSocket: JSON デコード失敗: %s", exc)
        except Exception as exc:
            logger.error("WebSocket: on_message ハンドラ例外: %s", exc)

    def _on_error(_ws: websocket.WebSocketApp, error: Exception) -> None:
        logger.error("WebSocket エラー: %s", error)

    def _on_close(_ws: websocket.WebSocketApp, code: int | None, msg: str | None) -> None:
        logger.info("WebSocket クローズ: code=%s", code)

    while not stop_event.is_set():
        try:
            token = self._get_token()
            ws = websocket.WebSocketApp(
                ws_url,
                header={"X-API-KEY": token},
                on_message=_on_message,
                on_error=_on_error,
                on_close=_on_close,
            )
            ws.run_forever(ping_interval=30, ping_timeout=10)
        except Exception as exc:
            logger.error("WebSocket 接続失敗: %s", exc)
        if not stop_event.is_set():
            stop_event.wait(timeout=1.0)  # 1秒後に再接続
```

- [ ] **Step 3: 既存テストが壊れていないことを確認**

```bash
python -m pytest tests/test_risk_manager.py tests/test_order_state_machine.py -v
```

Expected: 51 passed

- [ ] **Step 4: Commit**

```bash
git add src/kabusys/execution/kabu_client.py
git commit -m "feat: add WebSocket stream_push() to KabuStationClient (#30)"
```

---

## Task 6: ExecutionEngine — 骨格 + シグナル読み込み

**Files:**
- Create: `src/kabusys/execution/execution_engine.py`
- Create: `tests/test_execution_engine.py`

- [ ] **Step 1: テストの骨格を作成**

`tests/test_execution_engine.py` を新規作成:

```python
# tests/test_execution_engine.py
"""ExecutionEngine 統合テスト（Issue #30 / #34）"""
import queue
import sqlite3
import threading
from datetime import date, time
from unittest.mock import MagicMock

import duckdb
import pytest

from kabusys.execution.broker_api import OrderRequest, Position
from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.risk_manager import RiskConfig, RiskManager


TARGET_DATE = date(2026, 3, 29)


@pytest.fixture
def sqlite_conn():
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture
def duckdb_conn():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE signals (
            date DATE, code VARCHAR, side VARCHAR,
            score FLOAT, signal_rank INTEGER
        )
    """)
    conn.execute("""
        CREATE TABLE portfolio_targets (
            date DATE, code VARCHAR,
            target_size INTEGER, entry_price FLOAT
        )
    """)
    yield conn
    conn.close()


def _make_engine(broker, sqlite_conn, duckdb_conn, *, config=None) -> ExecutionEngine:
    repo = OrderRepository(sqlite_conn)
    risk_config = RiskConfig(initial_portfolio_value=10_000_000.0)
    rm = RiskManager(broker=broker, repo=repo, config=risk_config)
    order_manager = OrderManager(broker=broker, repo=repo)
    cfg = config or EngineConfig(target_date=TARGET_DATE)
    return ExecutionEngine(
        broker=broker,
        repo=repo,
        risk_manager=rm,
        order_manager=order_manager,
        duckdb_conn=duckdb_conn,
        config=cfg,
    )


def _insert_signal(conn, code: str, side: str = "buy", score: float = 0.8):
    conn.execute(
        "INSERT INTO signals VALUES (?, ?, ?, ?, ?)",
        [TARGET_DATE, code, side, score, 1],
    )


def _insert_target(conn, code: str, qty: int = 100, price: float = 1500.0):
    conn.execute(
        "INSERT INTO portfolio_targets VALUES (?, ?, ?, ?)",
        [TARGET_DATE, code, qty, price],
    )


class TestReadSignals:

    def test_reads_signals_joined_with_portfolio_targets(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        signals = engine._read_signals()
        assert len(signals) == 1
        assert signals[0]["code"] == "1234"
        assert signals[0]["qty"] == 100
        assert signals[0]["price"] == 1500.0

    def test_excludes_signals_without_portfolio_targets(self, sqlite_conn, duckdb_conn):
        _insert_signal(duckdb_conn, "1234")
        # portfolio_targets なし → JOIN で除外される
        broker = MockBrokerClient(available_cash=5_000_000.0)
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        signals = engine._read_signals()
        assert len(signals) == 0
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_execution_engine.py::TestReadSignals -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.execution.execution_engine'`

- [ ] **Step 3: `execution_engine.py` の骨格と `_read_signals()` を実装**

`src/kabusys/execution/execution_engine.py` を新規作成:

```python
# src/kabusys/execution/execution_engine.py
"""ExecutionEngine — Signal Queue Pull 型発注エンジン。

シグナル処理（8:50-9:10）+ WebSocket push ドレインループ（9:10-15:30）。
"""
from __future__ import annotations

import logging
import queue
import threading
from dataclasses import dataclass
from datetime import date, time

import duckdb

from kabusys.execution.broker_api import BrokerAPIProtocol
from kabusys.execution.order_manager import DuplicateOrderError, OrderManager
from kabusys.execution.order_repository import OrderRepository
from kabusys.execution.risk_manager import RiskManager

logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    target_date: date
    signal_send_start: time = time(8, 50)  # 発注開始時刻
    signal_send_end: time = time(9, 10)    # 発注締切時刻
    market_close: time = time(15, 30)      # セッション終了時刻


class ExecutionEngine:
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
        risk_manager: RiskManager,
        order_manager: OrderManager,
        duckdb_conn: duckdb.DuckDBPyConnection,
        config: EngineConfig,
    ) -> None:
        self._broker = broker
        self._repo = repo
        self._risk_manager = risk_manager
        self._order_manager = order_manager
        self._duckdb_conn = duckdb_conn
        self._config = config
        self._stop_event = threading.Event()
        self._push_queue: queue.Queue[dict] = queue.Queue()

    def _read_signals(self) -> list[dict]:
        """DuckDB から今日のシグナルを portfolio_targets と JOIN して返す。"""
        rows = self._duckdb_conn.execute(
            """
            SELECT s.code, s.side, pt.target_size AS qty, pt.entry_price AS price
            FROM signals s
            JOIN portfolio_targets pt ON s.date = pt.date AND s.code = pt.code
            WHERE s.date = ?
            ORDER BY s.signal_rank ASC NULLS LAST
            """,
            [self._config.target_date],
        ).fetchall()
        return [
            {"code": r[0], "side": r[1], "qty": int(r[2]), "price": float(r[3])}
            for r in rows
        ]
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_execution_engine.py::TestReadSignals -v
```

Expected: 2 passed

- [ ] **Step 5: Commit**

```bash
git add src/kabusys/execution/execution_engine.py tests/test_execution_engine.py
git commit -m "feat: ExecutionEngine scaffold and _read_signals() (#30)"
```

---

## Task 7: ExecutionEngine — シグナル処理ループ (Gate 1 + 2 + 発注)

**Files:**
- Modify: `src/kabusys/execution/execution_engine.py`
- Modify: `tests/test_execution_engine.py`

- [ ] **Step 1: シグナル処理のテストを追加**

`tests/test_execution_engine.py` に追加:

```python
class TestProcessSignals:

    def test_orders_created_for_valid_signals(self, sqlite_conn, duckdb_conn):
        """Gate 1/2 を通過したシグナルが OrderAccepted になる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        repo = engine._repo
        orders = repo.list_active()
        # fill_mode="instant" → Filled 状態（active）
        assert len(orders) == 1
        assert orders[0].code == "1234"

    def test_gate1_failure_skips_signal(self, sqlite_conn, duckdb_conn):
        """余力不足のシグナルはスキップされる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=0.0)  # 余力ゼロ
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        assert len(engine._repo.list_active()) == 0

    def test_duplicate_order_is_skipped(self, sqlite_conn, duckdb_conn):
        """DuplicateOrderError は skip（2回目呼び出しで重複にならない）"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        # 2回目: DuplicateOrderError が発生するが例外は出ない
        engine._process_signals()
        # 注文は1件のまま
        # fill_mode="instant" の場合 Filled → list_active に残る
        active = engine._repo.list_active()
        assert len(active) == 1

    def test_multiple_signals_processed(self, sqlite_conn, duckdb_conn):
        """複数シグナルがすべて処理される"""
        for code in ["1234", "5678", "9012"]:
            _insert_signal(duckdb_conn, code)
            _insert_target(duckdb_conn, code, qty=100, price=1000.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="instant")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()
        assert len(engine._repo.list_active()) == 3
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_execution_engine.py::TestProcessSignals -v
```

Expected: `AttributeError: 'ExecutionEngine' object has no attribute '_process_signals'`

- [ ] **Step 3: `_process_signals()` を実装**

`execution_engine.py` の `ExecutionEngine` クラスに追加:

```python
    def _process_signals(self) -> None:
        """今日のシグナルを読み込み、Gate 1/2 を通して発注する。"""
        from kabusys.execution.broker_api import OrderRequest
        from kabusys.execution.order_record import InvalidStateTransitionError

        signals = self._read_signals()
        logger.info("シグナル処理開始: %d 件", len(signals))

        for sig in signals:
            if self._stop_event.is_set():
                break

            code: str = sig["code"]
            side: str = sig["side"]
            qty: int = sig["qty"]
            price: float = sig["price"]
            signal_id = f"{self._config.target_date.isoformat()}_{code}_{side}"
            order_value = price * qty

            # Gate 1: シグナルレベル検査
            g1 = self._risk_manager.check_signal(signal_id, code, order_value)
            if not g1.passed:
                logger.info("Gate 1 NG - signal_id=%s: %s", signal_id, g1.reason)
                continue

            # Gate 2: エグゼキューションレベル検査（レート制限: リトライ最大3回）
            g2_passed = False
            for attempt in range(3):
                g2 = self._risk_manager.check_execution()
                if g2.passed:
                    g2_passed = True
                    break
                if "サーキットブレーカー" in g2.reason:
                    logger.warning("Gate 2 CB OPEN: シグナルループ停止 - %s", g2.reason)
                    return  # ドレインループは継続するため return のみ
                logger.debug("Gate 2 rate limit (attempt %d/3), waiting 0.2s", attempt + 1)
                self._stop_event.wait(timeout=0.2)

            if not g2_passed:
                logger.info("Gate 2 NG - signal_id=%s: %s", signal_id, g2.reason)
                continue

            # 発注
            try:
                order_type = "market" if price == 0.0 else "limit"
                record = self._order_manager.create_order(
                    signal_id,
                    OrderRequest(code=code, side=side, qty=qty, order_type=order_type, price=price),
                )
            except DuplicateOrderError:
                logger.info("DuplicateOrderError - skip: signal_id=%s", signal_id)
                continue

            try:
                self._order_manager.send_order(record.client_order_id)
                self._risk_manager.record_api_success()
                logger.info("発注成功: signal_id=%s, client_order_id=%s", signal_id, record.client_order_id)
            except Exception as exc:
                self._risk_manager.record_api_error()
                logger.error("発注失敗: signal_id=%s: %s", signal_id, exc)
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_execution_engine.py::TestProcessSignals -v
```

Expected: 4 passed

- [ ] **Step 5: Commit**

```bash
git add src/kabusys/execution/execution_engine.py tests/test_execution_engine.py
git commit -m "feat: ExecutionEngine signal processing loop with Gate 1/2 (#30)"
```

---

## Task 8: ExecutionEngine — push drain ループ + Gate 3 + kill_switch

**Files:**
- Modify: `src/kabusys/execution/execution_engine.py`
- Modify: `tests/test_execution_engine.py`

- [ ] **Step 1: drain ループと kill_switch のテストを追加**

`tests/test_execution_engine.py` に追加:

```python
class TestPushDrainAndKillSwitch:

    def test_handle_push_calls_sync_order(self, sqlite_conn, duckdb_conn):
        """push payload が _push_queue に入ると sync_order が呼ばれる"""
        _insert_signal(duckdb_conn, "1234")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()

        # OrderSent 状態の注文を取得
        uncertain = engine._repo.list_uncertain()
        assert len(uncertain) == 1
        order = uncertain[0]

        # broker の注文ステータスを "filled" に更新
        from kabusys.execution.broker_api import OrderStatus
        broker._orders[order.broker_order_id] = OrderStatus(
            order_id=order.broker_order_id,
            code="1234", side="buy", qty=100, filled_qty=100,
            status="filled", price=1500.0,
        )

        # push payload を直接キューに投入
        engine._push_queue.put({"OrderID": order.broker_order_id})
        engine._drain_push_queue()

        updated = engine._repo.get(order.client_order_id)
        from kabusys.execution.order_record import OrderState
        assert updated.state == OrderState.Filled

    def test_kill_switch_cancels_all_active_orders(self, sqlite_conn, duckdb_conn):
        """kill_switch() が全 active 注文をキャンセルして stop_event をセットする"""
        _insert_signal(duckdb_conn, "1234")
        _insert_signal(duckdb_conn, "5678")
        _insert_target(duckdb_conn, "1234", qty=100, price=1500.0)
        _insert_target(duckdb_conn, "5678", qty=100, price=1500.0)
        broker = MockBrokerClient(available_cash=5_000_000.0, fill_mode="never")
        engine = _make_engine(broker, sqlite_conn, duckdb_conn)
        engine._process_signals()

        active_before = engine._repo.list_active()
        assert len(active_before) >= 1  # OrderSent 状態の注文あり

        engine.kill_switch()

        assert engine._stop_event.is_set()
        # 全注文が Cancelled になっている
        from kabusys.execution.order_record import OrderState, InvalidStateTransitionError
        for order in engine._repo.list_active():
            # kill_switch 後は active 注文がない（または Filled のみ）
            assert order.state == OrderState.Filled  # "never" mode = OrderSent → skip

    def test_gate3_triggers_kill_switch_on_drawdown(self, sqlite_conn, duckdb_conn):
        """Gate 3 で drawdown 超過時に kill_switch が発動する"""
        broker = MockBrokerClient(available_cash=7_000_000.0)  # 30% drawdown
        config = RiskConfig(
            initial_portfolio_value=10_000_000.0,
            max_drawdown=0.15,
        )
        repo = OrderRepository(sqlite_conn)
        rm = RiskManager(broker=broker, repo=repo, config=config)
        order_manager = OrderManager(broker=broker, repo=repo)
        cfg = EngineConfig(target_date=TARGET_DATE)
        engine = ExecutionEngine(
            broker=broker, repo=repo, risk_manager=rm,
            order_manager=order_manager, duckdb_conn=duckdb_conn, config=cfg,
        )

        # 現在の評価額 7,000,000 円（30% drawdown > 15%）
        current_value = broker.get_available_cash()  # ポジションなし
        engine._check_gate3_and_maybe_kill(current_value)
        assert engine._stop_event.is_set()
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_execution_engine.py::TestPushDrainAndKillSwitch -v
```

Expected: `AttributeError: 'ExecutionEngine' object has no attribute '_drain_push_queue'`

- [ ] **Step 3: drain ループ・kill_switch・Gate 3 チェックを実装**

`execution_engine.py` に追加:

```python
    def _drain_push_queue(self) -> None:
        """_push_queue を全件処理する（sync_order + Gate 3 チェック）。"""
        while not self._push_queue.empty():
            try:
                payload = self._push_queue.get_nowait()
            except queue.Empty:
                break
            self._handle_push(payload)

    def _handle_push(self, payload: dict) -> None:
        """push 通知1件を処理する。"""
        order_id = payload.get("OrderID") or payload.get("order_id")
        if not order_id:
            logger.warning("push payload に OrderID がありません: %s", payload)
            return

        # broker_order_id から client_order_id を探す
        active_orders = self._repo.list_active()
        for order in active_orders:
            if order.broker_order_id == str(order_id):
                try:
                    self._order_manager.sync_order(order.client_order_id)
                    logger.debug("sync_order: client_order_id=%s", order.client_order_id)
                except Exception as exc:
                    logger.error("sync_order 失敗: %s", exc)
                break

        # Gate 3: ドローダウン監視
        positions = self._broker.get_positions()
        market_value = sum(
            p.qty * p.current_price
            for p in positions
            if p.current_price is not None
        )
        current_portfolio_value = self._broker.get_available_cash() + market_value
        self._check_gate3_and_maybe_kill(current_portfolio_value)

    def _check_gate3_and_maybe_kill(self, current_portfolio_value: float) -> None:
        """Gate 3 チェック。NG なら kill_switch() を発動。"""
        g3 = self._risk_manager.check_metrics(current_portfolio_value)
        if not g3.passed:
            logger.warning("Gate 3 NG: kill_switch 発動 - %s", g3.reason)
            self.kill_switch()

    def kill_switch(self) -> None:
        """全ループを停止し、全 active 注文をキャンセルする。"""
        self._stop_event.set()
        logger.warning("kill_switch 発動: 全 active 注文をキャンセルします")

        from kabusys.execution.order_record import InvalidStateTransitionError
        for order in self._repo.list_active():
            try:
                self._order_manager.cancel_order(order.client_order_id)
                logger.info("注文キャンセル: client_order_id=%s", order.client_order_id)
            except (InvalidStateTransitionError, RuntimeError) as exc:
                logger.debug("cancel_order スキップ: %s - %s", order.client_order_id, exc)
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_execution_engine.py::TestPushDrainAndKillSwitch -v
```

Expected: 3 passed

- [ ] **Step 5: 全テストが通ることを確認**

```bash
python -m pytest tests/ -v
```

Expected: すべて passed（エラーなし）

- [ ] **Step 6: Commit**

```bash
git add src/kabusys/execution/execution_engine.py tests/test_execution_engine.py
git commit -m "feat: ExecutionEngine push drain loop, Gate 3, kill_switch (#30)"
```

---

## Task 9: run_session() + __init__.py エクスポート更新

**Files:**
- Modify: `src/kabusys/execution/execution_engine.py`
- Modify: `src/kabusys/execution/__init__.py`

- [ ] **Step 1: `run_session()` を実装**

`execution_engine.py` に追加（本番用エントリポイント）:

```python
    def _websocket_worker(self) -> None:
        """WebSocket スレッド: kabu push を受信して _push_queue に投入する。"""
        def _on_message(payload: dict) -> None:
            self._push_queue.put(payload)

        # KabuStationClient のみ stream_push を持つ
        if not hasattr(self._broker, "stream_push"):
            logger.warning("broker が stream_push() を持たないため WebSocket スレッドをスキップします")
            return

        self._broker.stream_push(on_message=_on_message, stop_event=self._stop_event)

    def run_session(self) -> None:
        """セッション全体を実行する（本番用エントリポイント）。

        8:50 でシグナル処理 → 9:10 で発注締切 → 15:30 でセッション終了。
        テスト環境では _process_signals() と _drain_push_queue() を直接呼ぶこと。
        """
        import time as _time
        from datetime import datetime

        logger.info("ExecutionEngine: セッション開始 target_date=%s", self._config.target_date)

        # WebSocket スレッド起動
        ws_thread = threading.Thread(target=self._websocket_worker, daemon=True, name="ws-push")
        ws_thread.start()

        def _now_time() -> time:
            return datetime.now().time().replace(microsecond=0)

        # signal_send_start まで待機
        while _now_time() < self._config.signal_send_start and not self._stop_event.is_set():
            self._stop_event.wait(timeout=5.0)

        # シグナル処理ループ（8:50 ～ 9:10）
        if not self._stop_event.is_set():
            self._process_signals()

        # push drain ループ（9:10 ～ 15:30）
        while _now_time() < self._config.market_close and not self._stop_event.is_set():
            self._drain_push_queue()
            self._stop_event.wait(timeout=1.0)

        # セッション終了
        self._stop_event.set()
        ws_thread.join(timeout=5.0)
        logger.info("ExecutionEngine: セッション終了")
```

- [ ] **Step 2: `__init__.py` にエクスポートを追加**

`src/kabusys/execution/__init__.py` に以下を追加:

```python
from kabusys.execution.risk_manager import RiskConfig, RiskManager, RiskResult
from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
```

`__all__` に追加:
```python
    "RiskConfig",
    "RiskManager",
    "RiskResult",
    "EngineConfig",
    "ExecutionEngine",
```

- [ ] **Step 3: 全テストが通ることを確認**

```bash
python -m pytest tests/ -v
```

Expected: すべて passed

- [ ] **Step 4: import が通ることを確認**

```bash
python -c "from kabusys.execution import ExecutionEngine, RiskManager, EngineConfig, RiskConfig; print('OK')"
```

Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add src/kabusys/execution/execution_engine.py src/kabusys/execution/__init__.py
git commit -m "feat: ExecutionEngine.run_session() and __init__ exports (#30 #31)"
```

---

## Task 10: Issue クローズ処理

- [ ] **Step 1: GitHub Issues をクローズ**

```bash
gh issue close 33 --comment "PR #131 (Order State Machine) でテストも含めて実装済み"
gh issue close 31 --comment "risk_manager.py で3段階ガード実装完了"
gh issue close 30 --comment "execution_engine.py でメインループ + WebSocket 実装完了"
```

- [ ] **Step 2: PR を作成して main にマージ**

finishing-a-development-branch スキルを使用して完了する。
