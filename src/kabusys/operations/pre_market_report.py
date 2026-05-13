"""
Pre-Market Report 生成モジュール。

毎朝 08:00 頃、運用開始可否を READY / READY_WITH_WARNINGS / BLOCKED で判定する。
DB への参照は行わず、呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

STATUS_READY = "READY"
STATUS_READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class CheckItem:
    """1 チェック項目の結果。"""

    name: str
    status: str  # "ok" | "warning" | "failed"
    detail: str


@dataclass
class PreMarketReport:
    """Pre-Market Report 全体。"""

    report_date: str  # ISO date
    generated_at: str  # ISO 8601 UTC
    status: str  # READY / READY_WITH_WARNINGS / BLOCKED
    checks: list[CheckItem]
    warnings: list[str]
    signal_queue_pending: int


def _determine_status(
    *,
    data_freshness_ok: bool,
    signal_queue_pending: int,
    position_count: int,
    stop_flag_exists: bool,
    task_scheduler_ready: bool,
) -> str:
    """READY / READY_WITH_WARNINGS / BLOCKED を判定する。

    BLOCKED 条件（いずれかが真）:
      - signal_queue_pending == 0（本日の pending シグナルがない）
      - stop_flag_exists == True（停止フラグが立っている）
      - task_scheduler_ready == False（KabuSys_ExecutionStart が Ready でない）

    READY_WITH_WARNINGS 条件（BLOCKED でなく、いずれかが真）:
      - data_freshness_ok == False（prices_daily が古い）

    それ以外: READY
    """
    if signal_queue_pending == 0 or stop_flag_exists or not task_scheduler_ready:
        return STATUS_BLOCKED

    if not data_freshness_ok:
        return STATUS_READY_WITH_WARNINGS

    return STATUS_READY


def _generate_warnings(
    *,
    data_freshness_ok: bool,
    signal_queue_pending: int,
    position_count: int,
    stop_flag_exists: bool,
    task_scheduler_ready: bool,
) -> list[str]:
    """警告メッセージのリストを生成する。"""
    warnings: list[str] = []

    if signal_queue_pending == 0:
        warnings.append("signal_queue に本日の pending シグナルがありません（自動執行不可）")
    if stop_flag_exists:
        warnings.append("停止フラグ（stop_requested.flag）が存在します（自動執行不可）")
    if not task_scheduler_ready:
        warnings.append("Task Scheduler の KabuSys_ExecutionStart が Ready 状態ではありません")
    if not data_freshness_ok:
        warnings.append("prices_daily の最終更新日が直近営業日と一致しません（データが古い可能性）")

    return warnings


def _build_check_items(
    *,
    data_freshness_ok: bool,
    signal_queue_pending: int,
    position_count: int,
    stop_flag_exists: bool,
    task_scheduler_ready: bool,
) -> list[CheckItem]:
    return [
        CheckItem(
            name="data_freshness",
            status="ok" if data_freshness_ok else "warning",
            detail="prices_daily 最終更新日: 直近営業日"
            if data_freshness_ok
            else "prices_daily が古い（前営業日分が未反映の可能性）",
        ),
        CheckItem(
            name="signal_queue",
            status="ok" if signal_queue_pending > 0 else "failed",
            detail=f"pending シグナル: {signal_queue_pending} 件",
        ),
        CheckItem(
            name="position_count",
            status="ok",
            detail=f"DB ポジション: {position_count} 銘柄（詳細は 08:30 リコンシリエーションで確認）",
        ),
        CheckItem(
            name="stop_flag",
            status="failed" if stop_flag_exists else "ok",
            detail="停止フラグあり（stop_requested.flag 存在）"
            if stop_flag_exists
            else "停止フラグなし",
        ),
        CheckItem(
            name="task_scheduler",
            status="ok" if task_scheduler_ready else "failed",
            detail="KabuSys_ExecutionStart: Ready"
            if task_scheduler_ready
            else "KabuSys_ExecutionStart: Ready でない（要確認）",
        ),
    ]


def build_report(
    *,
    report_date: date,
    data_freshness_ok: bool,
    signal_queue_pending: int,
    position_count: int,
    stop_flag_exists: bool,
    task_scheduler_ready: bool,
) -> PreMarketReport:
    """PreMarketReport を構築する。"""
    kwargs = dict(
        data_freshness_ok=data_freshness_ok,
        signal_queue_pending=signal_queue_pending,
        position_count=position_count,
        stop_flag_exists=stop_flag_exists,
        task_scheduler_ready=task_scheduler_ready,
    )
    return PreMarketReport(
        report_date=report_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=_determine_status(**kwargs),
        checks=_build_check_items(**kwargs),
        warnings=_generate_warnings(**kwargs),
        signal_queue_pending=signal_queue_pending,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------

_STATUS_EMOJI = {
    STATUS_READY: "✅",
    STATUS_READY_WITH_WARNINGS: "⚠️",
    STATUS_BLOCKED: "🚫",
}

_CHECK_STATUS_LABEL = {
    "ok": "OK  ",
    "warning": "WARN",
    "failed": "FAIL",
}


def format_cli_summary(report: PreMarketReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 52
    thin = "-" * 52
    emoji = _STATUS_EMOJI.get(report.status, "")
    lines = [
        f"\n{sep}",
        f"  Pre-Market Report  {report.report_date}",
        f"  Status : {emoji} {report.status}",
        f"{sep}",
        "  Checks:",
    ]
    for c in report.checks:
        label = _CHECK_STATUS_LABEL.get(c.status, c.status.upper())
        lines.append(f"    [{label}] {c.name:<20} {c.detail}")
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


def format_json(report: PreMarketReport) -> str:
    """全指標を含む JSON 文字列を返す。"""
    return json.dumps(_to_serializable(asdict(report)), ensure_ascii=False, indent=2)


def format_markdown(report: PreMarketReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = []
    sec = 0

    def _section(title: str) -> str:
        nonlocal sec
        sec += 1
        return f"## {sec}. {title}"

    emoji = _STATUS_EMOJI.get(report.status, "")

    lines += [
        "# Pre-Market Report",
        "",
        _section("Overview"),
        "",
        "| 項目 | 値 |",
        "|-----|---|",
        f"| 実行日 | {report.report_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **最終判定** | **{emoji} {report.status}** |",
        "",
    ]

    lines += [
        _section("Checks"),
        "",
        "| チェック項目 | ステータス | 詳細 |",
        "|------------|-----------|------|",
    ]
    for c in report.checks:
        lines.append(f"| {c.name} | {c.status} | {c.detail} |")
    lines.append("")

    if report.warnings:
        lines += [_section("Warnings"), ""]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    lines += [_section("Final Decision"), ""]
    if report.status == STATUS_READY:
        lines += [
            f"**{STATUS_READY}** — 自動執行を開始できます。",
            "",
            "- 全チェック項目が正常です。",
            "- 08:30 の自動執行起動を待ってください。",
        ]
    elif report.status == STATUS_READY_WITH_WARNINGS:
        lines += [
            f"**{STATUS_READY_WITH_WARNINGS}** — 警告を確認した上で、執行開始を判断してください。",
            "",
            "- 基本的な準備は整っていますが、警告があります。",
            "- 上記 Warnings を確認し、問題がなければ自動執行を継続できます。",
        ]
    else:
        lines += [
            f"**{STATUS_BLOCKED}** — 自動執行を **開始しないでください**。",
            "",
            "- 上記 Warnings を確認し、問題を解消してから再実行してください。",
        ]
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: PreMarketReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/pre_market/{report_date}/ に保存する。

    Returns:
        保存先ディレクトリのパス。
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report.report_date):
        raise ValueError(f"Invalid report_date: {report.report_date!r}")
    try:
        date.fromisoformat(report.report_date)
    except ValueError:
        raise ValueError(f"Invalid report_date (not a valid calendar date): {report.report_date!r}")
    base = Path(output_dir) if output_dir else Path("artifacts") / "pre_market"
    run_dir = base / report.report_date
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / "warnings.json").write_text(
        json.dumps(report.warnings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return run_dir
