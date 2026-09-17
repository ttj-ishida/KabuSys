"""Manual trade entry service.

手動で発注・約定した取引を DuckDB に記録するための小さな業務ロジック。
CLI と将来の GUI はこのモジュールを共通利用する。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

import duckdb


class DuplicateManualTradeError(Exception):
    """同一 manual trade ID が既に存在するときに送出される。"""


@dataclass(frozen=True)
class ManualTradeInput:
    trade_date: date
    code: str
    side: str
    qty: int
    price: float
    fees: float = 0.0
    source_signal_id: str | None = None
    note: str | None = None


@dataclass(frozen=True)
class ManualTrade:
    trade_id: str
    trade_date: date
    code: str
    side: str
    qty: int
    price: float
    fees: float
    source_signal_id: str | None
    note: str | None
    created_at: datetime


_MANUAL_TRADES_DDL = """
CREATE TABLE IF NOT EXISTS manual_trades (
    trade_id          VARCHAR       NOT NULL PRIMARY KEY,
    trade_date        DATE          NOT NULL,
    code              VARCHAR       NOT NULL,
    side              VARCHAR       NOT NULL CHECK (side IN ('buy', 'sell')),
    qty               BIGINT        NOT NULL CHECK (qty > 0),
    price             DECIMAL(18,4) NOT NULL CHECK (price >= 0),
    fees              DECIMAL(18,4) NOT NULL DEFAULT 0 CHECK (fees >= 0),
    source_signal_id  VARCHAR,
    note              VARCHAR,
    created_at        TIMESTAMP     NOT NULL DEFAULT current_timestamp
)
"""


def ensure_manual_trade_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(_MANUAL_TRADES_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_manual_trades_date_code ON manual_trades(trade_date, code)"
    )


def build_manual_trade_id(trade_date: date, code: str, side: str) -> str:
    return f"MANUAL_{trade_date.isoformat()}_{code}_{side.lower()}"


def _normalize_input(payload: ManualTradeInput) -> ManualTradeInput:
    code = payload.code.strip()
    side = payload.side.strip().lower()
    if not code:
        raise ValueError("code は必須です")
    if side not in ("buy", "sell"):
        raise ValueError(f"side は buy/sell を指定してください: {payload.side!r}")
    if payload.qty <= 0:
        raise ValueError(f"qty は 1 以上を指定してください: {payload.qty}")
    if payload.price < 0:
        raise ValueError(f"price は 0 以上を指定してください: {payload.price}")
    if payload.fees < 0:
        raise ValueError(f"fees は 0 以上を指定してください: {payload.fees}")
    return ManualTradeInput(
        trade_date=payload.trade_date,
        code=code,
        side=side,
        qty=payload.qty,
        price=payload.price,
        fees=payload.fees,
        source_signal_id=payload.source_signal_id,
        note=payload.note,
    )


def add_manual_trade(
    conn: duckdb.DuckDBPyConnection,
    payload: ManualTradeInput,
    *,
    force: bool = False,
) -> str:
    ensure_manual_trade_schema(conn)
    normalized = _normalize_input(payload)
    trade_id = build_manual_trade_id(
        normalized.trade_date, normalized.code, normalized.side
    )

    conn.execute("BEGIN")
    try:
        existing = conn.execute(
            "SELECT 1 FROM manual_trades WHERE trade_id = ?", [trade_id]
        ).fetchone()
        if existing is not None:
            if not force:
                raise DuplicateManualTradeError(
                    f"trade_id={trade_id!r} は既に存在します。上書きするには --force を指定してください。"
                )
            conn.execute("DELETE FROM manual_trades WHERE trade_id = ?", [trade_id])

        conn.execute(
            """
            INSERT INTO manual_trades (
                trade_id, trade_date, code, side, qty, price, fees, source_signal_id, note
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                trade_id,
                normalized.trade_date,
                normalized.code,
                normalized.side,
                normalized.qty,
                normalized.price,
                normalized.fees,
                normalized.source_signal_id,
                normalized.note,
            ],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return trade_id


def _row_to_manual_trade(row: tuple[Any, ...]) -> ManualTrade:
    return ManualTrade(
        trade_id=row[0],
        trade_date=row[1],
        code=row[2],
        side=row[3],
        qty=int(row[4]),
        price=float(row[5]),
        fees=float(row[6]),
        source_signal_id=row[7],
        note=row[8],
        created_at=row[9],
    )


def list_manual_trades(
    conn: duckdb.DuckDBPyConnection,
    *,
    trade_date: date | None = None,
) -> list[ManualTrade]:
    ensure_manual_trade_schema(conn)
    if trade_date is None:
        rows = conn.execute(
            """
            SELECT trade_id, trade_date, code, side, qty, price, fees,
                   source_signal_id, note, created_at
            FROM manual_trades
            ORDER BY trade_date DESC, created_at DESC, trade_id
            """
        ).fetchall()
    else:
        rows = conn.execute(
            """
            SELECT trade_id, trade_date, code, side, qty, price, fees,
                   source_signal_id, note, created_at
            FROM manual_trades
            WHERE trade_date = ?
            ORDER BY created_at DESC, trade_id
            """,
            [trade_date],
        ).fetchall()
    return [_row_to_manual_trade(row) for row in rows]


def delete_manual_trade(conn: duckdb.DuckDBPyConnection, trade_id: str) -> int:
    ensure_manual_trade_schema(conn)
    existing = conn.execute(
        "SELECT 1 FROM manual_trades WHERE trade_id = ?", [trade_id]
    ).fetchone()
    if existing is None:
        return 0
    conn.execute("DELETE FROM manual_trades WHERE trade_id = ?", [trade_id])
    return 1
