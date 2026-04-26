"""夜間バッチレポートモジュールのテスト"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from kabusys.operations.night_batch_report import (
    MANDATORY_JOBS,
    JobRunResult,
    NightBatchReport,
    NextDaySummary,
    UpdateCounts,
    _determine_status,
    _generate_warnings,
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


# ---------------------------------------------------------------------------
# _determine_status
# ---------------------------------------------------------------------------


def test_status_ready_all_success():
    """全ジョブ成功 + signal_queue > 0 → READY。"""
    jobs = [
        _make_job(name=n)
        for n in [
            "data_update_job",
            "feature_generation_job",
            "ai_analysis_job",
            "strategy_signal_job",
            "portfolio_construction_job",
        ]
    ]
    counts = _make_counts()
    assert _determine_status(jobs, counts) == "READY"


def test_status_blocked_mandatory_failed():
    """必須ジョブが failed → BLOCKED。"""
    jobs = [_make_job(name="data_update_job", status="failed")]
    counts = _make_counts()
    assert _determine_status(jobs, counts) == "BLOCKED"


def test_status_blocked_signal_queue_zero():
    """signal_queue == 0 → BLOCKED。"""
    jobs = [
        _make_job(name=n)
        for n in [
            "data_update_job",
            "feature_generation_job",
            "ai_analysis_job",
            "strategy_signal_job",
            "portfolio_construction_job",
        ]
    ]
    counts = _make_counts(signal_queue=0)
    assert _determine_status(jobs, counts) == "BLOCKED"


def test_status_ready_with_warnings_job_warning():
    """ジョブが warning → READY_WITH_WARNINGS。"""
    jobs = [_make_job(name="ai_analysis_job", status="warning")]
    counts = _make_counts()
    assert _determine_status(jobs, counts) == "READY_WITH_WARNINGS"


def test_status_ready_with_warnings_signals_zero():
    """signals == 0（signal_queue > 0）→ READY_WITH_WARNINGS。"""
    jobs = [_make_job()]
    counts = _make_counts(signals=0, signal_queue=5)
    assert _determine_status(jobs, counts) == "READY_WITH_WARNINGS"


def test_status_ready_with_warnings_job_has_warning_message():
    """ジョブの warnings リストが空でない → READY_WITH_WARNINGS。"""
    jobs = [_make_job(warnings=["データ件数が少ない"])]
    counts = _make_counts()
    assert _determine_status(jobs, counts) == "READY_WITH_WARNINGS"


# ---------------------------------------------------------------------------
# _generate_warnings
# ---------------------------------------------------------------------------


def test_warnings_failed_mandatory_job():
    """必須ジョブが failed → 警告にジョブ名が含まれる。"""
    jobs = [_make_job(name="data_update_job", status="failed")]
    warnings = _generate_warnings(jobs, _make_counts())
    assert any("data_update_job" in w for w in warnings)


def test_warnings_signal_queue_zero():
    """signal_queue == 0 → 警告に signal_queue が含まれる。"""
    warnings = _generate_warnings([_make_job()], _make_counts(signal_queue=0))
    assert any("signal_queue" in w for w in warnings)


def test_warnings_signals_zero():
    """signals == 0 → 警告に signals が含まれる。"""
    warnings = _generate_warnings([_make_job()], _make_counts(signals=0))
    assert any("signals" in w for w in warnings)


def test_warnings_prices_daily_zero():
    """prices_daily == 0 → 警告が生成される。"""
    warnings = _generate_warnings([_make_job()], _make_counts(prices_daily=0))
    assert any("prices_daily" in w for w in warnings)


def test_warnings_empty_on_healthy():
    """全ジョブ成功・全カウント正常 → 警告なし。"""
    jobs = [_make_job(name=n) for n in MANDATORY_JOBS]
    warnings = _generate_warnings(jobs, _make_counts())
    assert warnings == []


def test_warnings_includes_job_warnings():
    """ジョブの warnings フィールドが全体の warnings に含まれる。"""
    jobs = [_make_job(warnings=["シグナル件数が少ない"])]
    warnings = _generate_warnings(jobs, _make_counts())
    assert "シグナル件数が少ない" in warnings
