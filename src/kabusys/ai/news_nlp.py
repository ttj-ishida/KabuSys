"""
ニュースNLPモジュール（スタブ）

このファイルは kabusys.ai.regime_detector のインポートを解決するための
スタブです。実装は後続タスクで追加されます。
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import duckdb


def calc_news_window(
    conn: duckdb.DuckDBPyConnection,
    target_date: date,
    window_days: int = 1,
) -> list[str]:
    """ニュースウィンドウ内のタイトル一覧を返す（スタブ）。"""
    raise NotImplementedError("calc_news_window は未実装です")
