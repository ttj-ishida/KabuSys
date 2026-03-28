# src/kabusys/execution/order_record.py
"""OrderRecord — Order State Machine のデータモデルと状態遷移ロジック。

DB には一切触れない。純粋なビジネスロジックのみ。
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class OrderState(str, enum.Enum):
    OrderCreated  = "created"    # 内部キューに登録済み、まだ送信前
    OrderSent     = "sent"       # broker API に送信済み、応答待ち（クラッシュ時に不明状態になりうる）
    OrderAccepted = "accepted"   # 証券会社受付済み、市場待機中
    PartialFill   = "partial"    # 一部約定済み
    Filled        = "filled"     # 全量約定済み
    Closed        = "closed"     # ポジション確定済み（Filled 後処理完了）
    Cancelled     = "cancelled"  # 取消済み
    Rejected      = "rejected"   # 証券会社拒否 or リスク統制拒否


_ALLOWED_TRANSITIONS: dict[OrderState, set[OrderState]] = {
    OrderState.OrderCreated:  {OrderState.OrderSent, OrderState.Rejected, OrderState.Cancelled},
    OrderState.OrderSent:     {OrderState.OrderAccepted, OrderState.Rejected, OrderState.Cancelled},
    OrderState.OrderAccepted: {OrderState.PartialFill, OrderState.Filled, OrderState.Cancelled, OrderState.Rejected},
    OrderState.PartialFill:   {OrderState.Filled, OrderState.Cancelled},
    OrderState.Filled:        {OrderState.Closed},
    OrderState.Closed:        set(),
    OrderState.Cancelled:     set(),
    OrderState.Rejected:      set(),
}


class InvalidStateTransitionError(Exception):
    """不正な状態遷移を試みた場合に raise される。"""


@dataclass
class OrderRecord:
    client_order_id: str          # UUID（冪等キー）
    signal_id: str                # signal_queue の signal_id
    code: str                     # 銘柄コード
    side: str                     # "buy" | "sell"
    qty: int                      # 発注数量
    order_type: str               # "market" | "limit"
    price: float                  # 指値価格（成行は 0.0）
    state: OrderState             # 現在の状態
    created_at: datetime          # UTC
    updated_at: datetime          # UTC
    broker_order_id: str | None = None    # 証券会社から受領した注文ID
    filled_qty: int = 0                   # 約定済み数量
    avg_fill_price: float | None = None   # 約定平均価格
    error_message: str | None = None      # エラー詳細（Rejected 時など）

    def transition_to(
        self,
        new_state: OrderState,
        *,
        broker_order_id: str | None = None,
        filled_qty: int | None = None,
        avg_fill_price: float | None = None,
        error_message: str | None = None,
    ) -> None:
        """
        状態遷移を検証して self.state を更新する。
        不正な遷移は InvalidStateTransitionError を raise する。
        broker_order_id / filled_qty / avg_fill_price / error_message はキーワード専用引数。
        updated_at は呼び出し時点の UTC に自動更新される。
        """
        allowed = _ALLOWED_TRANSITIONS.get(self.state, set())
        if new_state not in allowed:
            raise InvalidStateTransitionError(
                f"{self.state.value} → {new_state.value} は許可されていない状態遷移です"
            )

        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)

        # オプションフィールドの更新
        if broker_order_id is not None:
            self.broker_order_id = broker_order_id
        if filled_qty is not None:
            self.filled_qty = filled_qty
        if avg_fill_price is not None:
            self.avg_fill_price = avg_fill_price
        if error_message is not None:
            self.error_message = error_message
