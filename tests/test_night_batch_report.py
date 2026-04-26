"""夜間バッチレポートモジュールのテスト"""

from __future__ import annotations

from datetime import datetime, timezone

from kabusys.operations.night_batch_report import (
    JobRunResult,
    NextDaySummary,
    UpdateCounts,
)


def _make_job(
    name: str = "data_update_job",
    status: str = "success",
    duration: float = 10.0,
    updated_rows: dict | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> JobRunResult:
    dt = datetime(2026, 4, 26, 15, 30, 0, tzinfo=timezone.utc)
    return JobRunResult(
        job_name=name,
        status=status,
        started_at=dt,
        finished_at=datetime(2026, 4, 26, 15, 30, int(duration), tzinfo=timezone.utc),
        duration_sec=duration,
        updated_rows=updated_rows or {},
        warnings=warnings or [],
        errors=errors or [],
    )


def _make_counts(**kwargs) -> UpdateCounts:
    defaults = dict(
        prices_daily=1850,
        news_articles=120,
        fundamentals=1850,
        features=1850,
        ai_scores=1850,
        signals=25,
        signal_queue=15,
    )
    defaults.update(kwargs)
    return UpdateCounts(**defaults)


def _make_next_day(**kwargs) -> NextDaySummary:
    defaults = dict(buy_count=8, sell_count=7, target_symbols=15, expected_orders=15)
    defaults.update(kwargs)
    return NextDaySummary(**defaults)


def test_job_run_result_instantiation():
    """JobRunResult が正しくインスタンス化できる。"""
    job = _make_job()
    assert job.job_name == "data_update_job"
    assert job.status == "success"
    assert job.duration_sec == 10.0


def test_update_counts_defaults():
    """UpdateCounts のデフォルト値がすべて 0。"""
    counts = UpdateCounts()
    assert counts.prices_daily == 0
    assert counts.signal_queue == 0


def test_next_day_summary_instantiation():
    """NextDaySummary が正しくインスタンス化できる。"""
    nd = _make_next_day()
    assert nd.buy_count == 8
    assert nd.expected_orders == 15
