# src/kabusys/execution/paper_sandbox_broker.py
"""paper_sandbox_broker.py — Sandbox + Paper Trading ハイブリッドクライアント。"""

from __future__ import annotations

from kabusys.execution.broker_api import (
    BrokerAPIProtocol,
    OrderRequest,
    OrderResponse,
    OrderStatus,
    Position,
)


class PaperSandboxBroker:
    """kabuステーション検証環境への API 接続を維持しつつ、
    資金残高はペーパートレード用の仮想値を使うラッパー。

    - send_order / cancel_order / get_order_status / get_positions → 検証環境 API に委譲
    - get_available_cash → paper_trading.db 復元値 or PAPER_TRADING_INITIAL_CASH を返す
    - close → 検証環境 API クライアントのリソース解放を委譲

    kabuステーション検証環境の /wallet/cash は常に 0 を返すため（Issue #317）、
    get_available_cash() だけ paper_cash を返すことで RiskManager の余力チェックを正常化する。

    paper_cash は起動時の復元値または PAPER_TRADING_INITIAL_CASH で固定される。
    実行中の約定による動的更新は行わない（Paper Trading の検証用途として許容）。
    動的更新が必要になった場合は別途 setter を追加すること（現状は未実装）。
    """

    def __init__(self, real_broker: BrokerAPIProtocol, paper_cash: float) -> None:
        self._real = real_broker
        self._paper_cash = paper_cash

    def send_order(self, order: OrderRequest) -> OrderResponse:
        return self._real.send_order(order)

    def cancel_order(self, order_id: str) -> None:
        self._real.cancel_order(order_id)

    def get_order_status(self, order_id: str) -> OrderStatus | None:
        return self._real.get_order_status(order_id)

    def get_positions(self) -> list[Position]:
        return self._real.get_positions()

    def get_available_cash(self) -> float:
        return self._paper_cash

    def close(self) -> None:
        """検証環境 API クライアント（KabuStationClient）のリソースを解放する。"""
        self._real.close()

    def __getattr__(self, name: str) -> object:
        """BrokerAPIProtocol に将来メソッドが追加された場合のフォールバック委譲。"""
        return getattr(self._real, name)
