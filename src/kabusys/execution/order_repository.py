# src/kabusys/execution/order_repository.py
"""OrderRepository — SQLite を使った Order の永続化層。

ビジネスロジックを持たない。読み書きのみ。
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

from kabusys.execution.order_record import OrderRecord, OrderState


# Closed / Cancelled / Rejected が「終端」。
# Filled は終端ではなく 'active' 扱い（Closed になるまで list_active で返す）。
_TERMINAL_STATES = frozenset({
    OrderState.Closed.value,
    OrderState.Cancelled.value,
    OrderState.Rejected.value,
})


def init_orders_db(conn: sqlite3.Connection) -> None:
    """orders テーブルとインデックスを作成する（べき等）。"""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS orders (
            client_order_id  TEXT     NOT NULL PRIMARY KEY,
            signal_id        TEXT     NOT NULL,
            code             TEXT     NOT NULL,
            side             TEXT     NOT NULL CHECK (side IN ('buy', 'sell')),
            qty              INTEGER  NOT NULL,
            order_type       TEXT     NOT NULL CHECK (order_type IN ('market', 'limit')),
            price            REAL     NOT NULL DEFAULT 0.0,
            state            TEXT     NOT NULL,
            broker_order_id  TEXT,
            filled_qty       INTEGER  NOT NULL DEFAULT 0,
            avg_fill_price   REAL,
            error_message    TEXT,
            created_at       TEXT     NOT NULL,
            updated_at       TEXT     NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_orders_state  ON orders (state);
        CREATE INDEX IF NOT EXISTS idx_orders_signal ON orders (signal_id);
    """)
    conn.commit()


def _row_to_record(row: sqlite3.Row) -> OrderRecord:
    """SQLite の行を OrderRecord に変換する。"""
    return OrderRecord(
        client_order_id=row["client_order_id"],
        signal_id=row["signal_id"],
        code=row["code"],
        side=row["side"],
        qty=row["qty"],
        order_type=row["order_type"],
        price=row["price"],
        state=OrderState(row["state"]),
        broker_order_id=row["broker_order_id"],
        filled_qty=row["filled_qty"],
        avg_fill_price=row["avg_fill_price"],
        error_message=row["error_message"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
    )


class OrderRepository:
    def __init__(self, conn: sqlite3.Connection) -> None:
        conn.row_factory = sqlite3.Row
        self._conn = conn

    def save(self, record: OrderRecord) -> None:
        """INSERT のみ。重複 client_order_id は sqlite3.IntegrityError。"""
        self._conn.execute(
            """
            INSERT INTO orders (
                client_order_id, signal_id, code, side, qty, order_type, price,
                state, broker_order_id, filled_qty, avg_fill_price, error_message,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.client_order_id,
                record.signal_id,
                record.code,
                record.side,
                record.qty,
                record.order_type,
                record.price,
                record.state.value,
                record.broker_order_id,
                record.filled_qty,
                record.avg_fill_price,
                record.error_message,
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
            ),
        )
        self._conn.commit()

    def update(self, record: OrderRecord) -> None:
        """UPDATE。存在しない場合は RuntimeError。"""
        cursor = self._conn.execute(
            """
            UPDATE orders SET
                state           = ?,
                broker_order_id = ?,
                filled_qty      = ?,
                avg_fill_price  = ?,
                error_message   = ?,
                updated_at      = ?
            WHERE client_order_id = ?
            """,
            (
                record.state.value,
                record.broker_order_id,
                record.filled_qty,
                record.avg_fill_price,
                record.error_message,
                record.updated_at.isoformat(),
                record.client_order_id,
            ),
        )
        self._conn.commit()
        if cursor.rowcount == 0:
            raise RuntimeError(
                f"更新対象の注文が見つかりません: {record.client_order_id}"
            )

    def get(self, client_order_id: str) -> OrderRecord | None:
        cursor = self._conn.execute(
            "SELECT * FROM orders WHERE client_order_id = ?",
            (client_order_id,),
        )
        row = cursor.fetchone()
        return _row_to_record(row) if row else None

    def get_by_signal(self, signal_id: str) -> list[OrderRecord]:
        cursor = self._conn.execute(
            "SELECT * FROM orders WHERE signal_id = ?",
            (signal_id,),
        )
        return [_row_to_record(row) for row in cursor.fetchall()]

    def list_active(self) -> list[OrderRecord]:
        """state が Closed / Cancelled / Rejected 以外を返す。"""
        placeholders = ",".join("?" * len(_TERMINAL_STATES))
        cursor = self._conn.execute(
            f"SELECT * FROM orders WHERE state NOT IN ({placeholders})",
            tuple(_TERMINAL_STATES),
        )
        return [_row_to_record(row) for row in cursor.fetchall()]

    def list_uncertain(self) -> list[OrderRecord]:
        """state == OrderSent のみ返す（Reconciliation 用）。"""
        cursor = self._conn.execute(
            "SELECT * FROM orders WHERE state = ?",
            (OrderState.OrderSent.value,),
        )
        return [_row_to_record(row) for row in cursor.fetchall()]
