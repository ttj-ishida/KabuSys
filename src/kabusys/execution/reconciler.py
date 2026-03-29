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
        try:
            broker_positions = self._broker.get_positions()
        except BrokerAPIError:
            logger.warning("get_positions() 失敗: ポジション照合をスキップします", exc_info=True)
            return

        # ブローカーポジション: {code: qty} — 同一コードの複数エントリは合算
        broker_map: dict[str, int] = {}
        for p in broker_positions:
            broker_map[p.code] = broker_map.get(p.code, 0) + p.qty

        # ローカル推定ポジション: Filled / PartialFill の注文から code ごとにネット集計
        # list_active() は Closed/Cancelled/Rejected を除く。Filled と PartialFill は含まれる。
        # ※ Closed 状態（ポジションクローズ済）は list_active() では取得できないため対象外。
        #   現フェーズでは Filled → Closed 遷移は未実装のため、Filled buy - Filled sell のネットが
        #   現在保有数量に相当する。将来 Closed 遷移を実装する際は再検討が必要。
        local_map: dict[str, int] = {}
        try:
            active_orders = self._repo.list_active()
        except Exception:
            logger.warning("list_active() 失敗: ポジション照合をスキップします", exc_info=True)
            return
        for record in active_orders:
            if record.state not in {OrderState.Filled, OrderState.PartialFill}:
                continue
            if record.side == "buy":
                local_map[record.code] = local_map.get(record.code, 0) + record.filled_qty
            elif record.side == "sell":
                local_map[record.code] = local_map.get(record.code, 0) - record.filled_qty

        # 差分照合
        for code in set(broker_map) | set(local_map):
            broker_qty = broker_map.get(code, 0)
            local_qty = local_map.get(code, 0)
            diff = broker_qty - local_qty
            if diff != 0:
                result.position_discrepancies.append(
                    PositionDiscrepancy(
                        code=code,
                        broker_qty=broker_qty,
                        local_qty=local_qty,
                        diff=diff,
                    )
                )
                logger.warning(
                    "ポジション差分検出: code=%s, broker=%d, local=%d, diff=%+d",
                    code, broker_qty, local_qty, diff,
                )
