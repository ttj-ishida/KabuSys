"""BrokerAPI クライアント層のテスト。MockBrokerClient を使い kabu station 不要で実行可能。"""
from __future__ import annotations

from kabusys.execution.broker_api import (
    OrderRequest,
    OrderResponse,
    OrderStatus,
    Position,
    WalletInfo,
)


def test_order_request_defaults():
    """OrderRequest のデフォルト値がスペック通りであること。"""
    req = OrderRequest(code="1234", qty=100)
    assert req.exchange == 1
    assert req.side == "buy"
    assert req.price == 0.0
    assert req.order_type == "market"
    assert req.account_type == 4


def test_order_request_fields():
    """全フィールドを指定できること。"""
    req = OrderRequest(
        code="9999",
        exchange=3,
        side="sell",
        qty=200,
        price=1500.0,
        order_type="limit",
        account_type=2,
    )
    assert req.code == "9999"
    assert req.exchange == 3
    assert req.side == "sell"
    assert req.qty == 200
    assert req.price == 1500.0
    assert req.order_type == "limit"
    assert req.account_type == 2


def test_order_status_fields():
    """OrderStatus の全フィールドが設定できること。"""
    status = OrderStatus(
        order_id="ORD001",
        code="1234",
        side="buy",
        qty=100,
        filled_qty=0,
        status="open",
        price=None,
    )
    assert status.order_id == "ORD001"
    assert status.price is None


def test_position_fields():
    pos = Position(code="1234", qty=100, avg_price=1500.0)
    assert pos.qty == 100
    assert pos.avg_price == 1500.0


def test_wallet_info_fields():
    wallet = WalletInfo(available_cash=5_000_000.0)
    assert wallet.available_cash == 5_000_000.0
