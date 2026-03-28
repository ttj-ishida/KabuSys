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
        """get_by_signal は signal_id に紐づく全レコードを返す"""
        repo.save(_make_record(client_order_id="sig-test-001", signal_id="same-signal"))
        repo.save(_make_record(client_order_id="sig-test-002", signal_id="same-signal"))
        repo.save(_make_record(client_order_id="sig-test-003", signal_id="other-signal"))

        results = repo.get_by_signal("same-signal")
        assert len(results) == 2
        ids = {r.client_order_id for r in results}
        assert ids == {"sig-test-001", "sig-test-002"}

    def test_get_returns_none_for_missing(self, repo):
        """get は存在しない ID に対して None を返す"""
        assert repo.get("nonexistent") is None
