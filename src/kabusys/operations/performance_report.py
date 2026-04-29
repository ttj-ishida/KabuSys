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


_REPORT_TYPE_JA = {"daily": "日次", "weekly": "週次", "monthly": "月次"}


def _fmt_return(v: float | None) -> str:
    if v is None:
        return "N/A"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2%}"


def _fmt_yen(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"¥{int(v):,}"


def _fmt_rate(v: float | None) -> str:
    if v is None:
        return "N/A"
    return f"{v:.1%}"


def format_markdown(report: PerformanceReport) -> str:
    """PerformanceReport を Markdown 文字列に変換する。"""
    type_ja = _REPORT_TYPE_JA.get(report.report_type, report.report_type)
    s = report.summary
    lines = [
        f"# 運用成績レポート（{type_ja}）",
        "",
        f"- 環境: {report.env}",
        f"- 期間: {report.from_date} 〜 {report.to_date}",
        f"- 生成日時: {report.generated_at}",
        "",
        "## サマリー",
        "",
        "| 項目 | 値 |",
        "|---|---|",
        f"| 営業日数 | {s['total_trading_days']} 日 |",
        f"| 累積リターン | {_fmt_return(s['cumulative_return'])} |",
        f"| 最大ドローダウン | {_fmt_return(s['max_drawdown'])} |",
        f"| 勝率 | {_fmt_rate(s['win_rate'])} |",
        f"| 期首総資産 | {_fmt_yen(s['equity_start'])} |",
        f"| 期末総資産 | {_fmt_yen(s['equity_end'])} |",
        "",
    ]

    if report.report_type == "daily":
        lines += [
            "## 日次明細",
            "",
            "| 日付 | 総資産 | 日次リターン | ドローダウン | 累積リターン |",
            "|---|---|---|---|---|",
        ]
        for r in report.rows:
            lines.append(
                f"| {r.date} | {_fmt_yen(r.equity)} | {_fmt_return(r.daily_return)}"
                f" | {_fmt_return(r.drawdown)} | {_fmt_return(r.cumulative_return)} |"
            )
    elif report.report_type == "weekly":
        lines += [
            "## 週次明細",
            "",
            "| 週 | 営業日数 | 期首資産 | 期末資産 | 週次リターン | 最大DD | 勝ち日数 |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in report.rows:
            lines.append(
                f"| {r.week_label} | {r.trading_days} | {_fmt_yen(r.equity_start)}"
                f" | {_fmt_yen(r.equity_end)} | {_fmt_return(r.weekly_return)}"
                f" | {_fmt_return(r.max_drawdown)} | {r.win_days} |"
            )
    else:  # monthly
        lines += [
            "## 月次明細",
            "",
            "| 月 | 営業日数 | 期首資産 | 期末資産 | 月次リターン | 最大DD | 勝ち日数 |",
            "|---|---|---|---|---|---|---|",
        ]
        for r in report.rows:
            lines.append(
                f"| {r.month_label} | {r.trading_days} | {_fmt_yen(r.equity_start)}"
                f" | {_fmt_yen(r.equity_end)} | {_fmt_return(r.monthly_return)}"
                f" | {_fmt_return(r.max_drawdown)} | {r.win_days} |"
            )

    lines.append("")
    return "\n".join(lines)


def save_report(
    report: PerformanceReport,
    output_dir: Path | str | None = None,
) -> Path:
    """artifacts/performance/{env}/{report_type}/{period}/report.md に保存する。

    period:
      daily   → report.to_date (YYYY-MM-DD)
      weekly  → rows[-1].week_label (YYYY-Www)
      monthly → rows[-1].month_label (YYYY-MM)
      rows が空の場合は report.to_date を使用。
    """
    base = Path(output_dir) if output_dir else Path("artifacts") / "performance"

    if report.report_type == "weekly" and report.rows:
        period = report.rows[-1].week_label
    elif report.report_type == "monthly" and report.rows:
        period = report.rows[-1].month_label
    else:
        period = report.to_date  # daily またはフォールバック

    run_dir = base / report.env / report.report_type / period
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    return run_dir
