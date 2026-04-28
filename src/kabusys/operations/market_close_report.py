"""
Market Close Summary レポート生成モジュール。

引け後（15:30 頃）に「今日の運用が正常に締まったか」を確認し、
夜間バッチへ進んでよいかを OK / BLOCKED で判定する。
DB への参照は行わず、呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

STATUS_OK = "OK"
STATUS_BLOCKED = "BLOCKED"

_STATUS_EMOJI = {
    STATUS_OK: "✅",
    STATUS_BLOCKED: "🚫",
}

_CHECK_STATUS_LABEL = {
    "ok": "ok  ",
    "failed": "FAIL",
}


@dataclass
class CheckItem:
    """1 チェック項目の結果。"""

    name: str
    status: str  # "ok" | "failed"
    detail: str


@dataclass
class MarketCloseReport:
    """Market Close Summary レポート全体。"""

    report_date: str  # ISO date（YYYY-MM-DD）
    generated_at: str  # ISO 8601 UTC
    status: str  # "OK" / "BLOCKED"
    checks: list[CheckItem]
    summary: dict
    warnings: list[str]


def _determine_status(
    *,
    signal_pending_count: int,
    positions_updated: bool,
    performance_recorded: bool,
) -> str:
    if signal_pending_count > 0 or not positions_updated or not performance_recorded:
        return STATUS_BLOCKED
    return STATUS_OK


def _generate_warnings(
    *,
    signal_pending_count: int,
    positions_updated: bool,
    performance_recorded: bool,
) -> list[str]:
    warnings: list[str] = []
    if signal_pending_count > 0:
        warnings.append(
            f"signal_queue に本日の pending シグナルが {signal_pending_count} 件残っています"
        )
    if not positions_updated:
        warnings.append("positions に当日分が記録されていません")
    if not performance_recorded:
        warnings.append("portfolio_performance に当日分が記録されていません")
    return warnings


def _build_check_items(
    *,
    signal_pending_count: int,
    positions_updated: bool,
    performance_recorded: bool,
) -> list[CheckItem]:
    return [
        CheckItem(
            name="signal_queue",
            status="ok" if signal_pending_count == 0 else "failed",
            detail=(
                "pending: 0 件（全シグナル処理済み）"
                if signal_pending_count == 0
                else f"pending: {signal_pending_count} 件（未処理シグナルあり）"
            ),
        ),
        CheckItem(
            name="positions",
            status="ok" if positions_updated else "failed",
            detail=(
                "positions: 当日分 更新済み"
                if positions_updated
                else "positions: 当日分 未更新"
            ),
        ),
        CheckItem(
            name="portfolio_performance",
            status="ok" if performance_recorded else "failed",
            detail=(
                "portfolio_performance: 当日分 記録済み"
                if performance_recorded
                else "portfolio_performance: 当日分 未記録"
            ),
        ),
    ]


def build_report(
    *,
    report_date: date,
    signal_pending_count: int,
    positions_updated: bool,
    performance_recorded: bool,
    filled_count: int,
    daily_return: float | None,
    equity_today: float | None,
    equity_prev: float | None,
) -> MarketCloseReport:
    """MarketCloseReport を構築する。"""
    kwargs = dict(
        signal_pending_count=signal_pending_count,
        positions_updated=positions_updated,
        performance_recorded=performance_recorded,
    )
    pnl_amount = (
        equity_today - equity_prev
        if equity_today is not None and equity_prev is not None
        else None
    )
    return MarketCloseReport(
        report_date=report_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=_determine_status(**kwargs),
        checks=_build_check_items(**kwargs),
        summary={
            "filled_count": filled_count,
            "daily_return": daily_return,
            "pnl_amount": pnl_amount,
            "equity_today": equity_today,
        },
        warnings=_generate_warnings(**kwargs),
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------


def _fmt_return(v: float | None) -> str:
    if v is None:
        return "N/A"
    sign = "+" if v > 0 else ""
    return f"{sign}{v:.2%}"


def _fmt_yen(v: float | None) -> str:
    if v is None:
        return "N/A"
    sign = "+" if v > 0 else ""
    return f"{sign}¥{int(v):,}"


def format_cli_summary(report: MarketCloseReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 52
    thin = "-" * 52
    emoji = _STATUS_EMOJI.get(report.status, "")
    s = report.summary
    lines = [
        f"\n{sep}",
        f"  Market Close Summary  {report.report_date}",
        f"  Status : {emoji} {report.status}",
        f"{sep}",
        "  Checks:",
    ]
    for c in report.checks:
        label = _CHECK_STATUS_LABEL.get(c.status, c.status.upper())
        lines.append(f"    [{label}] {c.name:<22} {c.detail}")
    lines += [
        thin,
        "  Summary:",
        f"    約定件数    : {s['filled_count']} 件",
        f"    日次リターン : {_fmt_return(s['daily_return'])}",
        f"    当日損益額  : {_fmt_yen(s['pnl_amount'])}",
        f"    期末総資産  : {_fmt_yen(s['equity_today'])}",
    ]
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def _to_serializable(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(i) for i in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    return obj


def format_json(report: MarketCloseReport) -> str:
    """全フィールドを含む JSON 文字列を返す。"""
    return json.dumps(_to_serializable(asdict(report)), ensure_ascii=False, indent=2)


def format_markdown(report: MarketCloseReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = []
    sec = 0

    def _section(title: str) -> str:
        nonlocal sec
        sec += 1
        return f"## {sec}. {title}"

    emoji = _STATUS_EMOJI.get(report.status, "")
    s = report.summary

    lines += [
        "# Market Close Summary",
        "",
        _section("Overview"),
        "",
        "| 項目 | 値 |",
        "|-----|---|",
        f"| 実行日 | {report.report_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **最終判定** | **{emoji} {report.status}** |",
        "",
        _section("Checks"),
        "",
        "| チェック項目 | ステータス | 詳細 |",
        "|------------|-----------|------|",
    ]
    for c in report.checks:
        lines.append(f"| {c.name} | {c.status} | {c.detail} |")
    lines += [
        "",
        _section("Summary"),
        "",
        "| 項目 | 値 |",
        "|-----|---|",
        f"| 約定件数 | {s['filled_count']} 件 |",
        f"| 日次リターン | {_fmt_return(s['daily_return'])} |",
        f"| 当日損益額 | {_fmt_yen(s['pnl_amount'])} |",
        f"| 期末総資産 | {_fmt_yen(s['equity_today'])} |",
        "",
    ]
    if report.warnings:
        lines += [_section("Warnings"), ""]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    lines += [_section("Final Decision"), ""]
    if report.status == STATUS_OK:
        lines += [
            f"**{STATUS_OK}** — 夜間バッチへ進んでください。",
            "",
            "- 全チェック項目が正常です。",
        ]
    else:
        lines += [
            f"**{STATUS_BLOCKED}** — 夜間バッチへ **進まないでください**。",
            "",
            "- 上記 Warnings を確認し、問題を解消してから再実行してください。",
        ]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: MarketCloseReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/market_close/{report_date}/ に保存する。"""
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report.report_date):
        raise ValueError(f"Invalid report_date: {report.report_date!r}")
    try:
        date.fromisoformat(report.report_date)
    except ValueError:
        raise ValueError(f"Invalid report_date: {report.report_date!r}")
    base = Path(output_dir) if output_dir else Path("artifacts") / "market_close"
    run_dir = base / report.report_date
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / "warnings.json").write_text(
        json.dumps(report.warnings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return run_dir
