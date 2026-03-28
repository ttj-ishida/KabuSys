# src/kabusys/execution/order_manager.py
"""OrderManager — Order State Machine の外向き API。

signal_queue からシグナルを受け取り、broker API 経由で発注・状態管理を行う。
OrderRecord（純粋ロジック）と OrderRepository（SQLite）を組み合わせる。
"""
from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from kabusys.execution.broker_api import BrokerAPIProtocol, OrderRequest, OrderRejectedError
from kabusys.execution.order_record import InvalidStateTransitionError, OrderRecord, OrderState
from kabusys.execution.order_repository import OrderRepository


class DuplicateOrderError(Exception):
    """同一 signal_id の active 注文が既に存在する場合に raise される。"""


_STATUS_TO_STATE: dict[str, OrderState] = {
    "open": OrderState.OrderAccepted,
    "partial": OrderState.PartialFill,
    "filled": OrderState.Filled,
    "cancelled": OrderState.Cancelled,
    "rejected": OrderState.Rejected,
}

# キャンセル不可能な状態。
# order_repository.py の _TERMINAL_STATES（Filled 除く）とは意図が異なる:
# Filled は position tracking 上は 'active' だが、キャンセル不可なのでここに含める。
_CANCEL_INELIGIBLE_STATES = frozenset(
    {OrderState.Closed, OrderState.Cancelled, OrderState.Rejected, OrderState.Filled}
)


class OrderManager:
    def __init__(self, broker: BrokerAPIProtocol, repo: OrderRepository) -> None:
        self._broker = broker
        self._repo = repo

    def create_order(self, signal_id: str, request: OrderRequest) -> OrderRecord:
        """
        OrderCreated レコードを生成して DB に保存する。
        同一 signal_id の active 注文が存在する場合は DuplicateOrderError を raise。
        client_order_id には uuid4 を採番する。
        """
        existing = self._repo.get_by_signal(signal_id)
        active = [
            r for r in existing
            if r.state not in {OrderState.Closed, OrderState.Cancelled, OrderState.Rejected}
        ]
        if active:
            raise DuplicateOrderError(
                f"signal_id={signal_id} の active 注文が既に存在します: "
                f"{active[0].client_order_id}"
            )

        now = datetime.now(timezone.utc)
        record = OrderRecord(
            client_order_id=str(uuid.uuid4()),
            signal_id=signal_id,
            code=request.code,
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            price=request.price,
            state=OrderState.OrderCreated,
            created_at=now,
            updated_at=now,
        )
        try:
            self._repo.save(record)
        except sqlite3.IntegrityError as exc:
            # 部分ユニークインデックス違反: 並列実行でアプリ層チェックを抜けた場合に備える。
            # sqlite3.IntegrityError をそのまま上位に漏らさず DuplicateOrderError に正規化する。
            raise DuplicateOrderError(
                f"signal_id={signal_id} の active 注文が既に存在します（DB 制約）"
            ) from exc
        return record

    def send_order(self, client_order_id: str) -> OrderRecord:
        """
        以下の順序で処理する（クラッシュ安全性のため OrderSent の永続化を broker 呼び出しの前に行う）:

        1. OrderCreated → OrderSent に遷移して SQLite に保存（commit）
        2. broker API の send_order を呼び出す
        3a. 成功: broker_order_id を先に SQLite へ保存（state は Sent のまま commit） ← 2相永続化
        3b. OrderSent → OrderAccepted に遷移して SQLite を更新（commit）
        4. 失敗（OrderRejectedError）: Rejected に遷移して SQLite を更新

        ステップ1 と broker 呼び出しの間でクラッシュした場合、OrderSent レコードが残る。
        ステップ3a と 3b の間でクラッシュした場合でも、broker_order_id が DB に残るため
        Reconciliation（Issue #32）の sync_order が broker 照合で状態を回復できる。
        その他の例外（BrokerAPIError 等）は catch しない — OrderSent のまま残り、
        list_uncertain() で検出される。
        """
        record = self._repo.get(client_order_id)
        if record is None:
            raise RuntimeError(f"注文が見つかりません: {client_order_id}")

        # Step 1: OrderSent に遷移して永続化（broker 呼び出し前）
        record.transition_to(OrderState.OrderSent)
        self._repo.update(record)

        # Step 2: broker API 呼び出し
        api_request = OrderRequest(
            code=record.code,
            side=record.side,
            qty=record.qty,
            order_type=record.order_type,
            price=record.price,
        )
        try:
            response = self._broker.send_order(api_request)

            # Step 3a: broker_order_id を先にコミット（state は Sent のまま）。
            # ここでクラッシュしても broker_order_id が DB に残り、sync_order で照合可能。
            record.broker_order_id = response.order_id
            self._repo.update(record)

            # Step 3b: OrderAccepted に遷移してコミット
            record.transition_to(OrderState.OrderAccepted)
            self._repo.update(record)

        except OrderRejectedError as exc:
            record.transition_to(OrderState.Rejected, error_message=str(exc))
            self._repo.update(record)

        return record

    def sync_order(self, client_order_id: str) -> OrderRecord:
        """
        broker API の get_order_status を呼び、最新状態に同期する。
        broker が None を返した場合は状態を変更しない。
        broker が None を返す可能性: broker_order_id 未設定（クラッシュ後）または注文が見つからない。
        OrderSent に対して broker が 'open' を返した場合は OrderAccepted に遷移する。
        """
        record = self._repo.get(client_order_id)
        if record is None:
            raise RuntimeError(f"注文が見つかりません: {client_order_id}")

        if record.broker_order_id is None:
            return record

        status = self._broker.get_order_status(record.broker_order_id)
        if status is None:
            return record

        new_state = _STATUS_TO_STATE.get(status.status)
        if new_state is None or new_state == record.state:
            return record

        try:
            record.transition_to(
                new_state,
                filled_qty=status.filled_qty,
                avg_fill_price=status.price,
            )
            self._repo.update(record)
        except InvalidStateTransitionError:
            pass  # 既に終端状態の場合は無視

        return record

    def cancel_order(self, client_order_id: str) -> OrderRecord:
        """
        DB の現在状態を確認し、終端状態（Closed / Filled / Cancelled / Rejected）の場合は
        broker API を呼ばずに InvalidStateTransitionError を raise する。
        それ以外の場合は broker API の cancel_order を呼び、Cancelled に遷移する。
        """
        record = self._repo.get(client_order_id)
        if record is None:
            raise RuntimeError(f"注文が見つかりません: {client_order_id}")

        if record.state in _CANCEL_INELIGIBLE_STATES:
            raise InvalidStateTransitionError(
                f"終端状態 ({record.state.value}) の注文はキャンセルできません"
            )

        if record.broker_order_id:
            self._broker.cancel_order(record.broker_order_id)

        record.transition_to(OrderState.Cancelled)
        self._repo.update(record)
        return record
