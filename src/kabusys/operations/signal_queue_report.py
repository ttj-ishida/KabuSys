"""Signal Queue Confirmation View レポート生成モジュール。

翌営業日の発注予定シグナルを DuckDB の signals / portfolio_targets テーブルから読み取り、
READY / EMPTY ステータスと銘柄一覧を出力する。
DB 参照は collect_signals() のみ。それ以外の関数はすべて純粋関数。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

STATUS_READY = "READY"
STATUS_EMPTY = "EMPTY"


@dataclass
class SignalQueueReport:
    report_date: str  # ISO date（対象日）
    generated_at: str  # ISO 8601 UTC
    status: str  # READY / EMPTY
    total_count: int  # シグナル総数
    buy_count: int  # BUY シグナル数
    sell_count: int  # SELL シグナル数
    signals: list[dict]  # [{code, side, target_size, target_weight, signal_rank}]
    warnings: list[str]


def collect_signals(conn, target_date: date) -> list[dict]:
    """DuckDB から対象日のシグナルを取得する。

    signals LEFT JOIN portfolio_targets で target_size / target_weight を付与し、
    signal_rank 昇順・side 昇順でソートして返す。
    """
    rows = conn.execute(
        """
        SELECT s.code, s.side, pt.target_size, pt.target_weight, s.signal_rank
        FROM signals s
        LEFT JOIN portfolio_targets pt
               ON s.date = pt.date AND s.code = pt.code
        WHERE s.date = ?
        ORDER BY s.signal_rank ASC NULLS LAST, s.side
        """,
        [target_date],
    ).fetchall()
    return [
        {
            "code": row[0],
            "side": row[1],
            "target_size": row[2],
            "target_weight": row[3],
            "signal_rank": row[4],
        }
        for row in rows
    ]


def _generate_warnings(*, signals: list[dict], total_count: int) -> list[str]:
    warnings: list[str] = []
    if total_count == 0:
        warnings.append("翌営業日のシグナルがありません（自動執行は行われません）")
    buy_no_size = [
        s["code"] for s in signals if s["side"] == "buy" and s["target_size"] is None
    ]
    if buy_no_size:
        warnings.append(f"target_size 未設定の BUY シグナル: {', '.join(buy_no_size)}")
    return warnings


def build_report(
    signals: list[dict],
    *,
    report_date: date,
) -> SignalQueueReport:
    """signals リストから SignalQueueReport を構築する（純粋関数）。"""
    buy_count = sum(1 for s in signals if s["side"] == "buy")
    sell_count = sum(1 for s in signals if s["side"] == "sell")
    total_count = len(signals)
    warnings = _generate_warnings(signals=signals, total_count=total_count)
    status = STATUS_READY if total_count > 0 else STATUS_EMPTY
    return SignalQueueReport(
        report_date=report_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=status,
        total_count=total_count,
        buy_count=buy_count,
        sell_count=sell_count,
        signals=signals,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------


def format_cli_summary(report: SignalQueueReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 52
    thin = "-" * 52
    lines = [
        f"\n{sep}",
        f"  Signal Queue Confirmation  {report.report_date}",
        f"  Status : {report.status}",
        f"{sep}",
        f"    total  : {report.total_count:>6}",
        f"    buy    : {report.buy_count:>6}",
        f"    sell   : {report.sell_count:>6}",
    ]
    if report.signals:
        lines.append(thin)
        lines.append(
            f"  {'Code':<8}  {'Side':<5}  {'Shares':>8}  {'Weight':>8}  {'Rank':>5}"
        )
        lines.append(f"  {'-' * 8}  {'-' * 5}  {'-' * 8}  {'-' * 8}  {'-' * 5}")
        for s in report.signals:
            weight_str = (
                f"{s['target_weight'] * 100:.1f}%"
                if s["target_weight"] is not None
                else "N/A"
            )
            size_str = str(s["target_size"]) if s["target_size"] is not None else "N/A"
            rank_str = str(s["signal_rank"]) if s["signal_rank"] is not None else "-"
            lines.append(
                f"  {s['code']:<8}  {s['side']:<5}  {size_str:>8}  {weight_str:>8}  {rank_str:>5}"
            )
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def format_json(report: SignalQueueReport) -> str:
    """全フィールドを含む JSON 文字列を返す。"""
    return json.dumps(asdict(report), ensure_ascii=False, indent=2)


def format_markdown(report: SignalQueueReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = [
        "# Signal Queue Confirmation",
        "",
        "## 1. Overview",
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| 対象日 | {report.report_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **ステータス** | **{report.status}** |",
        f"| total | {report.total_count} |",
        f"| BUY | {report.buy_count} |",
        f"| SELL | {report.sell_count} |",
        "",
    ]

    sec = 2
    if report.signals:
        lines += [
            f"## {sec}. Signal 一覧",
            "",
            "| 銘柄コード | 方向 | 株数 | 目標ウェイト | ランク |",
            "|-----------|------|------|------------|-------|",
        ]
        for s in report.signals:
            weight_str = (
                f"{s['target_weight'] * 100:.1f}%"
                if s["target_weight"] is not None
                else "N/A"
            )
            size_str = str(s["target_size"]) if s["target_size"] is not None else "N/A"
            rank_str = str(s["signal_rank"]) if s["signal_rank"] is not None else "-"
            lines.append(
                f"| {s['code']} | {s['side']} | {size_str} | {weight_str} | {rank_str} |"
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
    if report.status == STATUS_READY:
        lines += [
            f"**{STATUS_READY}** — 発注シグナルが存在します。Execution 起動後に自動執行されます。",
            "",
            "- 上記一覧を確認し、意図しない銘柄・方向がある場合は"
            " `data/stop_requested.flag` を作成して自動執行を停止してください。",
        ]
    else:
        lines += [
            f"**{STATUS_EMPTY}** — 翌営業日のシグナルがありません。",
            "",
            "- 夜間バッチが正常に完了しているか確認してください。",
        ]
    lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: SignalQueueReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/signal_queue/{report_date}/ に保存する。

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
    base = Path(output_dir) if output_dir else Path("artifacts") / "signal_queue"
    run_dir = base / report.report_date
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / "warnings.json").write_text(
        json.dumps(report.warnings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return run_dir
