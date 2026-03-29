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
        from kabusys.execution.broker_api import OrderStatus, BrokerAPIError
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
