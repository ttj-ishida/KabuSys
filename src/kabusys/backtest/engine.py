"""
バックテストエンジンモジュール（スタブ）。

Task 4/5 で本実装を行う。本ファイルは __init__.py の import を通すためのスタブ。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class BacktestResult:
    """バックテスト実行結果（スタブ）。"""

    history: list = field(default_factory=list)
    trades: list = field(default_factory=list)
    metrics: Any = None


def run_backtest(*args: Any, **kwargs: Any) -> BacktestResult:
    """バックテストを実行する（スタブ）。Task 5 で本実装を行う。"""
    raise NotImplementedError("run_backtest is not yet implemented (Task 5)")
