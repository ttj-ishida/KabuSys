"""手動注文候補レポート（#412）の補助チェック。

データクラスに依存しない純粋なヘルパー群（DD 停止・ギャップ閾値・買付可能価格・
シグナル生成後の手動約定検出）。収集本体は manual_order_report.py。
"""

from __future__ import annotations

import logging
import math
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any

import duckdb

logger = logging.getLogger(__name__)


class SafeReader:
    """テーブル欠落（CatalogException）を空扱い + 警告にする読み取りヘルパー。"""

    def __init__(self, conn: duckdb.DuckDBPyConnection, warnings: list[str]) -> None:
        self.conn = conn
        self.warnings = warnings

    def warn(self, msg: str) -> None:
        if msg not in self.warnings:
            self.warnings.append(msg)

    def fetch(self, table: str, sql: str, params: list[Any] | None = None) -> list[tuple]:
        try:
            return self.conn.execute(sql, params or []).fetchall()
        except duckdb.CatalogException:
            self.warn(f"テーブル {table} がないため空として扱いました")
            return []

    def has_table(self, table: str) -> bool:
        row = self.conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = 'main' AND table_name = ?",
            [table],
        ).fetchone()
        return bool(row and row[0])


def as_date(v: object) -> date | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return date.fromisoformat(str(v)[:10])


HOLDINGS_CHANGED_REASON = "シグナル生成後に保有が変わりました。株数を再確認してください"


def check_dd_stop(sqlite_path: Path | None) -> tuple[bool | None, str | None]:
    """監視 SQLite の dashboard.dd_stop_blocked_since を読む。読めなければ (None, None)。"""
    if sqlite_path is None or not Path(sqlite_path).exists():
        return None, None
    try:
        sc = sqlite3.connect(f"file:{Path(sqlite_path).as_posix()}?mode=ro", uri=True)
        try:
            row = sc.execute("SELECT dd_stop_blocked_since FROM dashboard WHERE id = 1").fetchone()
        finally:
            sc.close()
    except Exception:
        logger.warning("DD 停止状態の取得に失敗しました: %s", sqlite_path, exc_info=True)
        return None, None
    since = row[0] if row else None
    return (since is not None and str(since).strip() != ""), since


def load_gap_thresholds() -> tuple[float, float]:
    """config/strategy_config.yaml の (gap_up_threshold, gap_down_threshold)。"""
    from kabusys.strategy.signal_generator import _load_strategy_config

    cfg = _load_strategy_config()
    return float(cfg["gap_up_threshold"]), float(cfg["gap_down_threshold"])


def buy_price_bounds(ref: float | None, gaps: tuple[float, float]) -> tuple[int | None, int | None]:
    """寄り付きで買付可能な (上限, 下限) 価格（円単位）。

    見送りルールは「前日終値比 +up 超 / down 以下」なので、
    上限 = floor(ref×(1+up))（この価格以下なら可）、
    下限 = ref×(1+down) を超える最小の整数円（この価格以上なら可）。
    浮動小数点誤差を避けるため 6 桁で丸めてから整数化する。
    """
    if ref is None:
        return None, None
    upper = math.floor(round(ref * (1 + gaps[0]), 6))
    lower = math.floor(round(ref * (1 + gaps[1]), 6)) + 1
    return upper, lower


def holdings_changed_codes(
    conn: duckdb.DuckDBPyConnection,
    signal_date: date,
    signal_created_at: dict[str, datetime | None],
) -> set[str]:
    """シグナル生成後に手動約定が入った BUY 候補コード。

    manual_trades に trade_date > signal_date、または created_at > そのコードの
    signal_queue.created_at の行があれば対象。テーブルがなければ空集合。
    """
    codes = list(signal_created_at)
    if not codes:
        return set()
    params = ",".join(["?"] * len(codes))
    try:
        rows = conn.execute(
            f"SELECT code, MAX(trade_date), MAX(created_at) FROM manual_trades "
            f"WHERE code IN ({params}) GROUP BY code",
            codes,
        ).fetchall()
    except duckdb.CatalogException:
        return set()
    changed: set[str] = set()
    for code, max_trade_date, max_created in rows:
        if max_trade_date is not None and max_trade_date > signal_date:
            changed.add(code)
            continue
        sq_created = signal_created_at.get(code)
        if sq_created is not None and max_created is not None and max_created > sq_created:
            changed.add(code)
    return changed
