# src/kabusys/execution/signal_queue_status.py
"""signal_queue の処理状態を SQLite に記録する（Issue #413）。

Execution Engine は DuckDB を read_only で開くため、signal_queue の status を
DuckDB に直接書かない。代わりに SQLite の signal_queue_status に記録し、
夜間の portfolio_construction（DuckDB を排他利用する時間帯）で
sync_to_duckdb() により DuckDB の signal_queue.status / processed_at へ反映する。

status の意味:
  pending    — エンジンが読み込んだが未処理（Gate 2 で見送り等）。再起動時に再処理対象。
  processing — 発注直前〜約定待ち。再起動時に再読込しない。
  filled     — 約定済み
  cancelled  — 重複（同一業務キーの注文が既にある）または取消
  failed     — リスクゲート不合格・発注 API 失敗・ブローカー拒否
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, timezone

from kabusys.execution.order_record import OrderState

logger = logging.getLogger(__name__)

VALID_STATUSES = frozenset({"pending", "processing", "filled", "cancelled", "failed"})

_DDL = """
CREATE TABLE IF NOT EXISTS signal_queue_status (
    queue_signal_id TEXT PRIMARY KEY,
    business_key    TEXT NOT NULL,
    signal_date     TEXT NOT NULL,
    code            TEXT NOT NULL,
    side            TEXT NOT NULL,
    status          TEXT NOT NULL
                    CHECK (status IN ('pending','processing','filled','cancelled','failed')),
    reason          TEXT,
    client_order_id TEXT,
    updated_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sqs_business_key ON signal_queue_status(business_key);
CREATE INDEX IF NOT EXISTS idx_sqs_signal_date ON signal_queue_status(signal_date);
CREATE INDEX IF NOT EXISTS idx_sqs_client_order_id ON signal_queue_status(client_order_id);
"""


def ensure_schema(conn: sqlite3.Connection) -> None:
    """signal_queue_status テーブルとインデックスを作成する（冪等）。"""
    conn.executescript(_DDL)
    conn.commit()


def business_key(signal_date: date, code: str, side: str) -> str:
    """発注の業務キー {signal_date}_{code}_{side} を返す。"""
    return f"{signal_date.isoformat()}_{code}_{side}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _table_exists(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'signal_queue_status'"
    ).fetchone()
    return row is not None


def record(
    conn: sqlite3.Connection,
    *,
    queue_signal_id: str,
    signal_date: date,
    code: str,
    side: str,
    status: str,
    reason: str | None = None,
    client_order_id: str | None = None,
) -> None:
    """queue 行の状態を UPSERT する。

    client_order_id は None で上書きしない（一度紐付いた注文を失わないため）。
    """
    conn.execute(
        """
        INSERT INTO signal_queue_status (
            queue_signal_id, business_key, signal_date, code, side,
            status, reason, client_order_id, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(queue_signal_id) DO UPDATE SET
            status          = excluded.status,
            reason          = excluded.reason,
            client_order_id = COALESCE(excluded.client_order_id,
                                       signal_queue_status.client_order_id),
            updated_at      = excluded.updated_at
        """,
        (
            queue_signal_id,
            business_key(signal_date, code, side),
            signal_date.isoformat(),
            code,
            side,
            status,
            reason,
            client_order_id,
            _now(),
        ),
    )
    conn.commit()


def register_pending(
    conn: sqlite3.Connection,
    *,
    queue_signal_id: str,
    signal_date: date,
    code: str,
    side: str,
) -> None:
    """未記録の queue 行を pending として登録する。既存行は変更しない。"""
    conn.execute(
        """
        INSERT INTO signal_queue_status (
            queue_signal_id, business_key, signal_date, code, side, status, updated_at
        ) VALUES (?, ?, ?, ?, ?, 'pending', ?)
        ON CONFLICT(queue_signal_id) DO NOTHING
        """,
        (
            queue_signal_id,
            business_key(signal_date, code, side),
            signal_date.isoformat(),
            code,
            side,
            _now(),
        ),
    )
    conn.commit()


def get_statuses(conn: sqlite3.Connection, signal_date: date) -> dict[str, str]:
    """signal_date の {queue_signal_id: status} を返す。テーブルがなければ空。"""
    if not _table_exists(conn):
        return {}
    rows = conn.execute(
        "SELECT queue_signal_id, status FROM signal_queue_status WHERE signal_date = ?",
        (signal_date.isoformat(),),
    ).fetchall()
    return {str(r[0]): str(r[1]) for r in rows}


def count_by_status(conn: sqlite3.Connection, signal_date: date, status: str) -> int:
    """signal_date で status の件数を返す。テーブルがなければ 0。"""
    if not _table_exists(conn):
        return 0
    row = conn.execute(
        "SELECT COUNT(*) FROM signal_queue_status WHERE signal_date = ? AND status = ?",
        (signal_date.isoformat(), status),
    ).fetchone()
    return int(row[0]) if row and row[0] is not None else 0


def update_by_client_order_id(
    conn: sqlite3.Connection,
    client_order_id: str,
    status: str,
    reason: str | None = None,
) -> int:
    """client_order_id に紐付く行の status を更新し、更新件数を返す。"""
    cur = conn.execute(
        """
        UPDATE signal_queue_status
           SET status = ?, reason = ?, updated_at = ?
         WHERE client_order_id = ?
           AND (status IS NOT ? OR reason IS NOT ?)
        """,
        (status, reason, _now(), client_order_id, status, reason),
    )
    conn.commit()
    return int(cur.rowcount or 0)


def list_open_order_links(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """注文に紐付き、まだ確定していない行の (queue_signal_id, client_order_id) を返す。

    processing（約定待ち）と failed（発注 API 例外。注文自体は送信済みの可能性あり）が対象。
    """
    if not _table_exists(conn):
        return []
    rows = conn.execute(
        """
        SELECT queue_signal_id, client_order_id FROM signal_queue_status
         WHERE client_order_id IS NOT NULL AND status IN ('processing', 'failed')
        """
    ).fetchall()
    return [(str(r[0]), str(r[1])) for r in rows]


def list_processing_without_order_id(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """client_order_id が未設定の processing 行の (queue_signal_id, business_key) を返す。"""
    if not _table_exists(conn):
        return []
    rows = conn.execute(
        """
        SELECT queue_signal_id, business_key FROM signal_queue_status
         WHERE status = 'processing' AND client_order_id IS NULL
        """
    ).fetchall()
    return [(str(r[0]), str(r[1])) for r in rows]


def count_unprocessed_pending(
    duckdb_conn, sqlite_conn: sqlite3.Connection, signal_date: date
) -> int:
    """signal_date の DuckDB signal_queue 行のうち、まだ処理されていない件数を返す。

    DuckDB で status='pending' の行から、SQLite signal_queue_status で pending 以外
    （処理済み）と記録された行を除いて数える。Execution Engine が起動しなかった・
    行を読まなかった場合も未処理として数える。signal_queue テーブルがなければ 0。
    """
    exists = duckdb_conn.execute(
        """
        SELECT 1 FROM information_schema.tables
         WHERE lower(table_name) = 'signal_queue' AND table_schema = current_schema()
         LIMIT 1
        """
    ).fetchone()
    if exists is None:
        return 0
    rows = duckdb_conn.execute(
        "SELECT signal_id FROM signal_queue WHERE date = ? AND status = 'pending'",
        [signal_date],
    ).fetchall()
    processed = {
        qid for qid, st in get_statuses(sqlite_conn, signal_date).items() if st != "pending"
    }
    return sum(1 for r in rows if str(r[0]) not in processed)


def status_for_order_state(state: OrderState) -> tuple[str, str | None]:
    """注文の状態を (signal_queue status, reason) に変換する。"""
    if state in (OrderState.Filled, OrderState.Closed):
        return "filled", None
    if state == OrderState.Rejected:
        return "failed", "rejected"
    if state == OrderState.Cancelled:
        return "cancelled", "cancelled"
    return "processing", None


def _to_duckdb_timestamp(raw: str) -> datetime | None:
    try:
        dt = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)  # ローカル時刻（naive）で保存
    return dt


def sync_to_duckdb(duckdb_conn, sqlite_conn: sqlite3.Connection) -> int:
    """SQLite の非 pending ステータスを DuckDB signal_queue に反映し、更新件数を返す。

    pending 行には触れない。status が既に一致する行は更新しない（冪等）。
    """
    if not _table_exists(sqlite_conn):
        return 0
    rows = sqlite_conn.execute(
        "SELECT queue_signal_id, status, updated_at FROM signal_queue_status"
        " WHERE status != 'pending'"
    ).fetchall()
    updated = 0
    for qid, status, updated_at in rows:
        result = duckdb_conn.execute(
            """
            UPDATE signal_queue
               SET status = ?, processed_at = COALESCE(?, processed_at)
             WHERE signal_id = ? AND status IS DISTINCT FROM ?
            """,
            [status, _to_duckdb_timestamp(updated_at), qid, status],
        ).fetchone()
        updated += int(result[0]) if result and result[0] is not None else 0
    return updated
