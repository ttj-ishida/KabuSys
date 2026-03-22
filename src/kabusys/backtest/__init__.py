"""バックテストフレームワーク。"""
from kabusys.backtest.engine import run_backtest, BacktestResult
from kabusys.backtest.simulator import DailySnapshot, TradeRecord
from kabusys.backtest.metrics import BacktestMetrics

__all__ = [
    "run_backtest",
    "BacktestResult",
    "DailySnapshot",
    "TradeRecord",
    "BacktestMetrics",
]
