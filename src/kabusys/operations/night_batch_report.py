"""
夜間バッチ結果確認レポート生成モジュール。

夜間バッチ（21:00頃）完了後に READY / READY_WITH_WARNINGS / BLOCKED
の最終判定を含むレポートを生成する。DB への参照は行わず、
呼び出し元から受け取ったデータのみを使用する。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

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
      - 必須ジョブのいずれかが failed
      - signal_queue == 0

    READY_WITH_WARNINGS 条件（BLOCKED でなく、いずれかが真）:
      - いずれかのジョブが status == "warning"
      - いずれかのジョブの warnings リストが空でない
      - signals == 0

    それ以外: READY
    """
    has_failed_mandatory = any(
        j.job_name in MANDATORY_JOBS and j.status == "failed" for j in job_results
    )
    if has_failed_mandatory or update_counts.signal_queue == 0:
        return STATUS_BLOCKED

    has_warning_status = any(j.status == "warning" for j in job_results)
    has_job_warnings = any(j.warnings for j in job_results)
    if has_warning_status or has_job_warnings or update_counts.signals == 0:
        return STATUS_READY_WITH_WARNINGS

    return STATUS_READY


def _generate_warnings(
    job_results: list[JobRunResult],
    update_counts: UpdateCounts,
) -> list[str]:
    """警告メッセージのリストを生成する。"""
    warnings: list[str] = []

    for j in job_results:
        if j.status == "failed" and j.job_name in MANDATORY_JOBS:
            warnings.append(f"必須ジョブが失敗しました: {j.job_name}")
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
