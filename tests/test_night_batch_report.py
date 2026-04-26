"""夜間バッチレポートモジュールのテスト"""

from __future__ import annotations

import json as json_mod
from datetime import date, datetime, timedelta, timezone

from kabusys.operations.night_batch_report import (
    MANDATORY_JOBS,
    JobRunResult,
    NightBatchReport,
    NextDaySummary,
    UpdateCounts,
    _determine_status,
    _generate_warnings,
    build_report,
    format_cli_summary,
    format_json,
    format_markdown,
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


def _all_success_jobs() -> list[JobRunResult]:
    return [_make_job(name=n) for n in MANDATORY_JOBS]


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


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def test_build_report_returns_night_batch_report():
    """build_report() が NightBatchReport を返す。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert isinstance(report, NightBatchReport)


def test_build_report_status_ready():
    """全成功 → status == READY。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.status == "READY"


def test_build_report_status_blocked():
    """必須ジョブ失敗 → status == BLOCKED。"""
    jobs = [_make_job(name="data_update_job", status="failed")]
    report = build_report(
        jobs,
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.status == "BLOCKED"


def test_build_report_dates_as_iso_string():
    """run_date / target_date が ISO 形式文字列。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.run_date == "2026-04-26"
    assert report.target_date == "2026-04-27"


def test_build_report_generated_at_is_utc_iso():
    """generated_at が UTC ISO 8601 形式（末尾が +00:00）。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.generated_at.endswith("+00:00")


def test_build_report_no_warnings_on_healthy():
    """全成功・全カウント正常 → warnings が空。"""
    report = build_report(
        _all_success_jobs(),
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )
    assert report.warnings == []


# ---------------------------------------------------------------------------
# フォーマッター用ヘルパー
# ---------------------------------------------------------------------------


def _make_report(status: str = "READY") -> NightBatchReport:
    if status == "BLOCKED":
        jobs = [_make_job(name="data_update_job", status="failed")]
    elif status == "READY_WITH_WARNINGS":
        jobs = [_make_job(name="ai_analysis_job", status="warning")]
    else:
        jobs = _all_success_jobs()
    return build_report(
        jobs,
        _make_counts(),
        _make_next_day(),
        run_date=date(2026, 4, 26),
        target_date=date(2026, 4, 27),
    )


# ---------------------------------------------------------------------------
# format_cli_summary
# ---------------------------------------------------------------------------


def test_format_cli_summary_contains_status():
    """CLI サマリに最終判定ステータスが含まれる。"""
    report = _make_report("READY")
    summary = format_cli_summary(report)
    assert "READY" in summary


def test_format_cli_summary_contains_run_date():
    """CLI サマリに実行日が含まれる。"""
    report = _make_report()
    summary = format_cli_summary(report)
    assert "2026-04-26" in summary


def test_format_cli_summary_contains_signal_queue():
    """CLI サマリに signal_queue 件数が含まれる。"""
    report = _make_report()
    summary = format_cli_summary(report)
    assert "15" in summary  # signal_queue=15


def test_format_cli_summary_blocked_shows_blocked():
    """BLOCKED のとき CLI サマリに BLOCKED が含まれる。"""
    report = _make_report("BLOCKED")
    summary = format_cli_summary(report)
    assert "BLOCKED" in summary


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


def test_format_json_is_valid_json():
    """format_json() が有効な JSON 文字列を返す。"""
    report = _make_report()
    raw = format_json(report)
    data = json_mod.loads(raw)
    assert isinstance(data, dict)


def test_format_json_contains_expected_keys():
    """JSON に必須キーが含まれる。"""
    report = _make_report()
    data = json_mod.loads(format_json(report))
    for key in [
        "run_date",
        "target_date",
        "generated_at",
        "status",
        "job_results",
        "update_counts",
        "next_day_summary",
        "warnings",
    ]:
        assert key in data, f"Missing key: {key}"


def test_format_json_status_roundtrip():
    """JSON から status が正しく復元できる。"""
    report = _make_report("BLOCKED")
    data = json_mod.loads(format_json(report))
    assert data["status"] == "BLOCKED"


def test_format_json_datetime_serialized_as_string():
    """JobRunResult の started_at が JSON で文字列にシリアライズされる。"""
    report = _make_report()
    data = json_mod.loads(format_json(report))
    assert isinstance(data["job_results"][0]["started_at"], str)


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


def test_format_markdown_contains_sections():
    """Markdown に必須セクション見出しが含まれる。"""
    report = _make_report()
    md = format_markdown(report)
    for section in [
        "Overview",
        "Job Status",
        "Update Counts",
        "Next Trading Day",
        "Final Decision",
    ]:
        assert section in md, f"Missing section: {section}"


def test_format_markdown_contains_status():
    """Markdown にステータスが含まれる。"""
    report = _make_report("READY")
    md = format_markdown(report)
    assert "READY" in md


def test_format_markdown_contains_signal_queue():
    """Markdown に signal_queue 件数が含まれる。"""
    report = _make_report()
    md = format_markdown(report)
    assert "15" in md  # signal_queue=15


def test_format_markdown_warnings_section():
    """警告がある場合は Warnings セクションが含まれる。"""
    report = _make_report("READY_WITH_WARNINGS")
    md = format_markdown(report)
    assert "Warnings" in md


def test_format_markdown_no_warnings_section_when_empty():
    """警告なしのとき Warnings セクションは含まれない。"""
    report = _make_report("READY")
    md = format_markdown(report)
    assert "## 5. Warnings" not in md


def test_format_markdown_final_decision_blocked():
    """BLOCKED のとき Final Decision に自動執行禁止の文言が含まれる。"""
    report = _make_report("BLOCKED")
    md = format_markdown(report)
    assert "BLOCKED" in md
    assert "自動執行" in md or "執行" in md
