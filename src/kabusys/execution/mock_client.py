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
        if self.fill_mode == "reject":
            raise OrderRejectedError(f"発注拒否（fill_mode=reject）: {order.code}")

        order_id = self._next_order_id()

        if self.fill_mode == "instant":
            filled_qty = order.qty
            status_str = "filled"
        else:  # partial
            filled_qty = order.qty // 2
            status_str = "partial" if filled_qty < order.qty else "filled"

        price = order.price if order.order_type == "limit" else 0.0

        self._orders[order_id] = OrderStatus(
            order_id=order_id,
            code=order.code,
            side=order.side,
            qty=order.qty,
            filled_qty=filled_qty,
            status=status_str,
            price=price if filled_qty > 0 else None,
        )

        if filled_qty > 0:
            self._apply_fill(order.code, order.side, filled_qty, price)

        return OrderResponse(order_id=order_id)

    def _apply_fill(self, code: str, side: str, qty: int, price: float) -> None:
        """約定分のポジションと現金を更新する。"""
        if side == "buy":
            if code in self._positions:
                pos = self._positions[code]
                total_qty = pos.qty + qty
                total_cost = pos.qty * pos.avg_price + qty * price
                self._positions[code] = Position(
                    code=code,
                    qty=total_qty,
                    avg_price=total_cost / total_qty if total_qty > 0 else 0.0,
                )
            else:
                self._positions[code] = Position(code=code, qty=qty, avg_price=price)
            self._cash -= qty * price
        else:  # sell
            if code in self._positions:
                pos = self._positions[code]
                new_qty = pos.qty - qty
                if new_qty <= 0:
                    del self._positions[code]
                else:
                    self._positions[code] = Position(
                        code=code, qty=new_qty, avg_price=pos.avg_price
                    )
                self._cash += qty * price

    def cancel_order(self, order_id: str) -> None:
        if order_id not in self._orders:
            raise BrokerAPIError(f"注文が見つかりません: {order_id}")
        status = self._orders[order_id]
        if status.status == "filled":
            raise BrokerAPIError(f"約定済み注文はキャンセルできません: {order_id}")
        self._orders[order_id] = OrderStatus(
            order_id=order_id,
            code=status.code,
            side=status.side,
            qty=status.qty,
            filled_qty=status.filled_qty,
            status="cancelled",
            price=status.price,
        )

    def get_order_status(self, order_id: str) -> OrderStatus | None:
        return self._orders.get(order_id)

    def get_positions(self) -> list[Position]:
        return list(self._positions.values())

    def get_available_cash(self) -> float:
        return self._cash
