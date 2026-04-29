"""運用成績サマリーレポート生成モジュール。

DB への参照は行わず、呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from kabusys.operations.performance_collector import (  # noqa: F401
    DailyRow,
    MonthlyRow,
    WeeklyRow,
)


@dataclass
class PerformanceReport:
    report_type: str   # "daily" | "weekly" | "monthly"
    env: str           # "live" | "paper_trading"
    generated_at: str  # ISO 8601 UTC
    from_date: str     # YYYY-MM-DD
    to_date: str       # YYYY-MM-DD
    rows: list         # list[DailyRow | WeeklyRow | MonthlyRow]
    summary: dict


def build_report(
    rows: list,
    *,
    report_type: str,
    env: str,
    from_date: date,
    to_date: date,
) -> PerformanceReport:
    """PerformanceReport を構築する。rows が空の場合は summary を None 値で返す。"""
    if not rows:
        summary: dict = {
            "total_trading_days": 0,
            "cumulative_return": None,
            "max_drawdown": None,
            "win_rate": None,
            "equity_start": None,
            "equity_end": None,
        }
    elif report_type == "daily":
        total = len(rows)
        eq_start = rows[0].equity
        eq_end = rows[-1].equity
        cum = (eq_end / eq_start - 1.0) if eq_start != 0.0 else None
        drawdowns = [r.drawdown for r in rows if r.drawdown is not None]
        max_dd = min(drawdowns) if drawdowns else None
        win = sum(1 for r in rows if r.daily_return is not None and r.daily_return > 0)
        summary = {
            "total_trading_days": total,
            "cumulative_return": cum,
            "max_drawdown": max_dd,
            "win_rate": win / total if total > 0 else None,
            "equity_start": eq_start,
            "equity_end": eq_end,
        }
    else:
        # weekly または monthly
        total = sum(r.trading_days for r in rows)
        eq_start = rows[0].equity_start
        eq_end = rows[-1].equity_end
        cum = (eq_end / eq_start - 1.0) if (eq_start and eq_start != 0.0) else None
        drawdowns = [r.max_drawdown for r in rows if r.max_drawdown is not None]
        max_dd = min(drawdowns) if drawdowns else None
        win = sum(r.win_days for r in rows)
        summary = {
            "total_trading_days": total,
            "cumulative_return": cum,
            "max_drawdown": max_dd,
            "win_rate": win / total if total > 0 else None,
            "equity_start": eq_start,
            "equity_end": eq_end,
        }
    return PerformanceReport(
        report_type=report_type,
        env=env,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        from_date=from_date.isoformat(),
        to_date=to_date.isoformat(),
        rows=rows,
        summary=summary,
    )


def format_markdown(report: PerformanceReport) -> str:
    raise NotImplementedError


def save_report(
    report: PerformanceReport,
    output_dir: Path | str | None = None,
) -> Path:
    raise NotImplementedError
