import os
import json
import math
import sqlite3
from types import SimpleNamespace
from datetime import date, datetime, timezone, timedelta
from pathlib import Path

import pytest

from kabusys.config import _parse_env_line, _load_env_file, _require, Settings
from kabusys.tools.paper_verification_report import _p95
from kabusys.operations.signal_queue_report import (
    build_report as build_signal_report,
    format_cli_summary as format_signal_cli,
    format_json as format_signal_json,
    format_markdown as format_signal_md,
    save_report as save_signal_report,
)
from kabusys.operations.execution_startup_report import (
    build_report as build_exec_report,
    format_cli_summary as format_exec_cli,
    format_json as format_exec_json,
    format_markdown as format_exec_md,
    save_report as save_exec_report,
)
from kabusys.operations.night_batch_report import (
    JobRunResult,
    UpdateCounts,
    NextDaySummary,
    build_report as build_night_report,
    _determine_status as night_determine_status,
    _generate_warnings as night_generate_warnings,
    format_cli_summary as format_night_cli,
    format_json as format_night_json,
)
from kabusys.operations.performance_report import (
    build_report as build_performance_report,
    format_markdown as format_performance_md,
    save_report as save_performance_report,
)


def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # comment") is None
    assert _parse_env_line("export KEY=val") == ("KEY", "val")
    assert _parse_env_line("KEY=  value  ") == ("KEY", "value")
    # no equals
    assert _parse_env_line("NOEQUALS") is None
    # quoted with escapes
    assert _parse_env_line("FOO='a\\'b\\nc'") == ("FOO", "a'b\\nc")
    assert _parse_env_line('BAR="x\\\\"') == ("BAR", 'x\\')
    # inline comment only when preceded by space/tab
    assert _parse_env_line("K=1#notcomment") == ("K", "1#notcomment")
    assert _parse_env_line("K=1 #comment") == ("K", "1")


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    envfile = tmp_path / ".env"
    envfile.write_text(
        "\n".join(
            [
                "# comment",
                "A=1",
                "B=two",
                "SECRET='s\\'e\\'c'",
                "EXPORT_ME=ok",
            ]
        ),
        encoding="utf-8",
    )
    # ensure B not set, A set
    monkeypatch.delenv("A", raising=False)
    monkeypatch.setenv("B", "existing")
    # protected should prevent overwrite when override=True
    protected = frozenset(["B"])
    _load_env_file(envfile, override=True, protected=protected)
    assert os.environ.get("A") == "1"
    # B should remain existing
    assert os.environ.get("B") == "existing"
    assert os.environ.get("SECRET") == "s'e'c"
    # load without override should not overwrite existing keys
    monkeypatch.setenv("EXPORT_ME", "existing2")
    _load_env_file(envfile, override=False, protected=frozenset())
    assert os.environ.get("EXPORT_ME") == "existing2"


def test_require_and_settings_properties(monkeypatch):
    # Ensure missing variable raises
    monkeypatch.delenv("SOME_REQUIRED", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_REQUIRED")
    # Test Settings.env and derived flags
    monkeypatch.setenv("KABUSYS_ENV", "live")
    s = Settings()
    assert s.env == "live"
    assert s.is_live is True
    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = Settings().env
    # paper_fill_mode valid/invalid
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert Settings().paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "PARTIAL")
    assert Settings().paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "bad_mode")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode


def test_p95_empty_and_values():
    assert _p95([]) is None
    vals = [1, 2, 3, 4, 5, 100]
    # 95th percentile index ceil(6 * .95) -1 = ceil(5.7)-1 = 6-1=5 -> vals[5]=100
    assert _p95(vals) == 100
    vals2 = list(range(100))
    # expect element at ceil(100*.95)-1 = 95-1=94 -> 94
    assert _p95(vals2) == 94


def test_signal_queue_build_format_save(tmp_path):
    # build with no signals -> EMPTY
    report = build_signal_report([], report_date=date(2026, 4, 28))
    assert report.status == "EMPTY"
    assert "翌営業日のシグナルがありません" in "\n".join(report.warnings)
    s = format_signal_cli(report)
    assert "Signal Queue Confirmation" in s
    j = format_signal_json(report)
    parsed = json.loads(j)
    assert parsed["report_date"] == "2026-04-28"
    md = format_signal_md(report)
    assert "Signal Queue Confirmation" in md
    # create one buy without size to generate warning
    signals = [
        {"code": "1234", "side": "buy", "target_size": None, "target_weight": None, "signal_rank": 1}
    ]
    report2 = build_signal_report(signals, report_date=date(2026, 4, 28))
    assert report2.status == "READY"
    assert any("target_size 未設定" in w for w in report2.warnings)
    # save to tmp dir
    out_dir = tmp_path / "out"
    run_dir = save_signal_report(report2, output_dir=out_dir)
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "warnings.json").exists()
    # invalid report_date should raise
    bad = report2
    bad.report_date = "2026-02-30"  # invalid calendar date
    with pytest.raises(ValueError):
        save_signal_report(bad, output_dir=out_dir)


def _make_reconcile_result(orders_synced=0, orders_no_status=0, discrepancies=None):
    if discrepancies is None:
        discrepancies = []
    # Create object with expected attributes
    return SimpleNamespace(
        orders_synced=orders_synced,
        orders_no_status=orders_no_status,
        position_discrepancies=discrepancies,
    )


def test_execution_startup_report_statuss_and_save(tmp_path):
    # BLOCKED when orders_no_status > 0
    rr = _make_reconcile_result(orders_synced=1, orders_no_status=2, discrepancies=[])
    rep = build_exec_report(rr, startup_date=date(2026, 4, 28))
    assert rep.status == "BLOCKED"
    assert any("ステータス不明の注文" in w for w in rep.warnings)
    # READY_WITH_WARNINGS when discrepancies exist
    disc = [SimpleNamespace(code="AAA", broker_qty=10, local_qty=8, diff=2)]
    rr2 = _make_reconcile_result(orders_synced=1, orders_no_status=0, discrepancies=disc)
    rep2 = build_exec_report(rr2, startup_date=date(2026, 4, 28))
    assert rep2.status == "READY_WITH_WARNINGS"
    assert any("ポジション差分" in w for w in rep2.warnings)
    # READY when clean
    rr3 = _make_reconcile_result(orders_synced=5, orders_no_status=0, discrepancies=[])
    rep3 = build_exec_report(rr3, startup_date=date(2026, 4, 28))
    assert rep3.status == "READY"
    # formatting
    s = format_exec_cli(rep3)
    assert "Execution Startup Summary" in s
    j = format_exec_json(rep3)
    parsed = json.loads(j)
    assert parsed["startup_date"] == "2026-04-28"
    md = format_exec_md(rep3)
    assert "Execution Startup Summary" in md
    # save and invalid startup_date
    out = tmp_path / "exec_out"
    run_dir = save_exec_report(rep3, output_dir=out)
    assert (run_dir / "summary.json").exists()
    # invalid startup_date format
    rep3_bad = rep3
    rep3_bad.startup_date = "bad-date"
    with pytest.raises(ValueError):
        save_exec_report(rep3_bad, output_dir=out)


def test_night_batch_report_logic_and_formatting():
    now = datetime.now(timezone.utc)
    # Build job results: include all mandatory jobs as success
    jobs = [
        JobRunResult(
            job_name=name,
            status="success",
            started_at=now,
            finished_at=now + timedelta(seconds=1),
            duration_sec=1.0,
            updated_rows={},
            warnings=[],
            errors=[],
        )
        for name in [
            "data_update_job",
            "feature_generation_job",
            "ai_analysis_job",
            "strategy_signal_job",
            "portfolio_construction_job",
        ]
    ]
    uc = UpdateCounts(prices_daily=10, features=5, signals=1, signal_queue=1)
    nd = NextDaySummary(buy_count=2, sell_count=1, target_symbols=3, expected_orders=3)
    report = build_night_report(jobs, uc, nd, run_date=date(2026, 4, 28), target_date=date(2026, 4, 29))
    assert report.status == "READY"
    s = format_night_cli(report)
    assert "Night Batch Report" in s
    j = format_night_json(report)
    parsed = json.loads(j)
    assert parsed["run_date"] == "2026-04-28"
    # Missing mandatory job => BLOCKED
    jobs_missing = jobs[:-1]
    status_blocked = night_determine_status(jobs_missing, uc)
    assert status_blocked == "BLOCKED"
    warnings = night_generate_warnings(jobs_missing, uc)
    assert any("必須ジョブが実行されませんでした" in w for w in warnings)
    # signal_queue == 0 => BLOCKED
    uc2 = UpdateCounts(prices_daily=10, features=5, signals=1, signal_queue=0)
    assert night_determine_status(jobs, uc2) == "BLOCKED"
    # job with warning => READY_WITH_WARNINGS
    jobs_warn = list(jobs)
    jobs_warn[0] = JobRunResult(
        job_name=jobs_warn[0].job_name,
        status="warning",
        started_at=now,
        finished_at=now + timedelta(seconds=1),
        duration_sec=1.0,
        updated_rows={},
        warnings=["minor"],
        errors=[],
    )
    assert night_determine_status(jobs_warn, uc) == "READY_WITH_WARNINGS"
    wlist = night_generate_warnings(jobs_warn, uc)
    assert any("ジョブが警告で完了" in w or "minor" in w for w in wlist)


def test_performance_report_build_format_save(tmp_path):
    # empty rows
    rep_empty = build_performance_report([], report_type="daily", env="live", from_date=date(2026, 4, 1), to_date=date(2026, 4, 30))
    assert rep_empty.summary["total_trading_days"] == 0
    md = format_performance_md(rep_empty)
    assert "運用成績レポート" in md
    out = tmp_path / "perf"
    saved = save_performance_report(rep_empty, output_dir=out)
    assert (saved / "report.md").exists()
    # daily rows
    Row = SimpleNamespace
    rows = [
        Row(date=date(2026,4,1), equity=1000.0, daily_return=0.01, drawdown=-0.02, cumulative_return=0.0),
        Row(date=date(2026,4,2), equity=1010.0, daily_return=0.01, drawdown=-0.01, cumulative_return=0.01),
    ]
    rep_daily = build_performance_report(rows, report_type="daily", env="paper_trading", from_date=date(2026,4,1), to_date=date(2026,4,2))
    assert rep_daily.summary["total_trading_days"] == 2
    md2 = format_performance_md(rep_daily)
    assert "日次明細" in md2
    saved2 = save_performance_report(rep_daily, output_dir=out)
    assert (saved2 / rep_daily.env / rep_daily.report_type / rep_daily.to_date / "report.md").exists() or (saved2 / "report.md").exists()  # path may vary based on implementation details