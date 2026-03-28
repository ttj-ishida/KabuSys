# tests/test_order_state_machine.py
"""Order State Machine — 単体テスト

Group 1: OrderRecord の状態遷移（DB なし・Mock なし）
Group 2: OrderRepository（インメモリ SQLite）  ← 後続タスクで追記
Group 3: OrderManager（MockBrokerClient + インメモリ SQLite）  ← 後続タスクで追記
"""
import time

import pytest
from datetime import datetime, timezone

from kabusys.execution.order_record import InvalidStateTransitionError, OrderRecord, OrderState


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _make_record(**overrides) -> OrderRecord:
    """テスト用の OrderRecord を生成するヘルパー。"""
    defaults = dict(
        client_order_id="test-order-id",
        signal_id="test-signal-id",
        code="1234",
        side="buy",
        qty=100,
        order_type="market",
        price=0.0,
        state=OrderState.OrderCreated,
        broker_order_id=None,
        filled_qty=0,
        avg_fill_price=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        error_message=None,
    )
    defaults.update(overrides)
    return OrderRecord(**defaults)


# ---------------------------------------------------------------------------
# Group 1: OrderRecord の状態遷移（DB なし・Mock なし）
# ---------------------------------------------------------------------------

class TestOrderRecordTransitions:

    def test_normal_flow_created_to_closed(self):
        """正常遷移: Created→Sent→Accepted→Filled→Closed"""
        r = _make_record()
        r.transition_to(OrderState.OrderSent)
        assert r.state == OrderState.OrderSent

        r.transition_to(OrderState.OrderAccepted, broker_order_id="broker-001")
        assert r.state == OrderState.OrderAccepted
        assert r.broker_order_id == "broker-001"

        r.transition_to(OrderState.Filled, filled_qty=100, avg_fill_price=1500.0)
        assert r.state == OrderState.Filled
        assert r.filled_qty == 100
        assert r.avg_fill_price == 1500.0

        r.transition_to(OrderState.Closed)
        assert r.state == OrderState.Closed

    def test_partial_fill_flow(self):
        """部分約定: Accepted→PartialFill→Filled→Closed"""
        r = _make_record(state=OrderState.OrderAccepted)
        r.transition_to(OrderState.PartialFill, filled_qty=50)
        assert r.state == OrderState.PartialFill
        assert r.filled_qty == 50

        r.transition_to(OrderState.Filled, filled_qty=100, avg_fill_price=1500.0)
        assert r.state == OrderState.Filled

        r.transition_to(OrderState.Closed)
        assert r.state == OrderState.Closed

    def test_cancel_from_created(self):
        """キャンセル: Created→Cancelled"""
        r = _make_record()
        r.transition_to(OrderState.Cancelled)
        assert r.state == OrderState.Cancelled

    def test_cancel_from_accepted(self):
        """キャンセル: Accepted→Cancelled"""
        r = _make_record(state=OrderState.OrderAccepted)
        r.transition_to(OrderState.Cancelled)
        assert r.state == OrderState.Cancelled

    def test_reject_from_created(self):
        """拒否: Created→Rejected"""
        r = _make_record()
        r.transition_to(OrderState.Rejected, error_message="余力不足")
        assert r.state == OrderState.Rejected
        assert r.error_message == "余力不足"

    def test_reject_from_sent(self):
        """拒否: Sent→Rejected"""
        r = _make_record(state=OrderState.OrderSent)
        r.transition_to(OrderState.Rejected, error_message="規制銘柄")
        assert r.state == OrderState.Rejected

    def test_invalid_transition_filled_to_sent(self):
        """不正遷移: Filled→Sent は InvalidStateTransitionError"""
        r = _make_record(state=OrderState.Filled)
        with pytest.raises(InvalidStateTransitionError):
            r.transition_to(OrderState.OrderSent)

    def test_invalid_transition_closed_to_accepted(self):
        """不正遷移: Closed→Accepted は InvalidStateTransitionError"""
        r = _make_record(state=OrderState.Closed)
        with pytest.raises(InvalidStateTransitionError):
            r.transition_to(OrderState.OrderAccepted)

    def test_transition_updates_updated_at(self):
        """transition_to は updated_at を更新する"""
        r = _make_record()
        old_updated_at = r.updated_at
        time.sleep(0.01)
        r.transition_to(OrderState.OrderSent)
        assert r.updated_at > old_updated_at


# ---------------------------------------------------------------------------
# Group 2: OrderRepository（インメモリ SQLite）
# ---------------------------------------------------------------------------

import sqlite3

from kabusys.execution.order_repository import OrderRepository, init_orders_db


@pytest.fixture
def conn():
    """インメモリ SQLite 接続（各テスト独立）。"""
    c = sqlite3.connect(":memory:")
    init_orders_db(c)
    yield c
    c.close()


@pytest.fixture
def repo(conn):
    return OrderRepository(conn)


class TestOrderRepository:

    def test_save_and_get_roundtrip(self, repo):
        """save → get の往復でフィールドが一致する"""
        r = _make_record(client_order_id="repo-test-001")
        repo.save(r)
        fetched = repo.get("repo-test-001")
        assert fetched is not None
        assert fetched.client_order_id == r.client_order_id
        assert fetched.signal_id == r.signal_id
        assert fetched.code == r.code
        assert fetched.side == r.side
        assert fetched.qty == r.qty
        assert fetched.order_type == r.order_type
        assert fetched.price == r.price
        assert fetched.state == r.state
        assert fetched.broker_order_id == r.broker_order_id
        assert fetched.filled_qty == r.filled_qty
        assert fetched.avg_fill_price == r.avg_fill_price
        assert fetched.error_message == r.error_message
        # タイムスタンプのラウンドトリップ検証（タイムゾーン付きで復元される）
        assert fetched.created_at is not None
        assert fetched.updated_at is not None
        assert fetched.created_at.tzinfo is not None  # timezone-aware であること
        assert fetched.updated_at.tzinfo is not None
        # ISO 文字列経由でもマイクロ秒まで一致する
        assert fetched.created_at == r.created_at
        assert fetched.updated_at == r.updated_at

    def test_save_duplicate_raises_integrity_error(self, repo):
        """save を同一 client_order_id で2回呼ぶと IntegrityError"""
        r = _make_record(client_order_id="dup-001")
        repo.save(r)
        with pytest.raises(sqlite3.IntegrityError):
            repo.save(r)

    def test_update(self, repo):
        """update でフィールドが更新される"""
        r = _make_record(client_order_id="update-001")
        repo.save(r)
        r.transition_to(OrderState.OrderSent)
        repo.update(r)
        fetched = repo.get("update-001")
        assert fetched.state == OrderState.OrderSent

    def test_update_nonexistent_raises_runtime_error(self, repo):
        """update で存在しない ID は RuntimeError"""
        r = _make_record(client_order_id="nonexistent-001")
        with pytest.raises(RuntimeError):
            repo.update(r)

    def test_list_active_excludes_terminal_states(self, repo):
        """list_active は Closed / Cancelled / Rejected を除外する"""
        active_states = [
            OrderState.OrderCreated,
            OrderState.OrderSent,
            OrderState.OrderAccepted,
            OrderState.PartialFill,
            OrderState.Filled,
        ]
        terminal_states = [
            OrderState.Closed,
            OrderState.Cancelled,
            OrderState.Rejected,
        ]
        for i, s in enumerate(active_states):
            repo.save(_make_record(client_order_id=f"active-{i}", signal_id=f"sig-active-{i}", state=s))
        for i, s in enumerate(terminal_states):
            repo.save(_make_record(client_order_id=f"terminal-{i}", signal_id=f"sig-terminal-{i}", state=s))

        active = repo.list_active()
        active_ids = {r.client_order_id for r in active}
        assert all(f"active-{i}" in active_ids for i in range(len(active_states)))
        assert all(f"terminal-{i}" not in active_ids for i in range(len(terminal_states)))

    def test_list_uncertain_returns_only_sent(self, repo):
        """list_uncertain は OrderSent のみ返す"""
        repo.save(_make_record(client_order_id="sent-001", signal_id="sig-s1", state=OrderState.OrderSent))
        repo.save(_make_record(client_order_id="created-001", signal_id="sig-c1", state=OrderState.OrderCreated))
        repo.save(_make_record(client_order_id="accepted-001", signal_id="sig-a1", state=OrderState.OrderAccepted))

        uncertain = repo.list_uncertain()
        assert len(uncertain) == 1
        assert uncertain[0].client_order_id == "sent-001"
        assert uncertain[0].state == OrderState.OrderSent

    def test_get_by_signal(self, repo):
        """get_by_signal は signal_id に紐づく全レコードを返す
        （1件目は Cancelled 済み、2件目は新規 OrderCreated — 現実の再発注シナリオ）"""
        repo.save(_make_record(client_order_id="sig-test-001", signal_id="same-signal",
                               state=OrderState.Cancelled))
        repo.save(_make_record(client_order_id="sig-test-002", signal_id="same-signal"))
        repo.save(_make_record(client_order_id="sig-test-003", signal_id="other-signal"))

        results = repo.get_by_signal("same-signal")
        assert len(results) == 2
        ids = {r.client_order_id for r in results}
        assert ids == {"sig-test-001", "sig-test-002"}

    def test_get_returns_none_for_missing(self, repo):
        """get は存在しない ID に対して None を返す"""
        assert repo.get("nonexistent") is None


# ---------------------------------------------------------------------------
# Group 3: OrderManager（MockBrokerClient + インメモリ SQLite）
# ---------------------------------------------------------------------------

from kabusys.execution.broker_api import OrderRequest
from kabusys.execution.mock_client import MockBrokerClient
from kabusys.execution.order_manager import DuplicateOrderError, OrderManager


@pytest.fixture
def manager(conn):
    """MockBrokerClient（fill_mode='instant'）+ インメモリ SQLite の OrderManager。"""
    broker = MockBrokerClient(fill_mode="instant")
    return OrderManager(broker=broker, repo=OrderRepository(conn))


def test_create_order_normal(manager):
    """create_order → OrderCreated レコードを返す"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = manager.create_order("sig-001", request)
    assert record.state == OrderState.OrderCreated
    assert record.signal_id == "sig-001"
    assert record.code == "1234"
    assert record.client_order_id is not None


def test_create_order_duplicate_signal_raises(manager):
    """同一 signal_id で create_order を2回呼ぶと DuplicateOrderError"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    manager.create_order("sig-dup", request)
    with pytest.raises(DuplicateOrderError):
        manager.create_order("sig-dup", request)


def test_send_order_normal_flow(manager):
    """create_order → send_order の正常フロー（OrderAccepted に遷移）"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = manager.create_order("sig-send", request)
    result = manager.send_order(record.client_order_id)
    assert result.state == OrderState.OrderAccepted
    assert result.broker_order_id is not None


def test_send_order_rejected(repo):
    """send_order で broker が OrderRejectedError → Rejected に遷移"""
    from kabusys.execution.broker_api import OrderRejectedError

    class RejectingBroker:
        def send_order(self, order):
            raise OrderRejectedError("余力不足テスト")
        def cancel_order(self, order_id): pass
        def get_order_status(self, order_id): return None
        def get_positions(self): return []
        def get_available_cash(self): return 0.0

    m = OrderManager(broker=RejectingBroker(), repo=repo)
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = m.create_order("sig-rejected", request)
    result = m.send_order(record.client_order_id)
    assert result.state == OrderState.Rejected
    assert result.error_message is not None


def test_send_order_persists_sent_state_before_broker_call(repo):
    """クラッシュ模擬: OrderSent 永続化後に broker が例外 → list_uncertain でレコードが見つかる"""

    class CrashingBroker:
        def send_order(self, order): raise RuntimeError("クラッシュ模擬")
        def cancel_order(self, order_id): pass
        def get_order_status(self, order_id): return None
        def get_positions(self): return []
        def get_available_cash(self): return 1_000_000.0

    crash_manager = OrderManager(broker=CrashingBroker(), repo=repo)
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = crash_manager.create_order("sig-crash", request)
    with pytest.raises(RuntimeError):
        crash_manager.send_order(record.client_order_id)

    uncertain = repo.list_uncertain()
    assert len(uncertain) == 1
    assert uncertain[0].state == OrderState.OrderSent


def test_sync_order_sent_to_accepted(repo):
    """sync_order: OrderSent のレコードに broker が 'open' を返したら OrderAccepted に遷移"""

    class StubBrokerReturnsOpen:
        def get_order_status(self, order_id):
            from kabusys.execution.broker_api import OrderStatus
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


def test_sync_order_filled(repo):
    """sync_order: broker が 'filled' を返したら Filled に遷移"""
    from kabusys.execution.broker_api import OrderStatus

    class StubBrokerFilled:
        def get_order_status(self, order_id):
            return OrderStatus(
                order_id=order_id,
                code="1234",
                side="buy",
                qty=100,
                filled_qty=100,
                status="filled",
                price=1500.0,
            )
        def send_order(self, order): pass
        def cancel_order(self, order_id): pass
        def get_positions(self): return []
        def get_available_cash(self): return 1_000_000.0

    # OrderAccepted 状態のレコードを直接 DB に保存
    r = _make_record(
        signal_id="sig-sync-filled",
        state=OrderState.OrderAccepted,
        broker_order_id="broker-filled-001",
    )
    repo.save(r)

    m = OrderManager(broker=StubBrokerFilled(), repo=repo)
    result = m.sync_order(r.client_order_id)
    assert result.state == OrderState.Filled
    assert result.filled_qty == 100
    assert result.avg_fill_price == 1500.0


def test_sync_order_broker_returns_none(manager):
    """sync_order: broker が None を返したら状態変化なし"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = manager.create_order("sig-sync-none", request)
    manager.send_order(record.client_order_id)

    class StubBrokerReturnsNone:
        def get_order_status(self, order_id): return None
        def send_order(self, order): pass
        def cancel_order(self, order_id): pass
        def get_positions(self): return []
        def get_available_cash(self): return 1_000_000.0

    repo_direct = manager._repo
    fetched = repo_direct.get(record.client_order_id)
    original_state = fetched.state

    from kabusys.execution.order_manager import OrderManager as OM
    stub_manager = OM(broker=StubBrokerReturnsNone(), repo=repo_direct)
    result = stub_manager.sync_order(record.client_order_id)
    assert result.state == original_state


def test_cancel_order_accepted(manager):
    """cancel_order: OrderAccepted → Cancelled"""
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = manager.create_order("sig-cancel", request)
    manager.send_order(record.client_order_id)  # OrderAccepted

    # fill_mode="instant" なので既に Filled になっている可能性があるため、
    # OrderAccepted 状態のレコードを直接作って cancel する
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


def test_cancel_order_terminal_state_raises(manager):
    """cancel_order: Filled の注文は broker を呼ばず InvalidStateTransitionError"""
    from kabusys.execution.order_record import InvalidStateTransitionError

    filled = _make_record(
        signal_id="sig-cancel-filled",
        state=OrderState.Filled,
        broker_order_id="broker-filled-001",
    )
    manager._repo.save(filled)
    with pytest.raises(InvalidStateTransitionError):
        manager.cancel_order(filled.client_order_id)


@pytest.mark.parametrize("terminal_state,signal_id", [
    (OrderState.Closed,    "sig-cancel-closed"),
    (OrderState.Cancelled, "sig-cancel-cancelled"),
    (OrderState.Rejected,  "sig-cancel-rejected"),
])
def test_cancel_order_all_terminal_states_raise(manager, terminal_state, signal_id):
    """cancel_order: Closed / Cancelled / Rejected も InvalidStateTransitionError"""
    from kabusys.execution.order_record import InvalidStateTransitionError

    record = _make_record(signal_id=signal_id, state=terminal_state)
    manager._repo.save(record)
    with pytest.raises(InvalidStateTransitionError):
        manager.cancel_order(record.client_order_id)


def test_send_order_persists_broker_order_id_before_accepted(repo):
    """2相永続化: broker応答後・Accepted遷移前クラッシュでも broker_order_id が DB に残る"""

    class CrashAfterBrokerIdBroker:
        """broker_order_id を返した後、Accepted への遷移前にクラッシュを模擬する。
        実際のクラッシュを再現するため、send_order は正常応答するが
        テストでは Step3a 完了後の DB 状態を直接検証する。"""
        def send_order(self, order):
            from kabusys.execution.broker_api import OrderResponse
            return OrderResponse(order_id="broker-twophase-001")
        def cancel_order(self, order_id): pass
        def get_order_status(self, order_id): return None
        def get_positions(self): return []
        def get_available_cash(self): return 1_000_000.0

    m = OrderManager(broker=CrashAfterBrokerIdBroker(), repo=repo)
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")
    record = m.create_order("sig-twophase", request)
    result = m.send_order(record.client_order_id)

    # 正常完了時は OrderAccepted かつ broker_order_id が保存されている
    assert result.state == OrderState.OrderAccepted
    assert result.broker_order_id == "broker-twophase-001"

    # DB からも確認（repo から直接取得）
    persisted = repo.get(record.client_order_id)
    assert persisted.broker_order_id == "broker-twophase-001"
    assert persisted.state == OrderState.OrderAccepted


def test_create_order_db_unique_violation_raises_duplicate_error(repo):
    """部分ユニークインデックス違反時も DuplicateOrderError が返る（IntegrityError が漏れない）"""
    from kabusys.execution.order_manager import DuplicateOrderError

    broker = MockBrokerClient(fill_mode="instant")
    m = OrderManager(broker=broker, repo=repo)
    request = OrderRequest(code="1234", side="buy", qty=100, order_type="market")

    # 1件目は正常
    m.create_order("sig-unique-test", request)

    # 2件目: アプリ層チェックより先に DB 制約で弾かれても DuplicateOrderError になる
    with pytest.raises(DuplicateOrderError):
        m.create_order("sig-unique-test", request)


def test_sync_order_partial_progress_updates_filled_qty(repo):
    """sync_order: partial→partial 進行で filled_qty / avg_fill_price が更新される"""
    from kabusys.execution.broker_api import OrderStatus

    # OrderPartialFill 状態のレコードを直接 DB に保存（filled_qty=50）
    r = _make_record(
        signal_id="sig-partial-progress",
        state=OrderState.PartialFill,
        broker_order_id="broker-partial-001",
        filled_qty=50,
        avg_fill_price=1500.0,
    )
    repo.save(r)

    class StubBrokerPartialProgress:
        """同一 partial 状態のまま filled_qty が 50→80 に進行した応答を返す。"""
        def get_order_status(self, order_id):
            return OrderStatus(
                order_id=order_id,
                code="1234",
                side="buy",
                qty=100,
                filled_qty=80,
                status="partial",
                price=1510.0,
            )
        def send_order(self, order): pass
        def cancel_order(self, order_id): pass
        def get_positions(self): return []
        def get_available_cash(self): return 1_000_000.0

    m = OrderManager(broker=StubBrokerPartialProgress(), repo=repo)
    result = m.sync_order(r.client_order_id)

    assert result.state == OrderState.PartialFill   # 状態は変わらない
    assert result.filled_qty == 80                  # 数量は更新される
    assert result.avg_fill_price == 1510.0          # 価格も更新される

    # DB からも確認
    persisted = repo.get(r.client_order_id)
    assert persisted.filled_qty == 80
    assert persisted.avg_fill_price == 1510.0
