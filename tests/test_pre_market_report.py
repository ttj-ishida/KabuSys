"""Pre-Market Report 純粋関数テスト"""

from __future__ import annotations

import json
from datetime import date

import pytest

from kabusys.operations.pre_market_report import (
    STATUS_BLOCKED,
    STATUS_READY,
    STATUS_READY_WITH_WARNINGS,
    PreMarketReport,
    _determine_status,
    _generate_warnings,
    build_report,
    format_cli_summary,
    format_json,
    format_markdown,
    save_report,
)


def _make_checks(
    data_freshness_ok: bool = True,
    signal_queue_pending: int = 5,
    position_count: int = 3,
    stop_flag_exists: bool = False,
    task_scheduler_ready: bool = True,
) -> dict:
    return dict(
        data_freshness_ok=data_freshness_ok,
        signal_queue_pending=signal_queue_pending,
        position_count=position_count,
        stop_flag_exists=stop_flag_exists,
        task_scheduler_ready=task_scheduler_ready,
    )


def _make_report(status_override: str | None = None) -> PreMarketReport:
    checks = _make_checks()
    report = build_report(
        report_date=date(2026, 4, 27),
        **checks,
    )
    if status_override:
        report = PreMarketReport(
            report_date=report.report_date,
            generated_at=report.generated_at,
            status=status_override,
            checks=report.checks,
            warnings=report.warnings,
        )
    return report


# --- _determine_status ---


def test_status_ready_all_ok():
    assert _determine_status(**_make_checks()) == STATUS_READY


def test_status_blocked_no_pending_signals():
    assert _determine_status(**_make_checks(signal_queue_pending=0)) == STATUS_BLOCKED


def test_status_blocked_stop_flag():
    assert _determine_status(**_make_checks(stop_flag_exists=True)) == STATUS_BLOCKED


def test_status_blocked_task_scheduler_not_ready():
    assert _determine_status(**_make_checks(task_scheduler_ready=False)) == STATUS_BLOCKED


def test_status_ready_with_warnings_stale_data():
    assert _determine_status(**_make_checks(data_freshness_ok=False)) == STATUS_READY_WITH_WARNINGS


# --- _generate_warnings ---


def test_no_warnings_when_all_ok():
    assert _generate_warnings(**_make_checks()) == []


def test_warning_no_pending_signals():
    ws = _generate_warnings(**_make_checks(signal_queue_pending=0))
    assert any("signal_queue" in w for w in ws)


def test_warning_stop_flag():
    ws = _generate_warnings(**_make_checks(stop_flag_exists=True))
    assert any("停止フラグ" in w for w in ws)


def test_warning_task_not_ready():
    ws = _generate_warnings(**_make_checks(task_scheduler_ready=False))
    assert any("Task Scheduler" in w for w in ws)


def test_warning_stale_data():
    ws = _generate_warnings(**_make_checks(data_freshness_ok=False))
    assert any("prices_daily" in w for w in ws)


# --- build_report ---


def test_build_report_ready():
    report = build_report(report_date=date(2026, 4, 27), **_make_checks())
    assert report.status == STATUS_READY
    assert len(report.checks) == 5
    assert report.report_date == "2026-04-27"
    assert report.warnings == []


def test_build_report_blocked_no_signals():
    report = build_report(report_date=date(2026, 4, 27), **_make_checks(signal_queue_pending=0))
    assert report.status == STATUS_BLOCKED
    assert any("signal_queue" in w for w in report.warnings)


# --- format_cli_summary ---


def test_format_cli_summary_contains_status():
    report = build_report(report_date=date(2026, 4, 27), **_make_checks())
    summary = format_cli_summary(report)
    assert "READY" in summary
    assert "2026-04-27" in summary


def test_format_cli_summary_blocked_shows_blocked():
    report = build_report(report_date=date(2026, 4, 27), **_make_checks(signal_queue_pending=0))
    summary = format_cli_summary(report)
    assert "BLOCKED" in summary


# --- format_json ---


def test_format_json_valid():
    report = build_report(report_date=date(2026, 4, 27), **_make_checks())
    data = json.loads(format_json(report))
    assert data["status"] == STATUS_READY
    assert "checks" in data
    assert len(data["checks"]) == 5


# --- format_markdown ---


def test_format_markdown_contains_sections():
    report = build_report(report_date=date(2026, 4, 27), **_make_checks())
    md = format_markdown(report)
    assert "# Pre-Market Report" in md
    assert "## " in md


def test_format_markdown_no_warnings_section_when_empty():
    report = build_report(report_date=date(2026, 4, 27), **_make_checks())
    md = format_markdown(report)
    assert "Warnings" not in md


def test_format_markdown_with_warnings_section():
    report = build_report(report_date=date(2026, 4, 27), **_make_checks(stop_flag_exists=True))
    md = format_markdown(report)
    assert "Warnings" in md


# --- save_report ---


def test_save_report_creates_files(tmp_path):
    report = build_report(report_date=date(2026, 4, 27), **_make_checks())
    run_dir = save_report(report, output_dir=tmp_path)
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "warnings.json").exists()


def test_save_report_default_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    report = build_report(report_date=date(2026, 4, 27), **_make_checks())
    run_dir = save_report(report)
    assert run_dir.parts[-3] == "artifacts"
    assert run_dir.parts[-2] == "pre_market"


def test_save_report_invalid_report_date_raises(tmp_path):
    report = build_report(report_date=date(2026, 4, 27), **_make_checks())
    report.report_date = "../evil"
    with pytest.raises(ValueError, match="Invalid report_date"):
        save_report(report, output_dir=tmp_path)
