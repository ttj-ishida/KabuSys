"""Position Reconciliation View レポート生成モジュール。

DB上のローカル推定ポジション（注文履歴から集計）と証券口座（kabuステーション）のポジションを
銘柄単位で突き合わせ、CLEAN / DISCREPANCY ステータスと全銘柄一覧を出力する。
DB 参照は collect_position_snapshot() のみ。それ以外の関数はすべて純粋関数。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

STATUS_CLEAN = "CLEAN"
STATUS_DISCREPANCY = "DISCREPANCY"
ENTRY_MATCH = "MATCH"
ENTRY_MISMATCH = "MISMATCH"


@dataclass
class PositionEntry:
    code: str
    broker_qty: int  # ブローカー側保有数量（未保有なら 0）
    local_qty: int  # ローカルDB推定数量（Filled/PartialFill の net qty）
    diff: int  # broker_qty - local_qty（0 なら一致）
    status: str  # "MATCH" / "MISMATCH"


@dataclass
class PositionReconciliationReport:
    report_date: str  # ISO date（対象日 YYYY-MM-DD）
    generated_at: str  # ISO 8601 UTC タイムスタンプ
    status: str  # "CLEAN" / "DISCREPANCY"
    total_count: int  # union(broker, local) の銘柄数
    match_count: int  # diff == 0 の銘柄数
    mismatch_count: int  # diff != 0 の銘柄数
    positions: list[dict]  # PositionEntry の dict 化リスト
    warnings: list[str]


def collect_position_snapshot(broker, repo) -> list[PositionEntry]:
    """ブローカーAPIとOrderRepositoryからポジションを比較して返す。

    ブローカー側は get_positions()、ローカル側は list_active() の
    Filled / PartialFill 注文から net qty を集計する。
    結果は code 昇順でソートして返す。
    """
    from kabusys.execution.order_record import OrderState

    broker_map: dict[str, int] = {}
    for p in broker.get_positions():
        broker_map[p.code] = broker_map.get(p.code, 0) + p.qty

    local_map: dict[str, int] = {}
    for record in repo.list_active():
        if record.state not in {OrderState.Filled, OrderState.PartialFill}:
            continue
        side = record.side.lower()
        if side == "buy":
            local_map[record.code] = local_map.get(record.code, 0) + record.filled_qty
        elif side == "sell":
            local_map[record.code] = local_map.get(record.code, 0) - record.filled_qty

    entries: list[PositionEntry] = []
    for code in sorted(set(broker_map) | set(local_map)):
        broker_qty = broker_map.get(code, 0)
        local_qty = local_map.get(code, 0)
        diff = broker_qty - local_qty
        entries.append(
            PositionEntry(
                code=code,
                broker_qty=broker_qty,
                local_qty=local_qty,
                diff=diff,
                status=ENTRY_MATCH if diff == 0 else ENTRY_MISMATCH,
            )
        )
    return entries


def _generate_warnings(entries: list[PositionEntry]) -> list[str]:
    warnings: list[str] = []
    for e in entries:
        if e.status == ENTRY_MISMATCH:
            sign = "+" if e.diff > 0 else ""
            warnings.append(
                f"code={e.code}: broker={e.broker_qty}株 / local={e.local_qty}株"
                f" (diff={sign}{e.diff})"
            )
    return warnings


def build_report(
    entries: list[PositionEntry],
    *,
    report_date: date,
) -> PositionReconciliationReport:
    """entries リストから PositionReconciliationReport を構築する（純粋関数）。"""
    match_count = sum(1 for e in entries if e.status == ENTRY_MATCH)
    mismatch_count = sum(1 for e in entries if e.status == ENTRY_MISMATCH)
    total_count = len(entries)
    warnings = _generate_warnings(entries)
    status = STATUS_CLEAN if mismatch_count == 0 else STATUS_DISCREPANCY
    return PositionReconciliationReport(
        report_date=report_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=status,
        total_count=total_count,
        match_count=match_count,
        mismatch_count=mismatch_count,
        positions=[asdict(e) for e in entries],
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------


def format_cli_summary(report: PositionReconciliationReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 56
    thin = "-" * 56
    lines = [
        f"\n{sep}",
        f"  Position Reconciliation  {report.report_date}",
        f"  Status : {report.status}",
        f"{sep}",
        f"    total     : {report.total_count:>6}",
        f"    match     : {report.match_count:>6}",
        f"    mismatch  : {report.mismatch_count:>6}",
    ]
    if report.positions:
        lines.append(thin)
        lines.append(
            f"  {'':3}{'Code':<8}  {'Broker':>8}  {'Local':>8}  {'Diff':>6}  Status"
        )
        lines.append(f"  {'':3}{'-' * 8}  {'-' * 8}  {'-' * 8}  {'-' * 6}  {'-' * 10}")
        for p in report.positions:
            mark = "[!]" if p["status"] == ENTRY_MISMATCH else "   "
            sign = "+" if p["diff"] > 0 else ""
            diff_str = f"{sign}{p['diff']}" if p["diff"] != 0 else "0"
            lines.append(
                f"  {mark} {p['code']:<8}  {p['broker_qty']:>8}"
                f"  {p['local_qty']:>8}  {diff_str:>6}  {p['status']}"
            )
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def format_json(report: PositionReconciliationReport) -> str:
    """全フィールドを含む JSON 文字列を返す。"""
    return json.dumps(asdict(report), ensure_ascii=False, indent=2)


def format_markdown(report: PositionReconciliationReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = [
        "# Position Reconciliation",
        "",
        "## 1. Overview",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| 対象日 | {report.report_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **ステータス** | **{report.status}** |",
        f"| 総銘柄数 | {report.total_count} |",
        f"| 一致 | {report.match_count} |",
        f"| 不一致 | {report.mismatch_count} |",
        "",
    ]

    sec = 2
    if report.positions:
        lines += [
            f"## {sec}. ポジション一覧",
            "",
            "| 銘柄コード | Broker | Local | Diff | 状態 |",
            "|-----------|--------|-------|------|------|",
        ]
        for p in report.positions:
            sign = "+" if p["diff"] > 0 else ""
            diff_str = f"{sign}{p['diff']}" if p["diff"] != 0 else "0"
            mark = "⚠️ " if p["status"] == ENTRY_MISMATCH else ""
            lines.append(
                f"| {mark}{p['code']} | {p['broker_qty']}"
                f" | {p['local_qty']} | {diff_str} | {p['status']} |"
            )
        lines.append("")
        sec += 1

    if report.warnings:
        lines += [f"## {sec}. Warnings", ""]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")
        sec += 1

    lines += [f"## {sec}. Final Decision", ""]
    if report.status == STATUS_CLEAN:
        lines += [
            f"**{STATUS_CLEAN}** — 全銘柄のポジションが一致しています。",
            "",
            "- 執行エンジンを安全に起動できます。",
        ]
    else:
        lines += [
            f"**{STATUS_DISCREPANCY}** — ポジションに差分が検出されました。",
            "",
            "- 上記 Warnings を確認し、手動調整を行ってください。",
            "- 差分が解消されるまで執行エンジンの起動を控えることを推奨します。",
        ]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: PositionReconciliationReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/position_reconciliation/{report_date}/ に保存する。

    保存ファイル:
        summary.json    全指標 JSON
        report.md       Markdown レポート
        warnings.json   警告リスト JSON

    同一 report_date で再実行した場合は上書き（exist_ok=True）。
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report.report_date):
        raise ValueError(f"Invalid report_date: {report.report_date!r}")
    try:
        date.fromisoformat(report.report_date)
    except ValueError:
        raise ValueError(
            f"Invalid report_date (not a valid calendar date): {report.report_date!r}"
        )
    base = (
        Path(output_dir)
        if output_dir
        else Path("artifacts") / "position_reconciliation"
    )
    run_dir = base / report.report_date
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / "warnings.json").write_text(
        json.dumps(report.warnings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return run_dir
