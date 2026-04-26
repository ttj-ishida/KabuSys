"""
バックテストメトリクス計算モジュール。

BacktestFramework.md Section 3 に定義された評価指標を計算する。
入力は DailySnapshot のリストと TradeRecord のリストのみ（DB 参照なし）。
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kabusys.backtest.simulator import DailySnapshot, TradeRecord


@dataclass
class BacktestMetrics:
    """バックテスト評価指標。"""

    cagr: float  # 年平均成長率
    sharpe_ratio: float  # シャープレシオ（無リスク金利=0）
    max_drawdown: float  # 最大ドローダウン（0〜1）
    win_rate: float  # 勝率（0〜1）
    payoff_ratio: float  # ペイオフレシオ（平均利益 / 平均損失）
    total_trades: int  # 全クローズトレード数
    annual_volatility: float = 0.0  # 年率ボラティリティ
    calmar_ratio: float = 0.0  # Calmar Ratio = CAGR / Max Drawdown
    profit_factor: float = 0.0  # Profit Factor = 総利益 / 総損失（絶対値）
    avg_holding_days: float = 0.0  # 平均保有日数


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
    cagr = _calc_cagr(history)
    max_dd = _calc_max_drawdown(history)
    return BacktestMetrics(
        cagr=cagr,
        sharpe_ratio=_calc_sharpe(history),
        max_drawdown=max_dd,
        win_rate=_calc_win_rate(trades),
        payoff_ratio=_calc_payoff_ratio(trades),
        total_trades=sum(1 for t in trades if t.side == "sell"),
        annual_volatility=_calc_annual_volatility(history),
        calmar_ratio=_calc_calmar_ratio(cagr, max_dd),
        profit_factor=_calc_profit_factor(trades),
        avg_holding_days=_calc_avg_holding_days(trades),
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
    history = sorted(history, key=lambda s: s.date)
    initial = history[0].portfolio_value
    final = history[-1].portfolio_value
    if initial <= 0:
        return 0.0
    start_date = history[0].date
    end_date = history[-1].date
    days = (end_date - start_date).days
    if days <= 0:
        return 0.0
    years = days / 365.0
    return (final / initial) ** (1.0 / years) - 1.0


def _calc_sharpe(history: list["DailySnapshot"]) -> float:
    """Sharpe Ratio = 年次化超過リターン / 年次化標準偏差（無リスク金利=0）。

    分散は母分散（n 分母）で計算する。DailySnapshot は取引日のみ前提（252 日/年）。
    """
    if len(history) < 2:
        return 0.0
    history = sorted(history, key=lambda s: s.date)
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
    if variance <= 0:
        return 0.0
    # 年次化（営業日252日）
    return (mean_r / math.sqrt(variance)) * math.sqrt(252)


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


def _calc_annual_volatility(history: list["DailySnapshot"]) -> float:
    """年率ボラティリティ = 日次リターンの標準偏差 × sqrt(252)。

    分散は母分散（n 分母）で計算する。DailySnapshot は取引日のみ前提。
    """
    if len(history) < 2:
        return 0.0
    history = sorted(history, key=lambda s: s.date)
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
    return math.sqrt(variance) * math.sqrt(252)


def _calc_calmar_ratio(cagr: float, max_drawdown: float) -> float:
    """Calmar Ratio = CAGR / Max Drawdown。ドローダウンが 0 の場合は 0.0 を返す。

    MDD=0（ドローダウンなし）のとき理論上は ∞ だが、下流のシリアライズ互換のため 0.0 とする。
    """
    if max_drawdown <= 0:
        return 0.0
    return cagr / max_drawdown


def _calc_profit_factor(trades: list["TradeRecord"]) -> float:
    """Profit Factor = 総利益 / 総損失（絶対値）。

    損失トレードなし（損失=0）のとき理論上は ∞ だが、シリアライズ互換のため 0.0 を返す。
    """
    sell_trades = [t for t in trades if t.side == "sell" and t.realized_pnl is not None]
    total_profit = sum(t.realized_pnl for t in sell_trades if t.realized_pnl > 0)
    total_loss = abs(sum(t.realized_pnl for t in sell_trades if t.realized_pnl < 0))
    if total_loss == 0:
        return 0.0
    return total_profit / total_loss


def _calc_avg_holding_days(trades: list["TradeRecord"]) -> float:
    """平均保有日数 = BUY-SELL ペアの保有日数の平均。

    同一 code の BUY→SELL を FIFO でマッチする（数量・分割決済は未考慮）。
    入力順序に依存しないよう (date, side) 昇順（同日は BUY を先に）でソートする。
    ペアが存在しない場合は 0.0 を返す。
    """
    buy_dates: dict[str, deque[date]] = {}
    holding_days: list[float] = []
    sorted_trades = sorted(trades, key=lambda t: (t.date, 0 if t.side == "buy" else 1))
    for t in sorted_trades:
        if t.side == "buy":
            buy_dates.setdefault(t.code, deque()).append(t.date)
        elif t.side == "sell" and t.code in buy_dates and buy_dates[t.code]:
            entry_date = buy_dates[t.code].popleft()
            days = max(0, (t.date - entry_date).days)
            holding_days.append(float(days))
    if not holding_days:
        return 0.0
    return sum(holding_days) / len(holding_days)
