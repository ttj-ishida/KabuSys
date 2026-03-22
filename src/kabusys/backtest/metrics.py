"""
バックテストメトリクス計算モジュール。

BacktestFramework.md Section 3 に定義された評価指標を計算する。
入力は DailySnapshot のリストと TradeRecord のリストのみ（DB 参照なし）。
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kabusys.backtest.simulator import DailySnapshot, TradeRecord


@dataclass
class BacktestMetrics:
    """バックテスト評価指標。"""

    cagr: float           # 年平均成長率
    sharpe_ratio: float   # シャープレシオ（無リスク金利=0）
    max_drawdown: float   # 最大ドローダウン（0〜1）
    win_rate: float       # 勝率（0〜1）
    payoff_ratio: float   # ペイオフレシオ（平均利益 / 平均損失）
    total_trades: int     # 全クローズトレード数


def calc_metrics(
    history: list["DailySnapshot"],
    trades: list["TradeRecord"],
) -> BacktestMetrics:
    """DailySnapshot と TradeRecord からバックテスト評価指標を計算する。

    Args:
        history: 日次ポートフォリオ履歴（portfolio_value が必要）。
        trades:  全約定履歴。SELL の realized_pnl を使用。

    Returns:
        BacktestMetrics インスタンス。
    """
    return BacktestMetrics(
        cagr=_calc_cagr(history),
        sharpe_ratio=_calc_sharpe(history),
        max_drawdown=_calc_max_drawdown(history),
        win_rate=_calc_win_rate(trades),
        payoff_ratio=_calc_payoff_ratio(trades),
        total_trades=len([t for t in trades if t.side == "sell"]),
    )


# ---------------------------------------------------------------------------
# 内部計算関数
# ---------------------------------------------------------------------------

def _calc_cagr(history: list["DailySnapshot"]) -> float:
    """CAGR = (最終資産 / 初期資産)^(365/(終了日-開始日)) - 1。

    暦日ベースで年数を計算する。スナップショット数が2未満の場合は 0.0 を返す。
    """
    if len(history) < 2:
        return 0.0
    initial = history[0].portfolio_value
    final = history[-1].portfolio_value
    if initial <= 0:
        return 0.0
    # 暦日数から年数を計算（DailySnapshot.date フィールドを使用）
    start_date = history[0].date
    end_date = history[-1].date
    days = (end_date - start_date).days
    if days <= 0:
        return 0.0
    years = days / 365.0
    return (final / initial) ** (1.0 / years) - 1.0


def _calc_sharpe(history: list["DailySnapshot"]) -> float:
    """Sharpe Ratio = 年次化超過リターン / 年次化標準偏差（無リスク金利=0）。"""
    if len(history) < 2:
        return 0.0
    values = [s.portfolio_value for s in history]
    returns = [
        (values[i] - values[i - 1]) / values[i - 1]
        for i in range(1, len(values))
        if values[i - 1] > 0
    ]
    if not returns:
        return 0.0
    n = len(returns)
    mean_r = sum(returns) / n
    variance = sum((r - mean_r) ** 2 for r in returns) / n
    std_r = math.sqrt(variance)
    if std_r == 0:
        return 0.0
    # 年次化（営業日252日）
    return (mean_r / std_r) * math.sqrt(252)


def _calc_max_drawdown(history: list["DailySnapshot"]) -> float:
    """Max Drawdown = max(1 - 評価額 / 過去ピーク)。"""
    if not history:
        return 0.0
    peak = history[0].portfolio_value
    max_dd = 0.0
    for snap in history:
        if snap.portfolio_value > peak:
            peak = snap.portfolio_value
        if peak > 0:
            dd = 1.0 - snap.portfolio_value / peak
            if dd > max_dd:
                max_dd = dd
    return max_dd


def _calc_win_rate(trades: list["TradeRecord"]) -> float:
    """勝率 = 勝ちトレード数 / 全クローズトレード数。"""
    sell_trades = [t for t in trades if t.side == "sell" and t.realized_pnl is not None]
    if not sell_trades:
        return 0.0
    wins = sum(1 for t in sell_trades if t.realized_pnl > 0)
    return wins / len(sell_trades)


def _calc_payoff_ratio(trades: list["TradeRecord"]) -> float:
    """Payoff Ratio = 平均利益 / 平均損失（絶対値）。"""
    sell_trades = [t for t in trades if t.side == "sell" and t.realized_pnl is not None]
    wins = [t.realized_pnl for t in sell_trades if t.realized_pnl > 0]
    losses = [t.realized_pnl for t in sell_trades if t.realized_pnl < 0]
    if not wins or not losses:
        return 0.0
    avg_win = sum(wins) / len(wins)
    avg_loss = abs(sum(losses) / len(losses))
    if avg_loss == 0:
        return 0.0
    return avg_win / avg_loss
