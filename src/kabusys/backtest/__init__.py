"""バックテストフレームワーク。"""

from kabusys.backtest.engine import BacktestResult, run_backtest
from kabusys.backtest.metrics import BacktestMetrics
from kabusys.backtest.simulator import DailySnapshot, TradeRecord

__all__ = [
    "run_backtest",
    "BacktestResult",
    "DailySnapshot",
    "TradeRecord",
    "BacktestMetrics",
]
