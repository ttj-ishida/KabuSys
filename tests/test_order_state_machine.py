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
