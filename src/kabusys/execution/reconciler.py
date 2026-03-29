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
        try:
            uncertain = self._repo.list_uncertain()
        except Exception:
            logger.error("list_uncertain() 失敗: リコンシリエーションをスキップします", exc_info=True)
            return

        for record in uncertain:
            if record.broker_order_id is None:
                result.orders_no_status += 1
                logger.warning(
                    "broker_order_id 未設定（手動確認要）: client_order_id=%s",
                    record.client_order_id,
                )
                continue
            try:
                updated = self._order_manager.sync_order(record.client_order_id)
                if updated.state == record.state:
                    if updated.state == OrderState.OrderSent:
                        # broker が None を返した（注文レコードなし）
                        result.orders_no_status += 1
                        logger.warning(
                            "broker に注文なし（手動確認要）: client_order_id=%s, broker_order_id=%s",
                            record.client_order_id, record.broker_order_id,
                        )
                else:
                    result.orders_synced += 1
                    logger.info(
                        "注文状態同期: %s → %s (client_order_id=%s)",
                        record.state.value, updated.state.value, record.client_order_id,
                    )
            except BrokerAPIError:
                logger.error(
                    "sync_order 失敗（スキップ）: client_order_id=%s",
                    record.client_order_id, exc_info=True,
                )

    def _reconcile_positions(self, result: ReconcileResult) -> None:
        pass  # Task 3 で実装
