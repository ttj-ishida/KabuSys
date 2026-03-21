"""
SimulatedClock — バックテスト用模擬時計。

engine.py のループ変数 trading_day が Simulated Time として機能するため、
現実装でこのクラスを直接使う必要はない。将来の拡張（分足シミュレーション等）用。
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class SimulatedClock:
    """バックテスト用の模擬時計。current_date を保持する。"""

    current_date: date
