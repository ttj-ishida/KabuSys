"""
バックテスト結果レポート生成モジュール。

BacktestResult から BacktestReport を構築し、
CLI summary / JSON / Markdown / CSV の各形式で出力・保存する。
"""

from __future__ import annotations

import csv
import json
import re
import uuid
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kabusys.backtest.engine import BacktestResult
    from kabusys.backtest.simulator import DailySnapshot


# ---------------------------------------------------------------------------
# データクラス
# ---------------------------------------------------------------------------


@dataclass
class ReportMeta:
    """実行条件・識別情報。"""

    run_id: str
    generated_at: str  # ISO 8601
    start_date: str
    end_date: str
    initial_cash: float
    slippage_rate: float
    commission_rate: float
    allocation_method: str
    max_position_pct: float
    max_utilization: float
    max_positions: int
    risk_pct: float
    stop_loss_pct: float
    lot_size: int
    report_type: str = "portfolio_backtest"


@dataclass
class HeadlineMetrics:
    """損益・リスクの主要指標。"""

    initial_cash: float
    final_value: float
    total_return: float  # (final - initial) / initial
    cagr: float
    realized_pnl: float
    total_commission: float
    sharpe_ratio: float
    max_drawdown: float
    annual_volatility: float
    calmar_ratio: float


@dataclass
class TradeSection:
    """売買統計。"""

    total_trades: int
    win_rate: float
    payoff_ratio: float
    profit_factor: float
    avg_profit: float
    avg_loss: float
    avg_holding_days: float


@dataclass
class MonthlyReturn:
    """月次リターン1行分。"""

    year: int
    month: int
    return_pct: float  # 月次リターン（%）


@dataclass
class PerformanceSection:
    """パフォーマンス分析セクション。"""

    monthly_returns: list[MonthlyReturn]


@dataclass
class BacktestReport:
    """run_backtest() 後に生成するレポート全体。"""

    meta: ReportMeta
    headline: HeadlineMetrics
    trades: TradeSection
    performance: PerformanceSection
    warnings: list[str]


# ---------------------------------------------------------------------------
# ビルダー
# ---------------------------------------------------------------------------


def build_report(
    result: "BacktestResult",
    *,
    run_id: str | None = None,
    start_date: date,
    end_date: date,
    initial_cash: float = 10_000_000,
    slippage_rate: float = 0.001,
    commission_rate: float = 0.00055,
    allocation_method: str = "risk_based",
    max_position_pct: float = 0.10,
    max_utilization: float = 0.70,
    max_positions: int = 10,
    risk_pct: float = 0.005,
    stop_loss_pct: float = 0.08,
    lot_size: int = 100,
) -> BacktestReport:
    """BacktestResult から BacktestReport を構築する。

    Args:
        result:           run_backtest() の戻り値。
        run_id:           一意の実行 ID（省略時は UUID4 を自動生成）。
        start_date:       バックテスト開始日。
        end_date:         バックテスト終了日。
        その他:           run_backtest() に渡したパラメータをそのまま渡す。

    Returns:
        BacktestReport インスタンス。
    """
    if run_id is None:
        run_id = str(uuid.uuid4())

    m = result.metrics
    history = result.history
    trades = result.trades

    final_value = history[-1].portfolio_value if history else initial_cash
    realized_pnl = sum(
        t.realized_pnl
        for t in trades
        if t.side == "sell" and t.realized_pnl is not None
    )
    total_commission = sum(t.commission for t in trades)
    sell_trades = [t for t in trades if t.side == "sell" and t.realized_pnl is not None]
    avg_profit = (
        sum(t.realized_pnl for t in sell_trades if t.realized_pnl > 0)
        / max(1, sum(1 for t in sell_trades if t.realized_pnl > 0))
        if any(t.realized_pnl > 0 for t in sell_trades)
        else 0.0
    )
    avg_loss = (
        sum(t.realized_pnl for t in sell_trades if t.realized_pnl < 0)
        / max(1, sum(1 for t in sell_trades if t.realized_pnl < 0))
        if any(t.realized_pnl < 0 for t in sell_trades)
        else 0.0
    )

    meta = ReportMeta(
        run_id=run_id,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        initial_cash=initial_cash,
        slippage_rate=slippage_rate,
        commission_rate=commission_rate,
        allocation_method=allocation_method,
        max_position_pct=max_position_pct,
        max_utilization=max_utilization,
        max_positions=max_positions,
        risk_pct=risk_pct,
        stop_loss_pct=stop_loss_pct,
        lot_size=lot_size,
    )
    headline = HeadlineMetrics(
        initial_cash=initial_cash,
        final_value=final_value,
        total_return=(final_value - initial_cash) / initial_cash
        if initial_cash > 0
        else 0.0,
        cagr=m.cagr,
        realized_pnl=realized_pnl,
        total_commission=total_commission,
        sharpe_ratio=m.sharpe_ratio,
        max_drawdown=m.max_drawdown,
        annual_volatility=m.annual_volatility,
        calmar_ratio=m.calmar_ratio,
    )
    trade_section = TradeSection(
        total_trades=m.total_trades,
        win_rate=m.win_rate,
        payoff_ratio=m.payoff_ratio,
        profit_factor=m.profit_factor,
        avg_profit=avg_profit,
        avg_loss=avg_loss,
        avg_holding_days=m.avg_holding_days,
    )
    performance = PerformanceSection(
        monthly_returns=_calc_monthly_returns(history),
    )
    warnings = _generate_warnings(result)

    return BacktestReport(
        meta=meta,
        headline=headline,
        trades=trade_section,
        performance=performance,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------


def format_cli_summary(report: BacktestReport) -> str:
    """CLI 表示用サマリ文字列を返す。headline と warnings のみ。"""
    h = report.headline
    m = report.meta
    t = report.trades
    lines = [
        f"\n{'=' * 50}",
        f"  Backtest Report  {m.start_date} -> {m.end_date}",
        f"  run_id: {m.run_id}",
        f"{'=' * 50}",
        f"  Initial Cash     : {h.initial_cash:>14,.0f} JPY",
        f"  Final Value      : {h.final_value:>14,.0f} JPY",
        f"  Total Return     : {h.total_return:>+13.2%}",
        f"  CAGR             : {h.cagr:>+13.2%}",
        f"  Realized P&L     : {h.realized_pnl:>+14,.0f} JPY",
        f"  Commission       : {h.total_commission:>14,.0f} JPY",
        f"{'─' * 50}",
        f"  Sharpe Ratio     : {h.sharpe_ratio:>13.3f}",
        f"  Max Drawdown     : {h.max_drawdown:>13.2%}",
        f"  Annual Volatility: {h.annual_volatility:>13.2%}",
        f"  Calmar Ratio     : {h.calmar_ratio:>13.3f}",
        f"{'─' * 50}",
        f"  Total Trades     : {t.total_trades:>13}",
        f"  Win Rate         : {t.win_rate:>13.2%}",
        f"  Payoff Ratio     : {t.payoff_ratio:>13.3f}",
        f"  Profit Factor    : {t.profit_factor:>13.3f}",
        f"  Avg Holding Days : {t.avg_holding_days:>13.1f}",
    ]
    if report.warnings:
        lines.append(f"{'─' * 50}")
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{'=' * 50}\n")
    return "\n".join(lines)


def format_json(report: BacktestReport) -> str:
    """全指標を含む JSON 文字列を返す。"""
    data = asdict(report)
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_markdown(report: BacktestReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    h = report.headline
    m = report.meta
    t = report.trades
    lines: list[str] = []

    # 1. Overview
    lines += [
        "# Backtest Report",
        "",
        "## 1. Overview",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| Run ID | `{m.run_id}` |",
        f"| Generated | {m.generated_at} |",
        f"| Period | {m.start_date} → {m.end_date} |",
        f"| Report Type | {m.report_type} |",
        "",
    ]

    # 2. Scope / Config
    lines += [
        "## 2. Scope / Config",
        "",
        "| Parameter | Value |",
        "|-----------|-------|",
        f"| Initial Cash | {m.initial_cash:,.0f} JPY |",
        f"| Allocation Method | {m.allocation_method} |",
        f"| Max Position % | {m.max_position_pct:.0%} |",
        f"| Max Utilization | {m.max_utilization:.0%} |",
        f"| Max Positions | {m.max_positions} |",
        f"| Slippage Rate | {m.slippage_rate:.4f} |",
        f"| Commission Rate | {m.commission_rate:.5f} |",
        f"| Risk % (risk_based) | {m.risk_pct:.3f} |",
        f"| Stop Loss % | {m.stop_loss_pct:.0%} |",
        f"| Lot Size | {m.lot_size} |",
        "",
    ]

    # 3. Headline Metrics
    lines += [
        "## 3. Headline Metrics",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Initial Cash | {h.initial_cash:,.0f} JPY |",
        f"| Final Value | {h.final_value:,.0f} JPY |",
        f"| Total Return | {h.total_return:+.2%} |",
        f"| CAGR | {h.cagr:+.2%} |",
        f"| Realized P&L | {h.realized_pnl:+,.0f} JPY |",
        f"| Total Commission | {h.total_commission:,.0f} JPY |",
        "",
    ]

    # 4. Risk
    lines += [
        "## 4. Equity & Risk",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Sharpe Ratio | {h.sharpe_ratio:.3f} |",
        f"| Max Drawdown | {h.max_drawdown:.2%} |",
        f"| Annual Volatility | {h.annual_volatility:.2%} |",
        f"| Calmar Ratio | {h.calmar_ratio:.3f} |",
        "",
    ]

    # 5. Trade Analysis
    lines += [
        "## 5. Trade Analysis",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Trades | {t.total_trades} |",
        f"| Win Rate | {t.win_rate:.2%} |",
        f"| Payoff Ratio | {t.payoff_ratio:.3f} |",
        f"| Profit Factor | {t.profit_factor:.3f} |",
        f"| Avg Profit | {t.avg_profit:+,.0f} JPY |",
        f"| Avg Loss | {t.avg_loss:+,.0f} JPY |",
        f"| Avg Holding Days | {t.avg_holding_days:.1f} days |",
        "",
    ]

    # 6. Monthly Returns
    monthly = report.performance.monthly_returns
    if monthly:
        lines += [
            "## 6. Monthly Returns",
            "",
            "| Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec |",
            "|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|",
        ]
        by_year: dict[int, dict[int, float]] = {}
        for mr in monthly:
            by_year.setdefault(mr.year, {})[mr.month] = mr.return_pct
        for year in sorted(by_year):
            cells = [f"| {year} "]
            for mo in range(1, 13):
                val = by_year[year].get(mo)
                cells.append(f"| {val:+.1f}% " if val is not None else "| — ")
            lines.append("".join(cells) + "|")
        lines.append("")

    # 7. Warnings
    if report.warnings:
        lines += [
            "## 7. Warnings",
            "",
        ]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: BacktestReport,
    result: "BacktestResult",
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/backtests/{run_id}/ に保存する。

    保存ファイル:
        summary.json      全指標 JSON
        report.md         Markdown レポート
        trades.csv        約定一覧
        daily_equity.csv  日次ポートフォリオ履歴

    同一 run_id で再実行した場合は既存ファイルを上書きする（exist_ok=True）。

    Args:
        report:     build_report() の戻り値。
        result:     run_backtest() の戻り値（CSV 出力用）。
        output_dir: 保存先ルート（省略時は artifacts/backtests）。

    Returns:
        保存先ディレクトリのパス。
    """
    base = Path(output_dir) if output_dir else Path("artifacts") / "backtests"
    safe_run_id = re.sub(r"[^A-Za-z0-9._-]", "_", report.meta.run_id)
    run_dir = base / safe_run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    # summary.json
    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")

    # report.md
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")

    # trades.csv
    trades_path = run_dir / "trades.csv"
    with trades_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            ["date", "code", "side", "shares", "price", "commission", "realized_pnl"]
        )
        for t in result.trades:
            writer.writerow(
                [
                    t.date.isoformat(),
                    t.code,
                    t.side,
                    t.shares,
                    t.price,
                    t.commission,
                    t.realized_pnl,
                ]
            )

    # daily_equity.csv
    equity_path = run_dir / "daily_equity.csv"
    with equity_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "cash", "portfolio_value"])
        for s in result.history:
            writer.writerow([s.date.isoformat(), s.cash, s.portfolio_value])

    return run_dir


# ---------------------------------------------------------------------------
# 内部ヘルパー
# ---------------------------------------------------------------------------


def _calc_monthly_returns(history: list["DailySnapshot"]) -> list[MonthlyReturn]:
    """日次スナップショットから月次リターンを計算する。"""
    if len(history) < 2:
        return []

    # 月末値を収集（入力順序に依存しないよう日付昇順でソート）
    month_end: dict[tuple[int, int], float] = {}
    for snap in sorted(history, key=lambda s: s.date):
        key = (snap.date.year, snap.date.month)
        month_end[key] = snap.portfolio_value

    keys = sorted(month_end)
    if len(keys) < 2:
        return []

    results: list[MonthlyReturn] = []
    prev_value = None
    prev_key = None

    for key in keys:
        value = month_end[key]
        if prev_value is not None and prev_key is not None:
            # 月が連続している（または跨いでいる）場合にリターンを計算
            ret = (value - prev_value) / prev_value if prev_value > 0 else 0.0
            results.append(
                MonthlyReturn(year=key[0], month=key[1], return_pct=ret * 100)
            )
        prev_value = value
        prev_key = key

    return results


def _generate_warnings(result: "BacktestResult") -> list[str]:
    """結果に基づいて自動 Warning を生成する。"""
    warnings: list[str] = []
    m = result.metrics
    trades = result.trades
    history = result.history

    # 総トレード数が少ない
    if m.total_trades < 10:
        warnings.append(
            f"総トレード数が少ないです（{m.total_trades}件）。統計的信頼性が低い可能性があります。"
        )

    # 検証期間が短い（入力順序に依存しないよう min/max で期間を算出）
    if len(history) >= 2:
        days = (max(s.date for s in history) - min(s.date for s in history)).days
        if days < 180:
            warnings.append(
                f"検証期間が短いです（{days}日）。180日以上の検証を推奨します。"
            )

    # 1銘柄寄与が過大（正の pnl のみで集計。負含む総和では損失が大きいと比率が歪むため）
    sell_trades = [t for t in trades if t.side == "sell" and t.realized_pnl is not None]
    if sell_trades:
        pos_by_code: dict[str, float] = {}
        for t in sell_trades:
            if t.realized_pnl > 0:
                pos_by_code[t.code] = pos_by_code.get(t.code, 0.0) + t.realized_pnl
        total_pos = sum(pos_by_code.values())
        if total_pos > 0:
            top_code, max_contrib = max(pos_by_code.items(), key=lambda kv: kv[1])
            if max_contrib / total_pos > 0.5:
                warnings.append(
                    f"銘柄 {top_code} が利益合計の {max_contrib / total_pos:.0%} を占めています。"
                    "特定銘柄への依存が過大な可能性があります。"
                )

    return warnings
