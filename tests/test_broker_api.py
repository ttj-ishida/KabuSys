"""BrokerAPI クライアント層のテスト。MockBrokerClient を使い kabu station 不要で実行可能。"""
from __future__ import annotations

from kabusys.execution.broker_api import (
    BrokerAPIError,
    BrokerAPIProtocol,
    OrderRejectedError,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    Position,
    RateLimitError,
    WalletInfo,
    create_broker_api,
)
from kabusys.execution.mock_client import MockBrokerClient


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
    """Position の qty と avg_price が正しく設定されること。"""
    pos = Position(code="1234", qty=100, avg_price=1500.0)
    assert pos.qty == 100
    assert pos.avg_price == 1500.0


def test_wallet_info_fields():
    """WalletInfo の available_cash が正しく設定されること。"""
    wallet = WalletInfo(available_cash=5_000_000.0)
    assert wallet.available_cash == 5_000_000.0


def test_order_response_fields():
    """OrderResponse の order_id が設定されること。"""
    resp = OrderResponse(order_id="ORD12345")
    assert resp.order_id == "ORD12345"


# ---------------------------------------------------------------------------
# 例外クラス
# ---------------------------------------------------------------------------

def test_broker_api_error_is_exception():
    err = BrokerAPIError("test error")
    assert isinstance(err, Exception)
    assert str(err) == "test error"


def test_broker_api_error_with_status_code():
    err = BrokerAPIError("rate limit", status_code=429)
    assert err.status_code == 429


def test_order_rejected_error_is_broker_api_error():
    err = OrderRejectedError("rejected")
    assert isinstance(err, BrokerAPIError)


def test_rate_limit_error_is_broker_api_error():
    err = RateLimitError("too many requests", status_code=429)
    assert isinstance(err, BrokerAPIError)
    assert err.status_code == 429


# ---------------------------------------------------------------------------
# ファクトリ
# ---------------------------------------------------------------------------

def test_create_broker_api_mock_returns_mock_client():
    from kabusys.execution.mock_client import MockBrokerClient
    api = create_broker_api(mock=True)
    assert isinstance(api, MockBrokerClient)


# ---------------------------------------------------------------------------
# MockBrokerClient — ハッピーパス（instant fill）
# ---------------------------------------------------------------------------

def test_mock_send_order_instant_fill():
    """instant モードでの発注：即約定し positions と cash が更新される。"""
    client = MockBrokerClient(fill_mode="instant", available_cash=1_000_000.0)
    req = OrderRequest(code="1234", qty=100, price=500.0, order_type="limit")

    resp = client.send_order(req)

    assert resp.order_id.startswith("MOCK")
    # 約定済み状態
    status = client.get_order_status(resp.order_id)
    assert status is not None
    assert status.status == "filled"
    assert status.filled_qty == 100
    assert status.code == "1234"
    assert status.side == "buy"
    # ポジション更新
    positions = client.get_positions()
    assert len(positions) == 1
    assert positions[0].code == "1234"
    assert positions[0].qty == 100
    assert positions[0].avg_price == 500.0
    # 現金減少
    cash = client.get_available_cash()
    assert cash == 1_000_000.0 - 100 * 500.0


def test_mock_send_order_market_order_instant_fill():
    """成行注文（price=0.0）は price=0.0 で約定記録される。"""
    client = MockBrokerClient(fill_mode="instant", available_cash=1_000_000.0)
    req = OrderRequest(code="5678", qty=50)  # market order

    resp = client.send_order(req)
    status = client.get_order_status(resp.order_id)

    assert status.status == "filled"
    assert status.price == 0.0  # 成行は価格 0.0 で記録


def test_mock_cancel_order_open():
    """open 状態の注文はキャンセルできる。"""
    client = MockBrokerClient(fill_mode="partial")
    req = OrderRequest(code="1234", qty=100, price=500.0, order_type="limit")
    resp = client.send_order(req)

    client.cancel_order(resp.order_id)

    status = client.get_order_status(resp.order_id)
    assert status.status == "cancelled"


def test_mock_get_order_status_not_found():
    """存在しない order_id は None を返す。"""
    client = MockBrokerClient()
    assert client.get_order_status("NONEXISTENT") is None


def test_mock_get_positions_initial():
    """initial_positions が反映される。"""
    initial = [Position(code="1234", qty=200, avg_price=600.0)]
    client = MockBrokerClient(initial_positions=initial)
    positions = client.get_positions()
    assert len(positions) == 1
    assert positions[0].code == "1234"
    assert positions[0].qty == 200


def test_mock_get_available_cash_decreases_after_buy():
    """buy 後に利用可能現金が減少する。"""
    client = MockBrokerClient(fill_mode="instant", available_cash=500_000.0)
    req = OrderRequest(code="3333", qty=10, price=1000.0, order_type="limit")
    client.send_order(req)
    assert client.get_available_cash() == 490_000.0


def test_mock_sell_order_increases_cash():
    """sell 後に利用可能現金が増加し、ポジションが減少する。"""
    initial = [Position(code="1234", qty=100, avg_price=500.0)]
    client = MockBrokerClient(
        fill_mode="instant",
        available_cash=0.0,
        initial_positions=initial,
    )
    req = OrderRequest(code="1234", side="sell", qty=50, price=600.0, order_type="limit")
    client.send_order(req)

    assert client.get_available_cash() == 50 * 600.0
    positions = client.get_positions()
    assert positions[0].qty == 50


# ---------------------------------------------------------------------------
# MockBrokerClient — 部分約定
# ---------------------------------------------------------------------------

def test_mock_fill_mode_partial():
    """partial モードでは発注数量の50%のみ約定し status=partial になる。"""
    client = MockBrokerClient(fill_mode="partial", available_cash=1_000_000.0)
    req = OrderRequest(code="1234", qty=100, price=500.0, order_type="limit")

    resp = client.send_order(req)
    status = client.get_order_status(resp.order_id)

    assert status.status == "partial"
    assert status.filled_qty == 50
    assert status.qty == 100
    # 部分約定分だけポジション・現金更新
    positions = client.get_positions()
    assert positions[0].qty == 50
    assert client.get_available_cash() == 1_000_000.0 - 50 * 500.0


def test_mock_fill_order_manual():
    """fill_order() で partial 注文を全量約定させられる。"""
    client = MockBrokerClient(fill_mode="partial", available_cash=1_000_000.0)
    req = OrderRequest(code="1234", qty=100, price=500.0, order_type="limit")
    resp = client.send_order(req)

    client.fill_order(resp.order_id)

    status = client.get_order_status(resp.order_id)
    assert status.status == "filled"
    assert status.filled_qty == 100
    # 残り50株分もポジション更新
    positions = client.get_positions()
    assert positions[0].qty == 100
    # 残り50株分の現金も減少
    assert client.get_available_cash() == 1_000_000.0 - 100 * 500.0


# ---------------------------------------------------------------------------
# MockBrokerClient — 異常系
# ---------------------------------------------------------------------------

def test_mock_fill_mode_reject():
    """reject モードでは OrderRejectedError が raise される。"""
    client = MockBrokerClient(fill_mode="reject")
    req = OrderRequest(code="1234", qty=100)

    import pytest
    with pytest.raises(OrderRejectedError):
        client.send_order(req)


def test_mock_cancel_unknown_order_raises():
    """存在しない order_id のキャンセルは BrokerAPIError を raise する。"""
    client = MockBrokerClient()

    import pytest
    with pytest.raises(BrokerAPIError):
        client.cancel_order("UNKNOWN9999")


def test_mock_cancel_filled_order_raises():
    """約定済み注文のキャンセルは BrokerAPIError を raise する。"""
    client = MockBrokerClient(fill_mode="instant", available_cash=1_000_000.0)
    req = OrderRequest(code="1234", qty=100, price=500.0, order_type="limit")
    resp = client.send_order(req)

    import pytest
    with pytest.raises(BrokerAPIError):
        client.cancel_order(resp.order_id)


def test_mock_cancel_partial_order():
    """partial 状態の注文はキャンセルできる。"""
    client = MockBrokerClient(fill_mode="partial")
    req = OrderRequest(code="1234", qty=100, price=500.0, order_type="limit")
    resp = client.send_order(req)

    client.cancel_order(resp.order_id)

    status = client.get_order_status(resp.order_id)
    assert status.status == "cancelled"


# ---------------------------------------------------------------------------
# テスト補助メソッド
# ---------------------------------------------------------------------------

def test_mock_get_order_history():
    """get_order_history() は送信された全注文の履歴を返す。"""
    client = MockBrokerClient(fill_mode="instant", available_cash=5_000_000.0)
    req1 = OrderRequest(code="1111", qty=100, price=500.0, order_type="limit")
    req2 = OrderRequest(code="2222", qty=200, price=300.0, order_type="limit")

    resp1 = client.send_order(req1)
    resp2 = client.send_order(req2)

    history = client.get_order_history()
    assert len(history) == 2
    order_ids = {s.order_id for s in history}
    assert resp1.order_id in order_ids
    assert resp2.order_id in order_ids


def test_mock_sell_without_position_does_not_credit_cash():
    """ポジションのない銘柄の売注文は現金残高を変化させない。"""
    client = MockBrokerClient(fill_mode="instant", available_cash=500_000.0)
    req = OrderRequest(code="9999", side="sell", qty=10, price=1000.0, order_type="limit")
    client.send_order(req)
    assert client.get_available_cash() == 500_000.0  # unchanged
