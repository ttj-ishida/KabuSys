"""夜間バッチレポートモジュールのテスト"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kabusys.operations.night_batch_report import (
    JobRunResult,
    NightBatchReport,
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
        finished_at=dt + timedelta(seconds=duration),
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
    assert counts.news_articles == 0
    assert counts.fundamentals == 0
    assert counts.features == 0
    assert counts.ai_scores == 0
    assert counts.signals == 0
    assert counts.signal_queue == 0


def test_next_day_summary_instantiation():
    """NextDaySummary が正しくインスタンス化できる。"""
    nd = _make_next_day()
    assert nd.buy_count == 8
    assert nd.expected_orders == 15


def test_night_batch_report_instantiation():
    """NightBatchReport が正しくインスタンス化できる。"""
    report = NightBatchReport(
        run_date="2026-04-26",
        target_date="2026-04-27",
        generated_at="2026-04-26T12:00:00+00:00",
        status="READY",
        job_results=[_make_job()],
        update_counts=_make_counts(),
        next_day_summary=_make_next_day(),
        warnings=[],
    )
    assert report.run_date == "2026-04-26"
    assert report.status == "READY"
    assert len(report.job_results) == 1
