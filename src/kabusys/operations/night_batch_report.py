"""
夜間バッチ結果確認レポート生成モジュール。

夜間バッチ（21:00頃）完了後に READY / READY_WITH_WARNINGS / BLOCKED
の最終判定を含むレポートを生成する。DB への参照は行わず、
呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path

# 必須ジョブ一覧（いずれかが failed → BLOCKED）
MANDATORY_JOBS: list[str] = [
    "data_update_job",
    "feature_generation_job",
    "ai_analysis_job",
    "strategy_signal_job",
    "portfolio_construction_job",
]

STATUS_READY = "READY"
STATUS_READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
STATUS_BLOCKED = "BLOCKED"


@dataclass
class JobRunResult:
    """1ジョブの実行結果。"""

    job_name: str
    status: str  # success / warning / failed / skipped
    started_at: datetime
    finished_at: datetime
    duration_sec: float
    updated_rows: dict[str, int]
    warnings: list[str]
    errors: list[str]


@dataclass
class UpdateCounts:
    """各テーブルへの更新件数。"""

    prices_daily: int = 0
    news_articles: int = 0
    fundamentals: int = 0
    features: int = 0
    ai_scores: int = 0
    signals: int = 0
    signal_queue: int = 0


@dataclass
class NextDaySummary:
    """翌営業日の発注準備サマリ。"""

    buy_count: int = 0
    sell_count: int = 0
    target_symbols: int = 0
    expected_orders: int = 0


@dataclass
class NightBatchReport:
    """夜間バッチ結果確認レポート全体。"""

    run_date: str  # ISO date（バッチ実行日）
    target_date: str  # ISO date（対象取引日＝翌営業日）
    generated_at: str  # ISO 8601 UTC
    status: str  # READY / READY_WITH_WARNINGS / BLOCKED
    job_results: list[JobRunResult]
    update_counts: UpdateCounts
    next_day_summary: NextDaySummary
    warnings: list[str]


def _determine_status(
    job_results: list[JobRunResult],
    update_counts: UpdateCounts,
) -> str:
    """READY / READY_WITH_WARNINGS / BLOCKED を判定する。

    BLOCKED 条件（いずれかが真）:
      - 必須ジョブのいずれかが job_results に存在しない（未実行）
      - 必須ジョブのいずれかが failed または skipped
      - signal_queue == 0

    READY_WITH_WARNINGS 条件（BLOCKED でなく、いずれかが真）:
      - いずれかのジョブが status == "warning"
      - いずれかのジョブの warnings リストが空でない
      - 非必須ジョブのいずれかが skipped
      - signals == 0

    それ以外: READY
    """
    present = {j.job_name for j in job_results}
    has_missing_mandatory = any(name not in present for name in MANDATORY_JOBS)
    has_blocked_mandatory = any(
        j.job_name in MANDATORY_JOBS and j.status in ("failed", "skipped")
        for j in job_results
    )
    if (
        has_missing_mandatory
        or has_blocked_mandatory
        or update_counts.signal_queue == 0
    ):
        return STATUS_BLOCKED

    has_warning_status = any(j.status == "warning" for j in job_results)
    has_job_warnings = any(j.warnings for j in job_results)
    has_nonmandatory_skipped = any(
        j.job_name not in MANDATORY_JOBS and j.status == "skipped" for j in job_results
    )
    if (
        has_warning_status
        or has_job_warnings
        or has_nonmandatory_skipped
        or update_counts.signals == 0
    ):
        return STATUS_READY_WITH_WARNINGS

    return STATUS_READY


def _generate_warnings(
    job_results: list[JobRunResult],
    update_counts: UpdateCounts,
) -> list[str]:
    """警告メッセージのリストを生成する。"""
    warnings: list[str] = []

    present = {j.job_name for j in job_results}
    for name in MANDATORY_JOBS:
        if name not in present:
            warnings.append(f"必須ジョブが実行されませんでした（未実行）: {name}")

    for j in job_results:
        if j.job_name in MANDATORY_JOBS and j.status == "failed":
            warnings.append(f"必須ジョブが失敗しました: {j.job_name}")
        if j.job_name in MANDATORY_JOBS and j.status == "skipped":
            warnings.append(f"必須ジョブがスキップされました: {j.job_name}")
        if j.job_name not in MANDATORY_JOBS and j.status == "skipped":
            warnings.append(f"ジョブがスキップされました: {j.job_name}")
        if j.status == "warning":
            warnings.append(f"ジョブが警告で完了: {j.job_name}")
        warnings.extend(j.warnings)

    if update_counts.signals == 0:
        warnings.append("signals が生成されていません")
    if update_counts.signal_queue == 0:
        warnings.append("signal_queue が空です（翌営業日の自動執行は不可）")
    if update_counts.prices_daily == 0:
        warnings.append("prices_daily の更新件数が 0 件です")
    if update_counts.features == 0:
        warnings.append("features の更新件数が 0 件です")

    return warnings


def build_report(
    job_results: list[JobRunResult],
    update_counts: UpdateCounts,
    next_day_summary: NextDaySummary,
    *,
    run_date: date,
    target_date: date,
) -> NightBatchReport:
    """NightBatchReport を構築する。

    Args:
        job_results:      各ジョブの実行結果リスト。
        update_counts:    各テーブルへの更新件数。
        next_day_summary: 翌営業日の発注準備サマリ。
        run_date:         バッチ実行日（キーワード引数）。
        target_date:      対象取引日（キーワード引数）。

    Returns:
        NightBatchReport インスタンス。
    """
    warnings = _generate_warnings(job_results, update_counts)
    status = _determine_status(job_results, update_counts)
    return NightBatchReport(
        run_date=run_date.isoformat(),
        target_date=target_date.isoformat(),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        status=status,
        job_results=job_results,
        update_counts=update_counts,
        next_day_summary=next_day_summary,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# フォーマッター
# ---------------------------------------------------------------------------

_STATUS_LABEL: dict[str, str] = {
    "READY": "READY",
    "READY_WITH_WARNINGS": "READY_WITH_WARNINGS",
    "BLOCKED": "BLOCKED",
}

_JOB_STATUS_LABEL: dict[str, str] = {
    "success": "SUCCESS",
    "warning": "WARNING",
    "failed": "FAILED",
    "skipped": "SKIPPED",
}


def format_cli_summary(report: NightBatchReport) -> str:
    """CLI 表示用サマリ文字列を返す。"""
    sep = "=" * 52
    thin = "-" * 52
    lines = [
        f"\n{sep}",
        f"  Night Batch Report  {report.run_date}",
        f"  Status : {_STATUS_LABEL.get(report.status, report.status)}",
        f"  Target : {report.target_date}（翌営業日）",
        f"{sep}",
        "  Job Status:",
    ]
    for j in report.job_results:
        label = _JOB_STATUS_LABEL.get(j.status, j.status.upper())
        lines.append(f"    {j.job_name:<32} {label}  ({j.duration_sec:.1f}s)")
    lines.append(thin)
    uc = report.update_counts
    lines += [
        "  Update Counts:",
        f"    prices_daily : {uc.prices_daily:>6}    features     : {uc.features:>6}",
        f"    news_articles: {uc.news_articles:>6}    ai_scores    : {uc.ai_scores:>6}",
        f"    fundamentals : {uc.fundamentals:>6}    signals      : {uc.signals:>6}",
        f"                              signal_queue : {uc.signal_queue:>6}",
    ]
    lines.append(thin)
    nd = report.next_day_summary
    lines += [
        f"  Next Trading Day ({report.target_date}):",
        f"    BUY: {nd.buy_count}  SELL: {nd.sell_count}  "
        f"Symbols: {nd.target_symbols}  Orders: {nd.expected_orders}",
    ]
    if report.warnings:
        lines.append(thin)
        lines.append("  Warnings:")
        for w in report.warnings:
            lines.append(f"    [!] {w}")
    lines.append(f"{sep}\n")
    return "\n".join(lines)


def _to_serializable(obj: object) -> object:
    """dataclass → dict 変換後の datetime を ISO 文字列に変換する。"""
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_serializable(i) for i in obj]
    if isinstance(obj, datetime):
        return obj.isoformat()
    return obj


def format_json(report: NightBatchReport) -> str:
    """全指標を含む JSON 文字列を返す。"""
    data = _to_serializable(asdict(report))
    return json.dumps(data, ensure_ascii=False, indent=2)


def format_markdown(report: NightBatchReport) -> str:
    """人間向け Markdown レポート文字列を返す。"""
    lines: list[str] = []
    sec = 0

    def _section(title: str) -> str:
        nonlocal sec
        sec += 1
        return f"## {sec}. {title}"

    # 1. Overview
    lines += [
        "# Night Batch Report",
        "",
        _section("Overview"),
        "",
        "| Item | Value |",
        "|------|-------|",
        f"| 実行日 | {report.run_date} |",
        f"| 対象取引日 | {report.target_date} |",
        f"| 生成時刻 | {report.generated_at} |",
        f"| **最終判定** | **{report.status}** |",
        "",
    ]

    # 2. Job Status
    lines += [
        _section("Job Status"),
        "",
        "| ジョブ名 | ステータス | 開始時刻 | 終了時刻 | 実行時間(s) |",
        "|---------|-----------|---------|---------|------------|",
    ]
    for j in report.job_results:
        started = (
            j.started_at.isoformat()
            if isinstance(j.started_at, datetime)
            else j.started_at
        )
        finished = (
            j.finished_at.isoformat()
            if isinstance(j.finished_at, datetime)
            else j.finished_at
        )
        lines.append(
            f"| {j.job_name} | {j.status} | {started} | {finished} | {j.duration_sec:.1f} |"
        )
    lines.append("")

    # 3. Update Counts
    uc = report.update_counts
    lines += [
        _section("Update Counts"),
        "",
        "| テーブル | 更新件数 |",
        "|---------|--------|",
        f"| prices_daily | {uc.prices_daily} |",
        f"| news_articles | {uc.news_articles} |",
        f"| fundamentals | {uc.fundamentals} |",
        f"| features | {uc.features} |",
        f"| ai_scores | {uc.ai_scores} |",
        f"| signals | {uc.signals} |",
        f"| signal_queue | {uc.signal_queue} |",
        "",
    ]

    # 4. Next Trading Day Preparation
    nd = report.next_day_summary
    lines += [
        _section("Next Trading Day Preparation"),
        "",
        f"対象取引日: **{report.target_date}**",
        "",
        "| 項目 | 件数 |",
        "|-----|-----|",
        f"| BUY 件数 | {nd.buy_count} |",
        f"| SELL 件数 | {nd.sell_count} |",
        f"| 対象銘柄数 | {nd.target_symbols} |",
        f"| 想定発注件数 | {nd.expected_orders} |",
        "",
    ]

    # 5. Warnings（ある場合のみ）
    if report.warnings:
        lines += [
            _section("Warnings"),
            "",
        ]
        for w in report.warnings:
            lines.append(f"- ⚠️ {w}")
        lines.append("")

    # Final Decision（章番号は警告の有無に応じて 5 or 6）
    lines += [_section("Final Decision"), ""]
    if report.status == STATUS_READY:
        lines += [
            f"**{STATUS_READY}** — 翌営業日の自動執行を開始できます。",
            "",
            "- 全必須ジョブが正常完了しています。",
            "- signal_queue が正常に作成されています。",
            "- 特段の対応は不要です。",
        ]
    elif report.status == STATUS_READY_WITH_WARNINGS:
        lines += [
            f"**{STATUS_READY_WITH_WARNINGS}** — 警告を確認した上で、執行開始を判断してください。",
            "",
            "- 基本的な処理は完了していますが、警告があります。",
            "- 上記 Warnings を確認し、問題がなければ自動執行を開始できます。",
        ]
    else:  # BLOCKED
        lines += [
            f"**{STATUS_BLOCKED}** — 翌営業日の自動執行を **開始しないでください**。",
            "",
            "- 必須ジョブの失敗または signal_queue が空のため、自動執行は安全ではありません。",
            "- 上記 Warnings を確認し、手動で問題を解消してから再実行してください。",
        ]
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 保存
# ---------------------------------------------------------------------------


def save_report(
    report: NightBatchReport,
    output_dir: Path | str | None = None,
) -> Path:
    """レポートを artifacts/night_batch/{run_date}/ に保存する。

    保存ファイル:
        summary.json    全指標 JSON
        report.md       Markdown レポート
        warnings.json   警告リスト JSON

    同一 run_date で再実行した場合は既存ファイルを上書きする（exist_ok=True）。

    Returns:
        保存先ディレクトリのパス。
    """
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", report.run_date):
        raise ValueError(f"Invalid run_date: {report.run_date!r}")
    base = Path(output_dir) if output_dir else Path("artifacts") / "night_batch"
    run_dir = base / report.run_date
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "summary.json").write_text(format_json(report), encoding="utf-8")
    (run_dir / "report.md").write_text(format_markdown(report), encoding="utf-8")
    (run_dir / "warnings.json").write_text(
        json.dumps(report.warnings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return run_dir
