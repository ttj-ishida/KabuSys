"""regime.py — RegimeProvider プロトコルと Core 実装。

Core-only モード（AI Addon 未導入時）は NullRegimeProvider を使う。
AI Addon 有効時は DatabaseRegimeProvider が market_regime テーブルを参照する。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Protocol, runtime_checkable

import duckdb

logger = logging.getLogger(__name__)


@runtime_checkable
class RegimeProvider(Protocol):
    """市場レジームラベルを返すインターフェース。"""

    def get_regime(self, target_date: date) -> str:
        """レジームラベルを返す。データなし時は 'bull' を返す。"""
        ...


class NullRegimeProvider:
    """AI Addon 未導入時のフォールバック。常に 'bull' を返す。"""

    def get_regime(self, target_date: date) -> str:
        return "bull"


class DatabaseRegimeProvider:
    """market_regime テーブルからレジームを取得する Core 実装。"""

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def get_regime(self, target_date: date) -> str:
        row = self._conn.execute(
            "SELECT regime_label FROM market_regime WHERE date = ?",
            [target_date],
        ).fetchone()
        if row is None:
            logger.debug("market_regime not found for %s; fallback to 'bull'", target_date)
            return "bull"
        return row[0]
