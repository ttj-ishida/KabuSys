"""kabu station API クライアント層。

主要エクスポート:
    create_broker_api()  — 環境に応じたクライアントを返すファクトリ
    BrokerAPIProtocol    — 型アノテーション用 Protocol
    OrderRequest, OrderResponse, OrderStatus, Position, WalletInfo — データモデル
    BrokerAPIError, OrderRejectedError, RateLimitError — 例外クラス
    OrderState, OrderRecord, InvalidStateTransitionError — 注文状態管理
    OrderRepository, init_orders_db — 注文永続化
    OrderManager, DuplicateOrderError — 注文管理
"""
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
from kabusys.execution.order_record import InvalidStateTransitionError, OrderRecord, OrderState
from kabusys.execution.order_repository import OrderRepository, init_orders_db
from kabusys.execution.order_manager import DuplicateOrderError, OrderManager

__all__ = [
    "BrokerAPIError",
    "BrokerAPIProtocol",
    "OrderRejectedError",
    "OrderRequest",
    "OrderResponse",
    "OrderStatus",
    "Position",
    "RateLimitError",
    "WalletInfo",
    "create_broker_api",
    "InvalidStateTransitionError",
    "OrderRecord",
    "OrderState",
    "OrderRepository",
    "init_orders_db",
    "DuplicateOrderError",
    "OrderManager",
]
