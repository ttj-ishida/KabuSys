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
