"""
バックテストシミュレータモジュール（スタブ）。

Task 3 で本実装を行う。本ファイルは Task 2 の metrics.py が参照する
データクラスのみを定義したスタブ。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional


@dataclass
class DailySnapshot:
    """1営業日分のポートフォリオ状態スナップショット。"""

    date: date
    cash: float
    positions: dict  # code -> shares
    portfolio_value: float


@dataclass
class TradeRecord:
    """1件の約定記録。"""

    date: date
    code: str
    side: str          # "buy" or "sell"
    shares: int
    price: float
    commission: float
    realized_pnl: Optional[float] = None
