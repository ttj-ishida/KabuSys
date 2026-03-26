"""MockBrokerClient — テスト・開発用モック実装。"""
from __future__ import annotations

from kabusys.execution.broker_api import (
    BrokerAPIError,
    OrderRejectedError,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    Position,
)


class MockBrokerClient:
    """kabuステーション不要でテスト可能なモック実装。"""

    def __init__(
        self,
        fill_mode: str = "instant",
        available_cash: float = 10_000_000.0,
        initial_positions: list[Position] | None = None,
    ) -> None:
        self.fill_mode = fill_mode
        self._cash = available_cash
        self._orders: dict[str, OrderStatus] = {}
        self._positions: dict[str, Position] = {
            p.code: p for p in (initial_positions or [])
        }
        self._order_counter = 0

    def _next_order_id(self) -> str:
        self._order_counter += 1
        return f"MOCK{self._order_counter:04d}"

    def send_order(self, order: OrderRequest) -> OrderResponse:
        raise NotImplementedError

    def cancel_order(self, order_id: str) -> None:
        raise NotImplementedError

    def get_order_status(self, order_id: str) -> OrderStatus | None:
        raise NotImplementedError

    def get_positions(self) -> list[Position]:
        raise NotImplementedError

    def get_available_cash(self) -> float:
        raise NotImplementedError
