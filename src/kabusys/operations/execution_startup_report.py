"""Execution Startup Summary レポート生成モジュール。

Execution 起動直後に READY / READY_WITH_WARNINGS / BLOCKED の判定を含む
サマリを生成する。DB への参照は行わず、呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from kabusys.execution.reconciler import ReconcileResult

STATUS_READY = "READY"
STATUS_READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class ExecutionStartupReport:
    startup_date: str  # ISO date（起動日）
    generated_at: str  # ISO 8601 UTC
    status: str  # READY / READY_WITH_WARNINGS / BLOCKED
    orders_synced: int
    orders_no_status: int
    position_discrepancies: list[dict]  # PositionDiscrepancy の dict 表現
    warnings: list[str]


def _determine_status(
    *,
    orders_no_status: int,
    position_discrepancies_count: int,
) -> str:
    """READY / READY_WITH_WARNINGS / BLOCKED を判定する。

    BLOCKED: orders_no_status > 0
      → 注文ステータス不明は二重発注・未約定放置のリスクがあり執行継続不可
    READY_WITH_WARNINGS: position_discrepancies_count > 0
      → DB とブローカー間で数量差分あり。要確認だが執行は継続可能
    READY: それ以外
    """
    if orders_no_status > 0:
        return STATUS_BLOCKED
    if position_discrepancies_count > 0:
        return STATUS_READY_WITH_WARNINGS
    return STATUS_READY


def _generate_warnings(
    *,
    orders_no_status: int,
    position_discrepancies: list[dict],
) -> list[str]:
    """警告メッセージのリストを生成する。"""
    warnings: list[str] = []
    if orders_no_status > 0:
        warnings.append(
            f"ステータス不明の注文が {orders_no_status} 件あります"
            "（二重発注・未約定放置のリスク。手動確認が必要）"
        )
    for d in position_discrepancies:
        warnings.append(
            f"ポジション差分: {d['code']}"
            f" broker={d['broker_qty']} local={d['local_qty']} diff={d['diff']:+d}"
        )
    return warnings


def build_report(
    reconcile_result: ReconcileResult,
    *,
    startup_date: date,
) -> ExecutionStartupReport:
    """ReconcileResult から ExecutionStartupReport を構築する。

    Args:
        reconcile_result: reconciler.run() の戻り値。
        startup_date:     起動日（キーワード引数）。

    Returns:
        ExecutionStartupReport インスタンス。
    """
    discrepancies = [
        {
            "code": d.code,
            "broker_qty": d.broker_qty,
            "local_qty": d.local_qty,
            "diff": d.diff,
        }
        for d in reconcile_result.position_discrepancies
    ]
    warnings = _generate_warnings(
        orders_no_status=reconcile_result.orders_no_status,
        position_discrepancies=discrepancies,
    )
    status = _determine_status(
        orders_no_status=reconcile_result.orders_no_status,
        position_discrepancies_count=len(discrepancies),
    )
    return ExecutionStartupReport(
        startup_date=startup_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=status,
        orders_synced=reconcile_result.orders_synced,
        orders_no_status=reconcile_result.orders_no_status,
        position_discrepancies=discrepancies,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------


def format_cli_summary(report: ExecutionStartupReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 52
    thin = "-" * 52
    lines = [
        f"\n{sep}",
        f"  Execution Startup Summary  {report.startup_date}",
        f"  Status : {report.status}",
        f"{sep}",
        "  Reconciliation:",
        f"    orders_synced      : {report.orders_synced:>6}",
        f"    orders_no_status   : {report.orders_no_status:>6}",
        f"    position_discrepancies: {len(report.position_discrepancies)} 件",
    ]
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def format_json(report: ExecutionStartupReport) -> str:
    """全指標を含む JSON 文字列を返す。

    Note: ExecutionStartupReport のフィールドは str / int / list[dict] のみで
    構成されるため _to_serializable は不要。date/datetime フィールドを追加する
    場合はこの前提を再確認すること。
    """
    return json.dumps(asdict(report), ensure_ascii=False, indent=2)


def format_markdown(report: ExecutionStartupReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = [
        "# Execution Startup Summary",
        "",
        "## 1. Overview",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| 起動日 | {report.startup_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **最終判定** | **{report.status}** |",
        "",
        "## 2. Reconciliation",
        "",
        "| 項目 | 件数 |",
        "|-----|-----|",
        f"| orders_synced | {report.orders_synced} |",
        f"| orders_no_status | {report.orders_no_status} |",
        f"| position_discrepancies | {len(report.position_discrepancies)} |",
        "",
    ]

    if report.position_discrepancies:
        lines += [
            "### Position Discrepancies",
            "",
            "| 銘柄コード | broker_qty | local_qty | diff |",
            "|-----------|-----------|----------|------|",
        ]
        for d in report.position_discrepancies:
            lines.append(
                f"| {d['code']} | {d['broker_qty']} | {d['local_qty']} | {d['diff']:+d} |"
            )
        lines.append("")

    sec = 3
    if report.warnings:
        lines += [
            f"## {sec}. Warnings",
            "",
        ]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")
        sec += 1

    lines += [f"## {sec}. Final Decision", ""]
    if report.status == STATUS_READY:
        lines += [
            f"**{STATUS_READY}** — 発注ループを継続できます。",
            "",
            "- リコンシリエーション正常完了。",
            "- 特段の対応は不要です。",
        ]
    elif report.status == STATUS_READY_WITH_WARNINGS:
        lines += [
            f"**{STATUS_READY_WITH_WARNINGS}** — ポジション差分を確認した上で、執行を継続してください。",
            "",
            "- 執行は継続可能ですが、上記 Warnings に記載の差分銘柄を確認してください。",
        ]
    else:
        lines += [
            f"**{STATUS_BLOCKED}** — 注文ステータス不明のため執行継続 **不可**。",
            "",
            "- 上記 Warnings に記載の注文を手動確認し、問題を解消してから再起動してください。",
        ]
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: ExecutionStartupReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/execution_startup/{startup_date}/ に保存する。

    保存ファイル:
        summary.json    全指標 JSON
        report.md       Markdown レポート
        warnings.json   警告リスト JSON

    同一 startup_date で再実行した場合は既存ファイルを上書きする（exist_ok=True）。

    Returns:
        保存先ディレクトリのパス。
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report.startup_date):
        raise ValueError(f"Invalid startup_date: {report.startup_date!r}")
    try:
        date.fromisoformat(report.startup_date)
    except ValueError:
        raise ValueError(
            f"Invalid startup_date (not a valid calendar date): {report.startup_date!r}"
        )
    base = Path(output_dir) if output_dir else Path("artifacts") / "execution_startup"
    run_dir = base / report.startup_date
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / "warnings.json").write_text(
        json.dumps(report.warnings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return run_dir
