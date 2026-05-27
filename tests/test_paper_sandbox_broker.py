# tests/test_paper_sandbox_broker.py
"""PaperSandboxBroker のユニットテスト。"""

from unittest.mock import MagicMock

import pytest

from kabusys.execution.broker_api import (
    OrderRequest,
    OrderResponse,
    OrderStatus,
    Position,
)
from kabusys.execution.paper_sandbox_broker import PaperSandboxBroker


@pytest.fixture
def real_broker():
    mock = MagicMock()
    mock.send_order.return_value = OrderResponse(order_id="SB001")
    mock.get_order_status.return_value = OrderStatus(
        order_id="SB001",
        code="7203",
        side="buy",
        qty=100,
        filled_qty=100,
        status="filled",
        price=2000.0,
    )
    mock.get_positions.return_value = [Position(code="7203", qty=100, avg_price=2000.0)]
    return mock


class TestPaperSandboxBrokerCash:
    def test_get_available_cash_returns_paper_cash(self, real_broker):
        broker = PaperSandboxBroker(real_broker=real_broker, paper_cash=5_000_000.0)
        assert broker.get_available_cash() == 5_000_000.0

    def test_get_available_cash_ignores_real_broker(self, real_broker):
        real_broker.get_available_cash.return_value = 0.0
        broker = PaperSandboxBroker(real_broker=real_broker, paper_cash=10_000_000.0)
        assert broker.get_available_cash() == 10_000_000.0
        real_broker.get_available_cash.assert_not_called()


class TestPaperSandboxBrokerDelegation:
    def test_send_order_delegates_to_real(self, real_broker):
        broker = PaperSandboxBroker(real_broker=real_broker, paper_cash=10_000_000.0)
        req = OrderRequest(code="7203", side="buy", qty=100, price=2000.0)
        resp = broker.send_order(req)
        assert resp.order_id == "SB001"
        real_broker.send_order.assert_called_once_with(req)

    def test_cancel_order_delegates_to_real(self, real_broker):
        broker = PaperSandboxBroker(real_broker=real_broker, paper_cash=10_000_000.0)
        broker.cancel_order("SB001")
        real_broker.cancel_order.assert_called_once_with("SB001")

    def test_get_order_status_delegates_to_real(self, real_broker):
        broker = PaperSandboxBroker(real_broker=real_broker, paper_cash=10_000_000.0)
        status = broker.get_order_status("SB001")
        assert status is not None
        assert status.order_id == "SB001"
        real_broker.get_order_status.assert_called_once_with("SB001")

    def test_get_positions_delegates_to_real(self, real_broker):
        broker = PaperSandboxBroker(real_broker=real_broker, paper_cash=10_000_000.0)
        positions = broker.get_positions()
        assert len(positions) == 1
        assert positions[0].code == "7203"
        real_broker.get_positions.assert_called_once()


class TestPaperSandboxBrokerProtocol:
    def test_implements_broker_protocol(self, real_broker):
        from kabusys.execution.broker_api import BrokerAPIProtocol

        broker = PaperSandboxBroker(real_broker=real_broker, paper_cash=10_000_000.0)
        assert isinstance(broker, BrokerAPIProtocol)
