# Order State Machine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `OrderRecord`・`OrderRepository`・`OrderManager` の3ファイルで Issue #29 の Order State Machine を実装し、クラッシュ安全な発注状態管理を実現する。

**Architecture:** 純粋ロジック層（`order_record.py`）・SQLite 永続化層（`order_repository.py`）・外向き API 層（`order_manager.py`）に責務を分離する。`order_manager.py` は `OrderSent` を SQLite に保存してから broker API を呼ぶことでクラッシュ安全性を担保する。Reconciliation（Issue #32）の入口となる `list_uncertain()` / `sync_order()` インターフェースを提供する。

**Tech Stack:** Python 3.10+, `sqlite3`（標準ライブラリ）, `pytest`, 既存の `MockBrokerClient`（`src/kabusys/execution/mock_client.py`）

---

## File Structure

| ファイル | 操作 | 責務 |
|---------|------|------|
| `src/kabusys/execution/order_record.py` | 新規作成 | `OrderState` enum・`InvalidStateTransitionError`・`OrderRecord` dataclass |
| `src/kabusys/execution/order_repository.py` | 新規作成 | `init_orders_db()`・`OrderRepository` クラス（SQLite 読み書き） |
| `src/kabusys/execution/order_manager.py` | 新規作成 | `DuplicateOrderError`・`OrderManager` クラス（外向き API） |
| `src/kabusys/execution/__init__.py` | 修正 | 新クラス・例外をエクスポートに追加 |
| `tests/test_order_state_machine.py` | 新規作成 | 3グループのテスト（Group1: 純粋ロジック / Group2: Repository / Group3: Manager） |

**依存関係（既存ファイル・読み取りのみ）:**
- `src/kabusys/execution/broker_api.py` — `BrokerAPIProtocol`, `OrderRequest`, `OrderResponse`, `OrderStatus`, `OrderRejectedError`
- `src/kabusys/execution/mock_client.py` — `MockBrokerClient`（テスト用）

---

## Task 1: OrderRecord — 状態遷移ロジック（DB なし）

**Files:**
- Create: `src/kabusys/execution/order_record.py`
- Create: `tests/test_order_state_machine.py`

### TDD ステップ

- [ ] **Step 1: テストファイルを作成してグループ1の failing テストを書く**

`tests/test_order_state_machine.py` を以下の内容で作成する:

```python
# tests/test_order_state_machine.py
"""Order State Machine テスト

Group 1: OrderRecord 状態遷移（DB なし・Mock なし）
Group 2: OrderRepository（インメモリ SQLite）
Group 3: OrderManager（MockBrokerClient + インメモリ SQLite）
"""
import sqlite3
import uuid
from datetime import datetime, timezone

import pytest

from kabusys.execution.broker_api import OrderRequest
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_record import (
    InvalidStateTransitionError,
    OrderRecord,
    OrderState,
)
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.order_manager import DuplicateOrderError, OrderManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_record(**kwargs) -> OrderRecord:
    """テスト用 OrderRecord を生成するヘルパー。"""
    now = datetime.now(timezone.utc)
    defaults = dict(
        client_order_id=str(uuid.uuid4()),
        signal_id="sig-001",
        code="1234",
        side="buy",
        qty=100,
        order_type="market",
        price=0.0,
        state=OrderState.OrderCreated,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return OrderRecord(**defaults)


@pytest.fixture
def db_conn():
    conn = sqlite3.connect(":memory:")
    init_orders_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def repo(db_conn):
    return OrderRepository(db_conn)


@pytest.fixture
def mock_broker():
    return MockBrokerClient(fill_mode="instant", available_cash=1_000_000.0)


@pytest.fixture
def manager(mock_broker, repo):
    return OrderManager(broker=mock_broker, repo=repo)


# ---------------------------------------------------------------------------
# Group 1: OrderRecord 状態遷移（DB なし・Mock なし）
# ---------------------------------------------------------------------------


def test_normal_transition_created_to_closed():
    """正常遷移: Created→Sent→Accepted→Filled→Closed"""
    r = _make_record()
    r.transition_to(OrderState.OrderSent)
    assert r.state == OrderState.OrderSent
    r.transition_to(OrderState.OrderAccepted, broker_order_id="B001")
    assert r.broker_order_id == "B001"
    r.transition_to(OrderState.Filled, filled_qty=100, avg_fill_price=1500.0)
    assert r.filled_qty == 100
    assert r.avg_fill_price == 1500.0
    r.transition_to(OrderState.Closed)
    assert r.state == OrderState.Closed


def test_partial_fill_transition():
    """部分約定: Accepted→PartialFill→Filled→Closed"""
    r = _make_record(state=OrderState.OrderAccepted)
    r.transition_to(OrderState.PartialFill, filled_qty=50)
    assert r.state == OrderState.PartialFill
    r.transition_to(OrderState.Filled, filled_qty=100)
    r.transition_to(OrderState.Closed)
    assert r.state == OrderState.Closed


def test_cancel_from_created():
    """Created → Cancelled"""
    r = _make_record()
    r.transition_to(OrderState.Cancelled)
    assert r.state == OrderState.Cancelled


def test_cancel_from_accepted():
    """Accepted → Cancelled"""
    r = _make_record(state=OrderState.OrderAccepted)
    r.transition_to(OrderState.Cancelled)
    assert r.state == OrderState.Cancelled


def test_reject_from_created():
    """Created → Rejected（リスク統制拒否）"""
    r = _make_record()
    r.transition_to(OrderState.Rejected, error_message="余力不足")
    assert r.state == OrderState.Rejected
    assert r.error_message == "余力不足"


def test_reject_from_sent():
    """Sent → Rejected（証券会社拒否）"""
    r = _make_record(state=OrderState.OrderSent)
    r.transition_to(OrderState.Rejected)
    assert r.state == OrderState.Rejected


def test_invalid_transition_filled_to_sent():
    """不正遷移: Filled → Sent は InvalidStateTransitionError"""
    r = _make_record(state=OrderState.Filled)
    with pytest.raises(InvalidStateTransitionError):
        r.transition_to(OrderState.OrderSent)


def test_invalid_transition_closed_to_accepted():
    """不正遷移: Closed → Accepted は InvalidStateTransitionError"""
    r = _make_record(state=OrderState.Closed)
    with pytest.raises(InvalidStateTransitionError):
        r.transition_to(OrderState.OrderAccepted)


def test_transition_updates_updated_at():
    """transition_to は updated_at を更新する"""
    r = _make_record()
    before = r.updated_at
    r.transition_to(OrderState.Cancelled)
    assert r.updated_at >= before
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_order_state_machine.py -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.execution.order_record'`

- [ ] **Step 3: `order_record.py` を実装する**

`src/kabusys/execution/order_record.py` を以下の内容で作成する:

```python
# src/kabusys/execution/order_record.py
"""OrderRecord dataclass と状態遷移ルール（DB なし純粋ロジック）。"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class OrderState(str, enum.Enum):
    OrderCreated = "created"
    OrderSent = "sent"
    OrderAccepted = "accepted"
    PartialFill = "partial"
    Filled = "filled"
    Closed = "closed"
    Cancelled = "cancelled"
    Rejected = "rejected"


_ALLOWED_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.OrderCreated: {OrderState.OrderSent, OrderState.Rejected, OrderState.Cancelled},
    OrderState.OrderSent: {OrderState.OrderAccepted, OrderState.Rejected, OrderState.Cancelled},
    OrderState.OrderAccepted: {
        OrderState.PartialFill,
        OrderState.Filled,
        OrderState.Cancelled,
        OrderState.Rejected,
    },
    OrderState.PartialFill: {OrderState.Filled, OrderState.Cancelled},
    OrderState.Filled: {OrderState.Closed},
    OrderState.Closed: set(),
    OrderState.Cancelled: set(),
    OrderState.Rejected: set(),
}


class InvalidStateTransitionError(Exception):
    """不正な状態遷移を試みた場合に raise される。"""


@dataclass
class OrderRecord:
    client_order_id: str
    signal_id: str
    code: str
    side: str
    qty: int
    order_type: str
    price: float
    state: OrderState
    broker_order_id: str | None = None
    filled_qty: int = 0
    avg_fill_price: float | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: str | None = None

    def transition_to(self, new_state: OrderState, **kwargs) -> None:
        """
        状態遷移を検証して self.state を更新する。
        不正な遷移は InvalidStateTransitionError を raise する。
        kwargs には broker_order_id / filled_qty / avg_fill_price / error_message を渡せる。
        updated_at は呼び出し時点の UTC に自動更新される。
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"{self.state.value} → {new_state.value} は許可されていない遷移です"
            )
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
```

- [ ] **Step 4: Group 1 テストがすべて通ることを確認する**

```
pytest tests/test_order_state_machine.py -k "test_normal_transition or test_partial or test_cancel or test_reject or test_invalid or test_transition_updates" -v
```

Expected: 9 passed

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/execution/order_record.py tests/test_order_state_machine.py
git commit -m "feat: add OrderRecord and OrderState with transition rules (Issue #29)"
```

---

## Task 2: OrderRepository — SQLite 永続化

**Files:**
- Create: `src/kabusys/execution/order_repository.py`
- Modify: `tests/test_order_state_machine.py` (Group 2 テストを追加)

### TDD ステップ

- [ ] **Step 1: Group 2 テストを `tests/test_order_state_machine.py` に追加する**

ファイル末尾に以下を追記する:

```python
# ---------------------------------------------------------------------------
# Group 2: OrderRepository（インメモリ SQLite）
# ---------------------------------------------------------------------------


def test_repo_save_and_get_roundtrip(repo):
    """save → get でフィールドが完全に一致する"""
    r = _make_record()
    repo.save(r)
    fetched = repo.get(r.client_order_id)
    assert fetched is not None
    assert fetched.client_order_id == r.client_order_id
    assert fetched.signal_id == r.signal_id
    assert fetched.code == r.code
    assert fetched.side == r.side
    assert fetched.qty == r.qty
    assert fetched.order_type == r.order_type
    assert fetched.price == r.price
    assert fetched.state == OrderState.OrderCreated
    assert fetched.broker_order_id is None
    assert fetched.filled_qty == 0
    assert fetched.avg_fill_price is None
    assert fetched.error_message is None


def test_repo_save_duplicate_raises_integrity_error(repo):
    """同一 client_order_id の save は IntegrityError"""
    r = _make_record()
    repo.save(r)
    with pytest.raises(Exception):  # sqlite3.IntegrityError
        repo.save(r)


def test_repo_update_modifies_state(repo):
    """update で状態が更新される"""
    r = _make_record()
    repo.save(r)
    r.transition_to(OrderState.OrderSent)
    repo.update(r)
    fetched = repo.get(r.client_order_id)
    assert fetched.state == OrderState.OrderSent


def test_repo_update_nonexistent_raises(repo):
    """存在しない client_order_id の update は RuntimeError"""
    r = _make_record()
    with pytest.raises(RuntimeError):
        repo.update(r)


def test_repo_list_active_excludes_terminal_states(repo):
    """list_active は Closed / Cancelled / Rejected を除外する"""
    active = _make_record(signal_id="sig-active", state=OrderState.OrderAccepted)
    closed = _make_record(
        client_order_id=str(uuid.uuid4()), signal_id="sig-closed", state=OrderState.Closed
    )
    cancelled = _make_record(
        client_order_id=str(uuid.uuid4()), signal_id="sig-cancelled", state=OrderState.Cancelled
    )
    rejected = _make_record(
        client_order_id=str(uuid.uuid4()), signal_id="sig-rejected", state=OrderState.Rejected
    )
    for r in [active, closed, cancelled, rejected]:
        repo.save(r)

    result = repo.list_active()
    ids = [r.client_order_id for r in result]
    assert active.client_order_id in ids
    assert closed.client_order_id not in ids
    assert cancelled.client_order_id not in ids
    assert rejected.client_order_id not in ids


def test_repo_list_uncertain_returns_only_sent(repo):
    """list_uncertain は OrderSent のみ返す"""
    sent = _make_record(signal_id="sig-sent", state=OrderState.OrderSent)
    accepted = _make_record(
        client_order_id=str(uuid.uuid4()),
        signal_id="sig-accepted",
        state=OrderState.OrderAccepted,
    )
    for r in [sent, accepted]:
        repo.save(r)

    result = repo.list_uncertain()
    assert len(result) == 1
    assert result[0].client_order_id == sent.client_order_id


def test_repo_get_returns_none_for_unknown(repo):
    """存在しない ID は None を返す"""
    assert repo.get("unknown-id") is None


def test_repo_get_by_signal(repo):
    """get_by_signal は同一 signal_id のレコードをすべて返す"""
    r1 = _make_record(signal_id="sig-x")
    r2 = _make_record(
        client_order_id=str(uuid.uuid4()), signal_id="sig-x", state=OrderState.Cancelled
    )
    r3 = _make_record(
        client_order_id=str(uuid.uuid4()), signal_id="sig-other"
    )
    for r in [r1, r2, r3]:
        repo.save(r)

    result = repo.get_by_signal("sig-x")
    ids = [r.client_order_id for r in result]
    assert r1.client_order_id in ids
    assert r2.client_order_id in ids
    assert r3.client_order_id not in ids
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_order_state_machine.py -k "test_repo" -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.execution.order_repository'`

- [ ] **Step 3: `order_repository.py` を実装する**

`src/kabusys/execution/order_repository.py` を以下の内容で作成する:

```python
# src/kabusys/execution/order_repository.py
"""OrderRepository — SQLite 永続化（状態管理のみ）。

使用規則:
  - save()  : OrderCreated レコードの初回挿入専用。重複は IntegrityError。
  - update(): 状態変更後の永続化に使用する。save() で状態変更しないこと。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime

from kabusys.execution.order_record import OrderRecord, OrderState

_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS orders (
    client_order_id  TEXT     NOT NULL PRIMARY KEY,
    signal_id        TEXT     NOT NULL,
    code             TEXT     NOT NULL,
    side             TEXT     NOT NULL CHECK (side IN ('buy', 'sell')),
    qty              INTEGER  NOT NULL,
    order_type       TEXT     NOT NULL CHECK (order_type IN ('market', 'limit')),
    price            REAL     NOT NULL DEFAULT 0.0,
    state            TEXT     NOT NULL,
    broker_order_id  TEXT,
    filled_qty       INTEGER  NOT NULL DEFAULT 0,
    avg_fill_price   REAL,
    error_message    TEXT,
    created_at       TEXT     NOT NULL,
    updated_at       TEXT     NOT NULL
)
"""
_CREATE_INDEX_STATE = "CREATE INDEX IF NOT EXISTS idx_orders_state  ON orders (state)"
_CREATE_INDEX_SIGNAL = "CREATE INDEX IF NOT EXISTS idx_orders_signal ON orders (signal_id)"

# Filled は終端ではなく "active" 扱い（Closed になるまで list_active で返す）
# order_manager.py の _TERMINAL_STATES（キャンセル可否判定用）とは意図が異なる
_TERMINAL_STATES = frozenset(
    {OrderState.Closed.value, OrderState.Cancelled.value, OrderState.Rejected.value}
)


def init_orders_db(conn: sqlite3.Connection) -> None:
    """orders テーブルとインデックスを作成する（冪等）。"""
    conn.execute(_CREATE_TABLE)
    conn.execute(_CREATE_INDEX_STATE)
    conn.execute(_CREATE_INDEX_SIGNAL)
    conn.commit()


def _row_to_record(row: sqlite3.Row) -> OrderRecord:
    return OrderRecord(
        client_order_id=row["client_order_id"],
        signal_id=row["signal_id"],
        code=row["code"],
        side=row["side"],
        qty=row["qty"],
        order_type=row["order_type"],
        price=row["price"],
        state=OrderState(row["state"]),
        broker_order_id=row["broker_order_id"],
        filled_qty=row["filled_qty"],
        avg_fill_price=row["avg_fill_price"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        error_message=row["error_message"],
    )


class OrderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self._conn = conn
        self._conn.row_factory = sqlite3.Row

    def save(self, record: OrderRecord) -> None:
        """INSERT のみ。重複 client_order_id は sqlite3.IntegrityError。
        使用場面: OrderCreated レコードの初回挿入のみ。
        """
        self._conn.execute(
            """
            INSERT INTO orders (
                client_order_id, signal_id, code, side, qty, order_type, price,
                state, broker_order_id, filled_qty, avg_fill_price, error_message,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.client_order_id,
                record.signal_id,
                record.code,
                record.side,
                record.qty,
                record.order_type,
                record.price,
                record.state.value,
                record.broker_order_id,
                record.filled_qty,
                record.avg_fill_price,
                record.error_message,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
            ),
        )
        self._conn.commit()

    def update(self, record: OrderRecord) -> None:
        """UPDATE（存在しない場合は RuntimeError）。"""
        cursor = self._conn.execute(
            """
            UPDATE orders SET
                state = ?, broker_order_id = ?, filled_qty = ?, avg_fill_price = ?,
                error_message = ?, updated_at = ?
            WHERE client_order_id = ?
            """,
            (
                record.state.value,
                record.broker_order_id,
                record.filled_qty,
                record.avg_fill_price,
                record.error_message,
                record.updated_at.isoformat(),
                record.client_order_id,
            ),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            raise RuntimeError(f"注文が見つかりません: {record.client_order_id}")

    def get(self, client_order_id: str) -> OrderRecord | None:
        row = self._conn.execute(
            "SELECT * FROM orders WHERE client_order_id = ?", (client_order_id,)
        ).fetchone()
        return _row_to_record(row) if row else None

    def get_by_signal(self, signal_id: str) -> list[OrderRecord]:
        rows = self._conn.execute(
            "SELECT * FROM orders WHERE signal_id = ?", (signal_id,)
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def list_active(self) -> list[OrderRecord]:
        """state が Closed / Cancelled / Rejected 以外を返す。"""
        placeholders = ",".join("?" * len(_TERMINAL_STATES))
        rows = self._conn.execute(
            f"SELECT * FROM orders WHERE state NOT IN ({placeholders})",
            tuple(_TERMINAL_STATES),
        ).fetchall()
        return [_row_to_record(r) for r in rows]

    def list_uncertain(self) -> list[OrderRecord]:
        """state == OrderSent のみ返す（Reconciliation 用：Issue #32 の入口）。"""
        rows = self._conn.execute(
            "SELECT * FROM orders WHERE state = ?", (OrderState.OrderSent.value,)
        ).fetchall()
        return [_row_to_record(r) for r in rows]
```

- [ ] **Step 4: Group 2 テストがすべて通ることを確認する**

```
pytest tests/test_order_state_machine.py -k "test_repo" -v
```

Expected: 8 passed

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/execution/order_repository.py tests/test_order_state_machine.py
git commit -m "feat: add OrderRepository with SQLite persistence (Issue #29)"
```

---

## Task 3: OrderManager — 外向き API

**Files:**
- Create: `src/kabusys/execution/order_manager.py`
- Modify: `tests/test_order_state_machine.py` (Group 3 テストを追加)

### TDD ステップ

- [ ] **Step 1: Group 3 テストを `tests/test_order_state_machine.py` に追加する**

ファイル末尾に以下を追記する:

```python
# ---------------------------------------------------------------------------
# Group 3: OrderManager（MockBrokerClient + インメモリ SQLite）
# ---------------------------------------------------------------------------


def test_create_order_returns_created_state(manager, repo):
    """create_order は OrderCreated レコードを DB に保存して返す"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = manager.create_order("sig-001", request)

    assert record.state == OrderState.OrderCreated
    assert record.client_order_id is not None
    assert record.signal_id == "sig-001"
    # DB に保存されている
    assert repo.get(record.client_order_id) is not None


def test_create_order_duplicate_signal_raises(manager):
    """同一 signal_id の active 注文が存在する場合は DuplicateOrderError"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    manager.create_order("sig-dup", request)
    with pytest.raises(DuplicateOrderError):
        manager.create_order("sig-dup", request)


def test_create_order_allows_reuse_of_terminal_signal(manager):
    """Closed / Cancelled / Rejected の signal_id は再利用できる"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = manager.create_order("sig-reuse", request)
    # 手動で Cancelled に遷移
    record.transition_to(OrderState.Cancelled)
    from kabusys.execution.order_repository import OrderRepository
    manager._repo.update(record)
    # 同一 signal_id で再発注できる
    new_record = manager.create_order("sig-reuse", request)
    assert new_record.state == OrderState.OrderCreated


def test_send_order_normal_flow(manager):
    """send_order: OrderCreated → OrderAccepted（broker_order_id が設定される）"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = manager.create_order("sig-send", request)
    result = manager.send_order(record.client_order_id)

    assert result.state == OrderState.OrderAccepted
    assert result.broker_order_id is not None


def test_send_order_broker_rejected(repo):
    """send_order で broker が OrderRejectedError を raise したら Rejected に遷移"""
    from kabusys.execution.broker_api import OrderRejectedError
    from kabusys.execution.mock_client import MockBrokerClient

    reject_broker = MockBrokerClient(fill_mode="reject", available_cash=1_000_000.0)
    m = OrderManager(broker=reject_broker, repo=repo)
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = m.create_order("sig-reject", request)
    result = m.send_order(record.client_order_id)

    assert result.state == OrderState.Rejected
    assert result.error_message is not None


def test_send_order_persists_sent_state_before_broker_call(repo):
    """クラッシュ安全性: OrderSent が broker 呼び出し前に SQLite に永続化される。
    broker が予期しない例外を raise しても OrderSent レコードが DB に残り、
    list_uncertain() が検出できることを確認する。
    """
    from kabusys.execution.broker_api import OrderRejectedError

    class CrashingBroker:
        def send_order(self, order):
            raise RuntimeError("プロセスクラッシュ模擬")

        def cancel_order(self, order_id): pass
        def get_order_status(self, order_id): return None
        def get_positions(self): return []
        def get_available_cash(self): return 1_000_000.0

    crash_manager = OrderManager(broker=CrashingBroker(), repo=repo)
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = crash_manager.create_order("sig-crash", request)

    with pytest.raises(RuntimeError):
        crash_manager.send_order(record.client_order_id)

    # DB に OrderSent レコードが残っている = Reconciliation で検出可能
    uncertain = repo.list_uncertain()
    assert len(uncertain) == 1
    assert uncertain[0].client_order_id == record.client_order_id
    assert uncertain[0].state == OrderState.OrderSent


def test_sync_order_filled(manager):
    """sync_order: broker が 'filled' を返したら Filled に遷移する"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = manager.create_order("sig-sync-filled", request)
    manager.send_order(record.client_order_id)  # OrderAccepted に遷移

    result = manager.sync_order(record.client_order_id)
    # fill_mode="instant" なので broker は "filled" を返す
    assert result.state == OrderState.Filled


def test_sync_order_broker_returns_none(manager, repo):
    """sync_order: broker が None を返した場合は状態変化なし"""
    # broker_order_id が設定されていないレコードを直接 DB に挿入
    r = _make_record(signal_id="sig-sync-none", state=OrderState.OrderAccepted)
    repo.save(r)

    result = manager.sync_order(r.client_order_id)
    assert result.state == OrderState.OrderAccepted  # 変化なし


def test_sync_order_open_returns_accepted(repo):
    """sync_order: broker が 'open' を返したら OrderAccepted に遷移する（Reconciliation ケース）"""
    from kabusys.execution.broker_api import OrderStatus

    class StubBrokerReturnsOpen:
        def get_order_status(self, order_id):
            return OrderStatus(
                order_id=order_id,
                code="1234",
                side="buy",
                qty=100,
                filled_qty=0,
                status="open",
                price=None,
            )

        def send_order(self, order):
            from kabusys.execution.broker_api import OrderResponse
            return OrderResponse(order_id="broker-recon-001")

        def cancel_order(self, order_id): pass
        def get_positions(self): return []
        def get_available_cash(self): return 1_000_000.0

    m = OrderManager(broker=StubBrokerReturnsOpen(), repo=repo)

    # OrderSent 状態のレコードを直接 DB に保存（クラッシュ後に残ったシナリオ）
    r = _make_record(
        signal_id="sig-recon",
        state=OrderState.OrderSent,
        broker_order_id="broker-recon-001",
    )
    repo.save(r)

    result = m.sync_order(r.client_order_id)
    assert result.state == OrderState.OrderAccepted


def test_cancel_order_accepted(manager):
    """cancel_order: OrderAccepted → Cancelled"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = manager.create_order("sig-cancel", request)
    manager.send_order(record.client_order_id)  # OrderAccepted

    # fill_mode="instant" なので既に Filled になっている可能性があるため、
    # OrderAccepted 状態のレコードを直接作って cancel する
    from kabusys.execution.order_record import InvalidStateTransitionError
    # broker_order_id=None: broker にはまだ送信前のレコードとしてキャンセルする
    # （broker_order_id が設定されていない場合、cancel_order は broker を呼ばない）
    accepted = _make_record(
        signal_id="sig-cancel-direct",
        state=OrderState.OrderAccepted,
        broker_order_id=None,
    )
    manager._repo.save(accepted)
    result = manager.cancel_order(accepted.client_order_id)
    assert result.state == OrderState.Cancelled


def test_cancel_order_terminal_state_raises(manager, repo):
    """cancel_order: Filled の注文は broker を呼ばず InvalidStateTransitionError"""
    from kabusys.execution.order_record import InvalidStateTransitionError

    filled = _make_record(
        signal_id="sig-cancel-filled",
        state=OrderState.Filled,
        broker_order_id="broker-filled-001",
    )
    repo.save(filled)
    with pytest.raises(InvalidStateTransitionError):
        manager.cancel_order(filled.client_order_id)
```

- [ ] **Step 2: テストが失敗することを確認する**

```
pytest tests/test_order_state_machine.py -k "test_create or test_send or test_sync or test_cancel" -v
```

Expected: `ModuleNotFoundError: No module named 'kabusys.execution.order_manager'`

- [ ] **Step 3: `order_manager.py` を実装する**

`src/kabusys/execution/order_manager.py` を以下の内容で作成する:

```python
# src/kabusys/execution/order_manager.py
"""OrderManager — Order State Machine の外向き API。

signal_queue からシグナルを受け取り、broker API 経由で発注・状態管理を行う。
OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせる。
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from kabusys.execution.broker_api import BrokerAPIProtocol, OrderRequest, OrderRejectedError
from kabusys.execution.order_record import InvalidStateTransitionError, OrderRecord, OrderState
from kabusys.execution.order_repository import OrderRepository


class DuplicateOrderError(Exception):
    """同一 signal_id の active 注文が既に存在する場合に raise される。"""


_STATUS_TO_STATE: dict[str, OrderState] = {
    "open": OrderState.OrderAccepted,
    "partial": OrderState.PartialFill,
    "filled": OrderState.Filled,
    "cancelled": OrderState.Cancelled,
    "rejected": OrderState.Rejected,
}

_TERMINAL_STATES = frozenset(
    {OrderState.Closed, OrderState.Cancelled, OrderState.Rejected, OrderState.Filled}
)


class OrderManager:
    def __init__(self, broker: BrokerAPIProtocol, repo: OrderRepository) -> None:
        self._broker = broker
        self._repo = repo

    def create_order(self, signal_id: str, request: OrderRequest) -> OrderRecord:
        """
        OrderCreated レコードを生成して DB に保存する。
        同一 signal_id の active 注文が存在する場合は DuplicateOrderError を raise。
        client_order_id には uuid4 を採番する。
        """
        existing = self._repo.get_by_signal(signal_id)
        active = [
            r for r in existing
            if r.state not in {OrderState.Closed, OrderState.Cancelled, OrderState.Rejected}
        ]
        if active:
            raise DuplicateOrderError(
                f"signal_id={signal_id} の active 注文が既に存在します: "
                f"{active[0].client_order_id}"
            )

        now = datetime.now(timezone.utc)
        record = OrderRecord(
            client_order_id=str(uuid.uuid4()),
            signal_id=signal_id,
            code=request.code,
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            price=request.price,
            state=OrderState.OrderCreated,
            created_at=now,
            updated_at=now,
        )
        self._repo.save(record)
        return record

    def send_order(self, client_order_id: str) -> OrderRecord:
        """
        以下の順序で処理する（クラッシュ安全性のため OrderSent の永続化を broker 呼び出しの前に行う）:

        1. OrderCreated → OrderSent に遷移して SQLite に保存（commit）
        2. broker API の send_order を呼び出す
        3. 成功: broker_order_id を受領 → OrderAccepted に遷移して SQLite を更新
        4. 失敗（OrderRejectedError）: Rejected に遷移して SQLite を更新

        ステップ1 と broker 呼び出しの間でクラッシュした場合、OrderSent レコードが残る。
        Reconciliation（Issue #32）が list_uncertain() でこのレコードを検出して状態を回復する。
        """
        record = self._repo.get(client_order_id)
        if record is None:
            raise RuntimeError(f"注文が見つかりません: {client_order_id}")

        # Step 1: OrderSent に遷移して永続化（broker 呼び出し前）
        record.transition_to(OrderState.OrderSent)
        self._repo.update(record)

        # Step 2-4: broker API 呼び出し
        api_request = OrderRequest(
            code=record.code,
            side=record.side,
            qty=record.qty,
            order_type=record.order_type,
            price=record.price,
        )
        try:
            response = self._broker.send_order(api_request)
            record.transition_to(OrderState.OrderAccepted, broker_order_id=response.order_id)
        except OrderRejectedError as exc:
            record.transition_to(OrderState.Rejected, error_message=str(exc))

        self._repo.update(record)
        return record

    def sync_order(self, client_order_id: str) -> OrderRecord:
        """
        broker API の get_order_status を呼び、最新状態に同期する。
        broker が None を返した場合は状態を変更しない。
        broker が None を返す可能性: broker_order_id 未設定（クラッシュ後）または注文が見つからない。
        OrderSent に対して broker が 'open' を返した場合は OrderAccepted に遷移する。
        """
        record = self._repo.get(client_order_id)
        if record is None:
            raise RuntimeError(f"注文が見つかりません: {client_order_id}")

        if record.broker_order_id is None:
            return record

        status = self._broker.get_order_status(record.broker_order_id)
        if status is None:
            return record

        new_state = _STATUS_TO_STATE.get(status.status)
        if new_state is None or new_state == record.state:
            return record

        try:
            record.transition_to(
                new_state,
                filled_qty=status.filled_qty,
                avg_fill_price=status.price,
            )
            self._repo.update(record)
        except InvalidStateTransitionError:
            pass  # 既に終端状態の場合は無視

        return record

    def cancel_order(self, client_order_id: str) -> OrderRecord:
        """
        DB の現在状態を確認し、終端状態（Closed / Filled / Cancelled / Rejected）の場合は
        broker API を呼ばずに InvalidStateTransitionError を raise する。
        それ以外の場合は broker API の cancel_order を呼び、Cancelled に遷移する。
        """
        record = self._repo.get(client_order_id)
        if record is None:
            raise RuntimeError(f"注文が見つかりません: {client_order_id}")

        if record.state in _TERMINAL_STATES:
            raise InvalidStateTransitionError(
                f"終端状態 ({record.state.value}) の注文はキャンセルできません"
            )

        if record.broker_order_id:
            self._broker.cancel_order(record.broker_order_id)

        record.transition_to(OrderState.Cancelled)
        self._repo.update(record)
        return record
```

- [ ] **Step 4: Group 3 テストがすべて通ることを確認する**

```
pytest tests/test_order_state_machine.py -k "test_create or test_send or test_sync or test_cancel" -v
```

Expected: 11 passed

- [ ] **Step 5: テストスイート全体を実行して回帰確認**

```
pytest tests/test_order_state_machine.py -v
```

Expected: 28 passed (Group 1: 9 + Group 2: 8 + Group 3: 11)

- [ ] **Step 6: コミット**

```bash
git add src/kabusys/execution/order_manager.py tests/test_order_state_machine.py
git commit -m "feat: add OrderManager with crash-safe send_order and sync_order (Issue #29)"
```

---

## Task 4: `__init__.py` エクスポート更新 + 既存テスト確認

**Files:**
- Modify: `src/kabusys/execution/__init__.py`

### ステップ

- [ ] **Step 1: 現在の `__init__.py` を確認する**

```
cat src/kabusys/execution/__init__.py
```

- [ ] **Step 2: 新しいクラスと例外をエクスポートに追加する**

`__init__.py` の末尾（または `__all__` リスト）に以下を追記する:

```python
from kabusys.execution.order_record import InvalidStateTransitionError, OrderRecord, OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.order_manager import DuplicateOrderError, OrderManager
```

`__all__` が定義されている場合は以下を追記する:

```python
    "InvalidStateTransitionError",
    "OrderRecord",
    "OrderState",
    "OrderRepository",
    "init_orders_db",
    "DuplicateOrderError",
    "OrderManager",
```

- [ ] **Step 3: `__init__.py` 経由でインポートできることを確認する**

```
python -c "from kabusys.execution import OrderManager, OrderRecord, OrderState, OrderRepository, DuplicateOrderError, InvalidStateTransitionError, init_orders_db; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: 既存テスト（broker API）への回帰確認**

```
pytest tests/test_broker_api.py tests/test_order_state_machine.py -v
```

Expected: 31 + 28 = 59 passed, 0 failed

- [ ] **Step 5: コミット**

```bash
git add src/kabusys/execution/__init__.py
git commit -m "feat: export OrderManager, OrderRecord, OrderRepository from execution package (Issue #29)"
```

---

## 完了確認

```
pytest tests/ -v
```

全テストが通ることを確認する。Issue #29 をクローズする。
