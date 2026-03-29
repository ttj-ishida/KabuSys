"""Reconciler — 起動時自動復旧・リコンシリエーション。

再起動・クラッシュ後に OrderSent 状態の注文をブローカーと突合して自動同期し、
ポジション差分をログに記録して安全に処理を再開する。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from kabusys.execution.broker_api import BrokerAPIError, BrokerAPIProtocol
from kabusys.execution.order_manager import OrderManager
from kabusys.execution.order_record import OrderState
from kabusys.execution.order_repository import OrderRepository

logger = logging.getLogger(__name__)


@dataclass
class PositionDiscrepancy:
    code: str
    broker_qty: int   # ブローカー側の保有数量
    local_qty: int    # ローカルDB推定値（注文履歴から集計）
    diff: int         # broker_qty - local_qty


@dataclass
class ReconcileResult:
    orders_synced: int = 0
    orders_no_status: int = 0
    position_discrepancies: list[PositionDiscrepancy] = field(default_factory=list)


class Reconciler:
    def __init__(
        self,
        broker: BrokerAPIProtocol,
        repo: OrderRepository,
        order_manager: OrderManager,
    ) -> None:
        self._broker = broker
        self._repo = repo
        self._order_manager = order_manager

    def run(self) -> ReconcileResult:
        """Step 1: OrderSent 照合 → Step 2: ポジション差分照合"""
        result = ReconcileResult()
        self._reconcile_orders(result)
        self._reconcile_positions(result)
        return result

    def _reconcile_orders(self, result: ReconcileResult) -> None:
        pass  # Task 2 で実装

    def _reconcile_positions(self, result: ReconcileResult) -> None:
        pass  # Task 3 で実装
