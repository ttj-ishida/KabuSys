"""保有ポジションの統一表現。

SELL 判定（signal_generator._generate_sell_signals）に渡す保有を、
自動売買分（positions / position_entries）と手動約定分（manual_trades）で
共通の形にそろえる。手動分の読み込みは operations.manual_trades 側に置く。
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date
from typing import Any

import duckdb


@dataclass(frozen=True)
class HeldPosition:
    code: str
    qty: int
    avg_price: float
    first_entry_date: date | None  # 現保有の最古エントリー日（ピーク価格の起点）
    latest_entry_date: date | None  # 現保有の最新エントリー日（保有日数の起点）
    source: str  # "auto" | "manual" | "mixed"


def _to_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value)[:10])


def load_auto_positions(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    sqlite_conn: sqlite3.Connection | None = None,
) -> list[HeldPosition]:
    """positions の target_date 以前の最新行（position_size > 0）を保有として返す。

    entry 日は未クローズの position_entries から取得する。
    sqlite_conn 指定時は SQLite（ライブ実行）、未指定時は DuckDB（バックテスト互換）を参照する。
    """
    rows = conn.execute(
        """
        SELECT p.code, CAST(p.avg_price AS DOUBLE), p.position_size
        FROM positions p
        INNER JOIN (
            SELECT code, MAX(date) AS max_date
            FROM positions
            WHERE date <= ?
            GROUP BY code
        ) m ON p.code = m.code AND p.date = m.max_date
        WHERE p.position_size > 0
        ORDER BY p.code
        """,
        [target_date],
    ).fetchall()

    entry_source: Any = sqlite_conn if sqlite_conn is not None else conn
    positions: list[HeldPosition] = []
    for code, avg_price, size in rows:
        entry_row = entry_source.execute(
            "SELECT MIN(entry_date), MAX(entry_date) FROM position_entries "
            "WHERE code = ? AND sell_date IS NULL",
            [code],
        ).fetchone()
        first_entry, latest_entry = entry_row if entry_row is not None else (None, None)
        positions.append(
            HeldPosition(
                code=code,
                qty=int(size),
                avg_price=float(avg_price) if avg_price is not None else 0.0,
                first_entry_date=_to_date(first_entry),
                latest_entry_date=_to_date(latest_entry),
                source="auto",
            )
        )
    return positions


def _min_date(a: date | None, b: date | None) -> date | None:
    candidates = [d for d in (a, b) if d is not None]
    return min(candidates) if candidates else None


def _max_date(a: date | None, b: date | None) -> date | None:
    candidates = [d for d in (a, b) if d is not None]
    return max(candidates) if candidates else None


def merge_positions(*groups: list[HeldPosition]) -> list[HeldPosition]:
    """同一銘柄を数量合算・数量加重平均単価で 1 件にまとめる（code 昇順）。"""
    merged: dict[str, HeldPosition] = {}
    for group in groups:
        for pos in group:
            cur = merged.get(pos.code)
            if cur is None:
                merged[pos.code] = pos
                continue
            qty = cur.qty + pos.qty
            avg_price = (cur.qty * cur.avg_price + pos.qty * pos.avg_price) / qty if qty else 0.0
            merged[pos.code] = HeldPosition(
                code=pos.code,
                qty=qty,
                avg_price=avg_price,
                first_entry_date=_min_date(cur.first_entry_date, pos.first_entry_date),
                latest_entry_date=_max_date(cur.latest_entry_date, pos.latest_entry_date),
                source=cur.source if cur.source == pos.source else "mixed",
            )
    return sorted(merged.values(), key=lambda p: p.code)
