# Reconciliation（自動復旧）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** システム再起動・クラッシュ後に OrderSent 状態の注文をブローカーと突合して自動同期し、ポジション差分を記録して安全に発注処理を再開する。

**Architecture:** `Reconciler` 独立クラスを新設し、`ExecutionEngine.__init__` に Optional で注入する。`run_session()` の先頭（WebSocket スレッド起動・signal_send_start 待機より前）で `reconciler.run()` を呼ぶ。既存の `list_uncertain()` と `sync_order()` をそのまま利用するため新しいブローカーAPIは不要。

**Tech Stack:** Python 3.10+, SQLite（`OrderRepository`）, `BrokerAPIProtocol`, `OrderManager.sync_order()`

---

## ファイル変更サマリー

| ファイル | 変更 |
|---------|------|
| `src/kabusys/execution/reconciler.py` | 新規作成 |
| `src/kabusys/execution/execution_engine.py` | `reconciler` 引数追加・`run_session` 先頭で呼ぶ |
| `src/kabusys/execution/__init__.py` | `Reconciler`・`ReconcileResult`・`PositionDiscrepancy` をエクスポート追加 |
| `tests/conftest.py` | `sqlite_conn`・`duckdb_conn` フィクスチャを追加（共有化） |
| `tests/test_execution_engine.py` | `sqlite_conn`・`duckdb_conn` フィクスチャを削除（conftest に移動） |
| `tests/test_reconciler.py` | 新規作成 |

---

## Task 1: Reconciler — データ型・スケルトン・no-op ケース

**Files:**
- Create: `src/kabusys/execution/reconciler.py`
- Create: `tests/test_reconciler.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
# tests/test_reconciler.py
"""Reconciler 単体テスト（Issue #32）"""
import sqlite3
import pytest
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.reconciler import Reconciler, ReconcileResult, PositionDiscrepancy


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return OrderRepository(conn)


def _make_reconciler(broker, repo) -> Reconciler:
    order_manager = OrderManager(broker=broker, repo=repo)
    return Reconciler(broker=broker, repo=repo, order_manager=order_manager)


class TestReconcilerNoOp:

    def test_returns_empty_result_when_no_uncertain_orders(self, repo):
        """uncertain 注文なし → ReconcileResult(0, 0, [])"""
        broker = MockBrokerClient()
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_synced == 0
        assert result.orders_no_status == 0
        assert result.position_discrepancies == []
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
cd C:/Users/tetsu/Projects/KabuSys
python -m pytest tests/test_reconciler.py -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.execution.reconciler'`

- [ ] **Step 3: `reconciler.py` スケルトンを実装**

```python
# src/kabusys/execution/reconciler.py
"""Reconciler — 起動時自動復旧・リコンシリエーション。

再起動・クラッシュ後に OrderSent 状態の注文をブローカーと突合して自動同期し、
ポジション差分をログに記録して安全に処理を再開する。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from kabusys.execution.broker_api import BrokerAPIError, BrokerAPIProtocol
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository

logger = logging.getLogger(__name__)


@dataclass
class PositionDiscrepancy:
    code: str
    broker_qty: int   # ブローカー側の保有数量
    local_qty: int    # ローカルDB推定値（注文履歴から集計）
    diff: int         # broker_qty - local_qty


@dataclass
class ReconcileResult:
    orders_synced: int = 0
    orders_no_status: int = 0
    position_discrepancies: list[PositionDiscrepancy] = field(default_factory=list)


class Reconciler:
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
        order_manager: OrderManager,
    ) -> None:
        self._broker = broker
        self._repo = repo
        self._order_manager = order_manager

    def run(self) -> ReconcileResult:
        """Step 1: OrderSent 照合 → Step 2: ポジション差分照合"""
        result = ReconcileResult()
        self._reconcile_orders(result)
        self._reconcile_positions(result)
        return result

    def _reconcile_orders(self, result: ReconcileResult) -> None:
        pass  # Task 2 で実装

    def _reconcile_positions(self, result: ReconcileResult) -> None:
        pass  # Task 3 で実装
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_reconciler.py::TestReconcilerNoOp -v
```

Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/execution/reconciler.py tests/test_reconciler.py
git commit -m "feat: add Reconciler skeleton with data types (Issue #32)"
```

---

## Task 2: `_reconcile_orders` — OrderSent 照合

**Files:**
- Modify: `src/kabusys/execution/reconciler.py`（`_reconcile_orders` を実装）
- Modify: `tests/test_reconciler.py`（テスト追加）

- [ ] **Step 1: 失敗するテストを書く**

`TestReconcilerNoOp` クラスの後に以下を追加する:

```python
class TestReconcileOrders:

    def test_broker_order_id_none_increments_no_status(self, repo):
        """broker_order_id=None の OrderSent は orders_no_status をインクリメント"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id="test-sent-001",
            signal_id="2026-03-29_1234_buy",
            code="1234", side="buy", qty=100,
            order_type="limit", price=1500.0,
            state=OrderState.OrderSent,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        # broker_order_id は None のまま（デフォルト）
        repo.save(record)
        broker = MockBrokerClient()
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_no_status == 1
        assert result.orders_synced == 0
        # 状態は変化しない
        from kabusys.execution.order_repository import OrderRepository
        updated = repo.get("test-sent-001")
        assert updated.state == OrderState.OrderSent

    def test_broker_returns_open_transitions_to_accepted(self, repo):
        """broker → 'open' なら OrderAccepted に遷移し orders_synced=1"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from kabusys.execution.broker_api import OrderStatus
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id="test-sent-002",
            signal_id="2026-03-29_5678_buy",
            code="5678", side="buy", qty=100,
            order_type="limit", price=1500.0,
            state=OrderState.OrderSent,
            broker_order_id="BROKER002",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(record)
        broker = MockBrokerClient()
        broker._orders["BROKER002"] = OrderStatus(
            order_id="BROKER002", code="5678", side="buy",
            qty=100, filled_qty=0, status="open", price=1500.0,
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_synced == 1
        assert result.orders_no_status == 0
        assert repo.get("test-sent-002").state == OrderState.OrderAccepted

    def test_broker_returns_filled_transitions_to_filled(self, repo):
        """broker → 'filled' なら Filled に遷移し orders_synced=1"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from kabusys.execution.broker_api import OrderStatus
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id="test-sent-003",
            signal_id="2026-03-29_9012_buy",
            code="9012", side="buy", qty=100,
            order_type="limit", price=1500.0,
            state=OrderState.OrderSent,
            broker_order_id="BROKER003",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(record)
        broker = MockBrokerClient()
        broker._orders["BROKER003"] = OrderStatus(
            order_id="BROKER003", code="9012", side="buy",
            qty=100, filled_qty=100, status="filled", price=1500.0,
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_synced == 1
        assert repo.get("test-sent-003").state == OrderState.Filled

    def test_get_order_status_returns_none_increments_no_status(self, repo):
        """broker_order_id 設定済みだが get_order_status() が None → orders_no_status=1"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id="test-sent-004",
            signal_id="2026-03-29_3333_buy",
            code="3333", side="buy", qty=100,
            order_type="limit", price=1500.0,
            state=OrderState.OrderSent,
            broker_order_id="BROKER_MISSING",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(record)
        broker = MockBrokerClient()  # _orders に "BROKER_MISSING" なし → None を返す
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.orders_no_status == 1
        assert result.orders_synced == 0
        assert repo.get("test-sent-004").state == OrderState.OrderSent

    def test_sync_order_broker_api_error_skips_and_continues(self, repo):
        """sync_order が BrokerAPIError を raise → スキップして他の注文は続行"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from kabusys.execution.broker_api import OrderStatus
        from unittest.mock import MagicMock, patch
        from datetime import datetime, timezone
        # 2件の OrderSent を作成
        for i, cid in enumerate(["sent-err-001", "sent-ok-001"], start=1):
            r = OrderRecord(
                client_order_id=cid,
                signal_id=f"2026-03-29_{1000+i}_buy",
                code=str(1000 + i), side="buy", qty=100,
                order_type="limit", price=1500.0,
                state=OrderState.OrderSent,
                broker_order_id=f"BROKER_X{i}",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
            repo.save(r)
        broker = MockBrokerClient()
        broker._orders["BROKER_X2"] = OrderStatus(
            order_id="BROKER_X2", code="1002", side="buy",
            qty=100, filled_qty=0, status="open", price=1500.0,
        )
        reconciler = _make_reconciler(broker, repo)
        # sent-err-001 の sync_order を BrokerAPIError にパッチ
        original_sync = reconciler._order_manager.sync_order
        def patched_sync(cid):
            if cid == "sent-err-001":
                raise BrokerAPIError("API failure")
            return original_sync(cid)
        reconciler._order_manager.sync_order = patched_sync
        result = reconciler.run()
        # sent-ok-001 は正常に処理される
        assert result.orders_synced == 1
        assert repo.get("sent-ok-001").state == OrderState.OrderAccepted

    def test_list_uncertain_exception_returns_empty_result(self, repo):
        """list_uncertain が Exception → ReconcileResult(0, 0, []) を返す、例外は伝播しない"""
        from unittest.mock import patch
        broker = MockBrokerClient()
        reconciler = _make_reconciler(broker, repo)
        with patch.object(repo, "list_uncertain", side_effect=Exception("DB error")):
            result = reconciler.run()
        assert result.orders_synced == 0
        assert result.orders_no_status == 0
        assert result.position_discrepancies == []
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_reconciler.py::TestReconcileOrders -v
```

Expected: FAIL（`_reconcile_orders` が pass のまま）

- [ ] **Step 3: `_reconcile_orders` を実装**

`reconciler.py` の `_reconcile_orders` を以下で置き換える:

```python
    def _reconcile_orders(self, result: ReconcileResult) -> None:
        try:
            uncertain = self._repo.list_uncertain()
        except Exception:
            logger.error("list_uncertain() 失敗: リコンシリエーションをスキップします", exc_info=True)
            return

        for record in uncertain:
            if record.broker_order_id is None:
                result.orders_no_status += 1
                logger.warning(
                    "broker_order_id 未設定（手動確認要）: client_order_id=%s",
                    record.client_order_id,
                )
                continue
            try:
                updated = self._order_manager.sync_order(record.client_order_id)
                if updated.state == record.state:
                    if updated.state == OrderState.OrderSent:
                        # broker が None を返した（注文レコードなし）
                        result.orders_no_status += 1
                        logger.warning(
                            "broker に注文なし（手動確認要）: client_order_id=%s, broker_order_id=%s",
                            record.client_order_id, record.broker_order_id,
                        )
                else:
                    result.orders_synced += 1
                    logger.info(
                        "注文状態同期: %s → %s (client_order_id=%s)",
                        record.state.value, updated.state.value, record.client_order_id,
                    )
            except BrokerAPIError:
                logger.error(
                    "sync_order 失敗（スキップ）: client_order_id=%s",
                    record.client_order_id, exc_info=True,
                )
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_reconciler.py::TestReconcileOrders -v
```

Expected: 6 PASS

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/execution/reconciler.py tests/test_reconciler.py
git commit -m "feat: implement _reconcile_orders in Reconciler (Issue #32)"
```

---

## Task 3: `_reconcile_positions` — ポジション差分照合

**Files:**
- Modify: `src/kabusys/execution/reconciler.py`（`_reconcile_positions` を実装）
- Modify: `tests/test_reconciler.py`（テスト追加）

- [ ] **Step 1: 失敗するテストを書く**

```python
class TestReconcilePositions:

    def _insert_filled_order(
        self, repo, code: str, side: str, qty: int, cid: str
    ) -> None:
        """Filled 状態の注文を DB に直接挿入するヘルパー。"""
        from kabusys.execution.order_record import OrderRecord, OrderState
        from datetime import datetime, timezone
        record = OrderRecord(
            client_order_id=cid,
            signal_id=f"sig_{cid}",
            code=code, side=side, qty=qty,
            order_type="limit", price=1500.0,
            state=OrderState.Filled,
            filled_qty=qty,
            broker_order_id=f"BRK_{cid}",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        repo.save(record)

    def test_no_discrepancy_when_positions_match(self, repo):
        """broker と local が一致 → position_discrepancies=[]"""
        from kabusys.execution.broker_api import Position
        self._insert_filled_order(repo, "1234", "buy", 100, "pos-001")
        broker = MockBrokerClient(
            initial_positions=[Position(code="1234", qty=100, avg_price=1500.0)]
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.position_discrepancies == []

    def test_discrepancy_detected_when_broker_has_more(self, repo):
        """broker 100株、local 80株 → diff=+20 の PositionDiscrepancy"""
        from kabusys.execution.broker_api import Position
        self._insert_filled_order(repo, "1234", "buy", 80, "pos-002")
        broker = MockBrokerClient(
            initial_positions=[Position(code="1234", qty=100, avg_price=1500.0)]
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert len(result.position_discrepancies) == 1
        d = result.position_discrepancies[0]
        assert d.code == "1234"
        assert d.broker_qty == 100
        assert d.local_qty == 80
        assert d.diff == 20

    def test_discrepancy_detected_when_local_has_more(self, repo):
        """local 100株、broker 0株 → diff=-100 の PositionDiscrepancy"""
        self._insert_filled_order(repo, "1234", "buy", 100, "pos-003")
        broker = MockBrokerClient()  # ポジションなし
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert len(result.position_discrepancies) == 1
        assert result.position_discrepancies[0].diff == -100

    def test_net_position_accounts_for_sell_orders(self, repo):
        """buy 100株 - sell 30株 = local 70株; broker 70株 → 差分なし"""
        from kabusys.execution.broker_api import Position
        self._insert_filled_order(repo, "1234", "buy", 100, "pos-buy-001")
        self._insert_filled_order(repo, "1234", "sell", 30, "pos-sell-001")
        broker = MockBrokerClient(
            initial_positions=[Position(code="1234", qty=70, avg_price=1500.0)]
        )
        reconciler = _make_reconciler(broker, repo)
        result = reconciler.run()
        assert result.position_discrepancies == []

    def test_get_positions_failure_skips_position_check(self, repo):
        """`get_positions()` が BrokerAPIError → position_discrepancies=[] で続行"""
        from unittest.mock import patch
        self._insert_filled_order(repo, "1234", "buy", 100, "pos-004")
        broker = MockBrokerClient()
        reconciler = _make_reconciler(broker, repo)
        with patch.object(broker, "get_positions", side_effect=BrokerAPIError("API error")):
            result = reconciler.run()
        assert result.position_discrepancies == []
        # 処理は続行している（例外が伝播していない）
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_reconciler.py::TestReconcilePositions -v
```

Expected: FAIL（`_reconcile_positions` が pass のまま）

- [ ] **Step 3: `_reconcile_positions` を実装**

`reconciler.py` の `_reconcile_positions` を以下で置き換える:

```python
    def _reconcile_positions(self, result: ReconcileResult) -> None:
        try:
            broker_positions = self._broker.get_positions()
        except BrokerAPIError:
            logger.warning("get_positions() 失敗: ポジション照合をスキップします", exc_info=True)
            return

        # ブローカーポジション: {code: qty}
        broker_map: dict[str, int] = {p.code: p.qty for p in broker_positions}

        # ローカル推定ポジション: Filled / PartialFill の注文から code ごとにネット集計
        # list_active() は Closed/Cancelled/Rejected を除く。Filled と PartialFill は含まれる。
        # ※ Closed 状態（ポジションクローズ済）は list_active() では取得できないため対象外。
        #   実運用では Filled buy - Filled sell のネットが現在保有数量に相当する。
        local_map: dict[str, int] = {}
        for record in self._repo.list_active():
            if record.state not in {OrderState.Filled, OrderState.PartialFill}:
                continue
            if record.side == "buy":
                local_map[record.code] = local_map.get(record.code, 0) + record.filled_qty
            elif record.side == "sell":
                local_map[record.code] = local_map.get(record.code, 0) - record.filled_qty

        # 差分照合
        for code in set(broker_map) | set(local_map):
            broker_qty = broker_map.get(code, 0)
            local_qty = local_map.get(code, 0)
            diff = broker_qty - local_qty
            if diff != 0:
                result.position_discrepancies.append(
                    PositionDiscrepancy(
                        code=code,
                        broker_qty=broker_qty,
                        local_qty=local_qty,
                        diff=diff,
                    )
                )
                logger.warning(
                    "ポジション差分検出: code=%s, broker=%d, local=%d, diff=%+d",
                    code, broker_qty, local_qty, diff,
                )
```

- [ ] **Step 4: テストが通ることを確認**

```bash
python -m pytest tests/test_reconciler.py::TestReconcilePositions -v
```

Expected: 5 PASS

- [ ] **Step 5: 全テストが通ることを確認**

```bash
python -m pytest tests/test_reconciler.py -v
```

Expected: 12 PASS

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/execution/reconciler.py tests/test_reconciler.py
git commit -m "feat: implement _reconcile_positions in Reconciler (Issue #32)"
```

---

## Task 4: ExecutionEngine 統合 + エクスポート追加

**Files:**
- Modify: `src/kabusys/execution/execution_engine.py`（`reconciler` 引数・`run_session` 先頭）
- Modify: `src/kabusys/execution/__init__.py`（エクスポート追加）
- Modify: `tests/test_reconciler.py`（統合テスト追加）

- [ ] **Step 1: 失敗するテストを書く**

まず `tests/conftest.py` に `sqlite_conn` と `duckdb_conn` フィクスチャを追加し、`tests/test_execution_engine.py` から同名フィクスチャを削除する。その後 `tests/test_reconciler.py` の末尾にテストクラスを追加する。

**`tests/conftest.py` の末尾に追加する:**

```python
import sqlite3
from kabusys.execution.order_repository import init_orders_db


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
        CREATE TABLE signals (date DATE, code VARCHAR, side VARCHAR, score FLOAT, signal_rank INTEGER)
    """)
    conn.execute("""
        CREATE TABLE portfolio_targets (date DATE, code VARCHAR, target_size INTEGER, entry_price FLOAT)
    """)
    yield conn
    conn.close()
```

**`tests/test_execution_engine.py` から以下のフィクスチャ定義を削除する（conftest に移動済みのため）:**

```python
# 削除: @pytest.fixture def sqlite_conn(): ... (lines 26-29)
# 削除: @pytest.fixture def duckdb_conn(): ... (lines 33-49)
```

**`tests/test_reconciler.py` の末尾に以下を追加する:**

```python
class TestExecutionEngineIntegration:

    def test_run_session_calls_reconciler_before_signal_processing(self, sqlite_conn, duckdb_conn):
        """reconciler.run() が run_session 内で WebSocket 起動より先に呼ばれる"""
        import sqlite3
        import duckdb as duckdb_mod
        from datetime import date, time
        from unittest.mock import MagicMock
        from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
        from kabusys.execution.order_manager import OrderManager
        from kabusys.execution.risk_manager import RiskConfig, RiskManager
        from kabusys.execution.reconciler import Reconciler, ReconcileResult

        broker = MockBrokerClient(available_cash=5_000_000.0)
        repo = OrderRepository(sqlite_conn)
        risk_manager = RiskManager(broker=broker, repo=repo, config=RiskConfig(initial_portfolio_value=10_000_000.0))
        order_manager = OrderManager(broker=broker, repo=repo)
        reconciler = MagicMock(spec=Reconciler)
        reconciler.run.return_value = ReconcileResult()

        cfg = EngineConfig(
            target_date=date(2026, 3, 29),
            signal_send_start=time(0, 0),
            signal_send_end=time(0, 0),   # シグナル処理をスキップ
            market_close=time(0, 0),       # 即終了
        )
        engine = ExecutionEngine(
            broker=broker,
            repo=repo,
            risk_manager=risk_manager,
            order_manager=order_manager,
            duckdb_conn=duckdb_conn,
            config=cfg,
            reconciler=reconciler,
        )
        engine.run_session()
        reconciler.run.assert_called_once()

    def test_run_session_without_reconciler_does_not_raise(self, sqlite_conn, duckdb_conn):
        """reconciler=None（デフォルト）でも run_session は正常動作する"""
        import duckdb as duckdb_mod
        from datetime import date, time
        from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine
        from kabusys.execution.order_manager import OrderManager
        from kabusys.execution.risk_manager import RiskConfig, RiskManager

        broker = MockBrokerClient(available_cash=5_000_000.0)
        repo = OrderRepository(sqlite_conn)
        risk_manager = RiskManager(broker=broker, repo=repo, config=RiskConfig(initial_portfolio_value=10_000_000.0))
        order_manager = OrderManager(broker=broker, repo=repo)
        cfg = EngineConfig(
            target_date=date(2026, 3, 29),
            signal_send_start=time(0, 0),
            signal_send_end=time(0, 0),
            market_close=time(0, 0),
        )
        # reconciler を渡さない（デフォルト None）→ 例外なし
        engine = ExecutionEngine(
            broker=broker, repo=repo, risk_manager=risk_manager,
            order_manager=order_manager, duckdb_conn=duckdb_conn, config=cfg,
        )
        engine.run_session()  # 例外が出なければ PASS
```

- [ ] **Step 2: テストが失敗することを確認**

```bash
python -m pytest tests/test_reconciler.py::TestExecutionEngineIntegration -v
```

Expected: FAIL（`ExecutionEngine.__init__` が `reconciler` 引数を受け取らない）

- [ ] **Step 3: `execution_engine.py` を修正**

`execution_engine.py` の import に追加:

```python
# 既存 import の後に追加
from kabusys.execution.reconciler import Reconciler
```

`ExecutionEngine.__init__` を修正（末尾に `reconciler` 追加）:

```python
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
        risk_manager: RiskManager,
        order_manager: OrderManager,
        duckdb_conn: duckdb.DuckDBPyConnection,
        config: EngineConfig,
        reconciler: Reconciler | None = None,  # ← 追加
    ) -> None:
        self._broker = broker
        self._repo = repo
        self._risk_manager = risk_manager
        self._order_manager = order_manager
        self._duckdb_conn = duckdb_conn
        self._config = config
        self._reconciler = reconciler           # ← 追加
        self._stop_event = threading.Event()
        self._push_queue: queue.Queue[dict] = queue.Queue()
```

`run_session()` の先頭（`logger.info(セッション開始)` の直後、WebSocket スレッド起動の前）に追加:

```python
        # 起動時リコンシリエーション（reconciler が設定されている場合のみ）
        if self._reconciler is not None:
            rec_result = self._reconciler.run()
            logger.info(
                "Reconciliation 完了: synced=%d, no_status=%d, position_discrepancies=%d",
                rec_result.orders_synced,
                rec_result.orders_no_status,
                len(rec_result.position_discrepancies),
            )
```

- [ ] **Step 4: `__init__.py` にエクスポートを追加**

`src/kabusys/execution/__init__.py` の末尾付近を以下のように修正:

既存の `from kabusys.execution.execution_engine import EngineConfig, ExecutionEngine` の後に追加:

```python
from kabusys.execution.reconciler import PositionDiscrepancy, ReconcileResult, Reconciler
```

`__all__` リストに追加:

```python
    "PositionDiscrepancy",
    "ReconcileResult",
    "Reconciler",
```

- [ ] **Step 5: テストが通ることを確認**

```bash
python -m pytest tests/test_reconciler.py -v
```

Expected: 14 PASS

- [ ] **Step 6: 全テストスイートが通ることを確認**

```bash
python -m pytest -v
```

Expected: 全テスト PASS（既存テストに回帰なし）

- [ ] **Step 7: コミット**

```bash
git add src/kabusys/execution/reconciler.py \
        src/kabusys/execution/execution_engine.py \
        src/kabusys/execution/__init__.py \
        tests/test_reconciler.py
git commit -m "feat: integrate Reconciler into ExecutionEngine, add exports (Issue #32)"
```
