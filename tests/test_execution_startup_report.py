"""execution_startup_report のユニットテスト"""

from __future__ import annotations

import json as json_mod
from datetime import date

import pytest

from kabusys.execution.reconciler import PositionDiscrepancy, ReconcileResult
from kabusys.operations.execution_startup_report import (
    ExecutionStartupReport,
    _determine_status,
    _generate_warnings,
    build_report,
    format_cli_summary,
    format_json,
    format_markdown,
    save_report,
)


# ---------------------------------------------------------------------------
# _determine_status
# ---------------------------------------------------------------------------


def test_determine_status_blocked_by_no_status():
    assert _determine_status(orders_no_status=1, position_discrepancies_count=0) == "BLOCKED"


def test_determine_status_blocked_even_with_discrepancies():
    """orders_no_status > 0 は discrepancies があっても BLOCKED。"""
    assert _determine_status(orders_no_status=2, position_discrepancies_count=3) == "BLOCKED"


def test_determine_status_ready_with_warnings():
    assert (
        _determine_status(orders_no_status=0, position_discrepancies_count=1)
        == "READY_WITH_WARNINGS"
    )


def test_determine_status_ready():
    assert _determine_status(orders_no_status=0, position_discrepancies_count=0) == "READY"


# ---------------------------------------------------------------------------
# _generate_warnings
# ---------------------------------------------------------------------------


def test_generate_warnings_no_issues():
    assert _generate_warnings(orders_no_status=0, position_discrepancies=[]) == []


def test_generate_warnings_orders_no_status():
    w = _generate_warnings(orders_no_status=2, position_discrepancies=[])
    assert len(w) == 1
    assert "2" in w[0]


def test_generate_warnings_position_discrepancy():
    disc = [{"code": "1234", "broker_qty": 100, "local_qty": 80, "diff": 20}]
    w = _generate_warnings(orders_no_status=0, position_discrepancies=disc)
    assert len(w) == 1
    assert "1234" in w[0]


def test_generate_warnings_both():
    disc = [{"code": "1234", "broker_qty": 100, "local_qty": 80, "diff": 20}]
    w = _generate_warnings(orders_no_status=1, position_discrepancies=disc)
    assert len(w) == 2


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def test_build_report_ready():
    result = ReconcileResult(orders_synced=3, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    assert report.status == "READY"
    assert report.orders_synced == 3
    assert report.orders_no_status == 0
    assert report.position_discrepancies == []
    assert report.warnings == []
    assert report.startup_date == "2026-04-27"


def test_build_report_blocked():
    result = ReconcileResult(orders_synced=0, orders_no_status=1, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    assert report.status == "BLOCKED"
    assert len(report.warnings) > 0


def test_build_report_ready_with_warnings():
    discrepancy = PositionDiscrepancy(code="1234", broker_qty=100, local_qty=80, diff=20)
    result = ReconcileResult(
        orders_synced=2, orders_no_status=0, position_discrepancies=[discrepancy]
    )
    report = build_report(result, startup_date=date(2026, 4, 27))
    assert report.status == "READY_WITH_WARNINGS"
    assert len(report.position_discrepancies) == 1
    assert report.position_discrepancies[0]["code"] == "1234"
    assert report.position_discrepancies[0]["diff"] == 20


def test_build_report_generated_at_is_utc():
    result = ReconcileResult()
    report = build_report(result, startup_date=date(2026, 4, 27))
    assert "+00:00" in report.generated_at


# ---------------------------------------------------------------------------
# format_cli_summary
# ---------------------------------------------------------------------------


def test_format_cli_summary_ready():
    result = ReconcileResult(orders_synced=3, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    s = format_cli_summary(report)
    assert "READY" in s
    assert "2026-04-27" in s
    assert "orders_synced" in s


def test_format_cli_summary_blocked_shows_warnings():
    result = ReconcileResult(orders_synced=0, orders_no_status=1, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    s = format_cli_summary(report)
    assert "BLOCKED" in s
    assert "Warnings" in s


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


def test_format_json_parseable_with_required_keys():
    result = ReconcileResult(orders_synced=1, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    data = json_mod.loads(format_json(report))
    assert data["status"] == "READY"
    assert data["orders_synced"] == 1
    assert "startup_date" in data
    assert "generated_at" in data
    assert "warnings" in data
    assert "position_discrepancies" in data


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


def test_format_markdown_contains_required_sections():
    result = ReconcileResult(orders_synced=1, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    md = format_markdown(report)
    assert "Execution Startup Summary" in md
    assert "Reconciliation" in md
    assert "Final Decision" in md


def test_format_markdown_blocked_includes_warnings_section():
    result = ReconcileResult(orders_synced=0, orders_no_status=2, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    md = format_markdown(report)
    assert "Warnings" in md
    assert "BLOCKED" in md


def test_format_markdown_discrepancy_table():
    discrepancy = PositionDiscrepancy(code="5678", broker_qty=50, local_qty=30, diff=20)
    result = ReconcileResult(orders_synced=0, orders_no_status=0, position_discrepancies=[discrepancy])
    report = build_report(result, startup_date=date(2026, 4, 27))
    md = format_markdown(report)
    assert "5678" in md
    assert "Position Discrepancies" in md


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------


def test_save_report_creates_three_files(tmp_path):
    result = ReconcileResult(orders_synced=2, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    dest = save_report(report, output_dir=tmp_path)
    assert (dest / "summary.json").exists()
    assert (dest / "report.md").exists()
    assert (dest / "warnings.json").exists()


def test_save_report_invalid_startup_date_raises(tmp_path):
    report = ExecutionStartupReport(
        startup_date="invalid-date",
        generated_at="2026-04-27T00:00:00+00:00",
        status="READY",
        orders_synced=0,
        orders_no_status=0,
        position_discrepancies=[],
        warnings=[],
    )
    with pytest.raises(ValueError, match="Invalid startup_date"):
        save_report(report, output_dir=tmp_path)


def test_save_report_overwrite_is_idempotent(tmp_path):
    """同一 startup_date で 2 回保存しても例外にならない。"""
    result = ReconcileResult(orders_synced=1, orders_no_status=0, position_discrepancies=[])
    report = build_report(result, startup_date=date(2026, 4, 27))
    save_report(report, output_dir=tmp_path)
    save_report(report, output_dir=tmp_path)  # 2回目も例外なし
    assert (tmp_path / "2026-04-27" / "summary.json").exists()
