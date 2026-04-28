import os
import csv
import json
import sqlite3
import subprocess
from types import SimpleNamespace
from datetime import date, datetime, timezone
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

from kabusys.config import _parse_env_line, _load_env_file, Settings
from kabusys.tools.paper_verification_report import (
    _p95,
    _build_date_filter,
    _fmt_float,
    _fmt_int,
)
from kabusys.operations import signal_queue_report as sqr
from kabusys.operations import execution_startup_report as esr
from kabusys.operations import pre_market_report as pmr
from kabusys.operations import night_batch_report as nbr
from kabusys.operations import position_reconciliation_report as prr
from kabusys.operations import pre_market_collector as pmc


def test_parse_env_line_blank_and_comment():
    assert _parse_env_line("") is None
    assert _parse_env_line("   \n") is None
    assert _parse_env_line("# comment") is None
    assert _parse_env_line("   # inline") is None


def test_parse_env_line_export_and_simple():
    assert _parse_env_line("export KEY=val") == ("KEY", "val")
    assert _parse_env_line("FOO=bar") == ("FOO", "bar")


def test_parse_env_line_no_equal():
    assert _parse_env_line("NOEQUAL") is None


def test_parse_env_line_quoted_with_escapes_and_inline_comment():
    s = r"KEY='va\'lue' # comment ignored"
    assert _parse_env_line(s) == ("KEY", "va'lue")
    s2 = r'KEY2="a\"b"'
    assert _parse_env_line(s2) == ("KEY2", 'a"b')


def test_parse_env_line_unquoted_with_hash_behavior():
    # '#' preceded by space => comment starts
    assert _parse_env_line("KEY=value #comment") == ("KEY", "value")
    # '#' directly after value char => kept
    assert _parse_env_line("KEY=value#notcomment") == ("KEY", "value#notcomment")


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("A=1\nB=2\nC=3\n")
    # set initial environ
    monkeypatch.setenv("A", "orig")
    # override=False should not change existing A, but set D if present
    _load_env_file(env_file, override=False, protected=frozenset())
    assert os.environ["A"] == "orig"
    assert os.environ.get("B") == "2"
    # override True but protect A should not overwrite A
    env_file.write_text("A=9\nB=8\n")
    protected = frozenset({"A"})
    _load_env_file(env_file, override=True, protected=protected)
    assert os.environ["A"] == "orig"
    assert os.environ["B"] == "8"


def test_settings_paper_fill_mode_valid_and_invalid(monkeypatch):
    s = Settings()
    # default should be 'instant'
    monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
    assert Settings().paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    assert Settings().paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "INSTANT")
    assert Settings().paper_fill_mode == "instant"
    # invalid value should raise
    monkeypatch.setenv("PAPER_FILL_MODE", "badvalue")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode


def test_p95_empty_and_values():
    assert _p95([]) is None
    vals = [1, 2, 3, 4, 5, 100]
    # 95th percentile index ceil(6*0.95)-1 = ceil(5.7)-1=6-1=5 -> value 100
    assert _p95(vals) == 100
    vals2 = [10] * 20
    assert _p95(vals2) == 10


def test_build_date_filter_variations():
    clause, params = _build_date_filter("ts", None, None)
    assert clause == ""
    assert params == []
    clause, params = _build_date_filter("ts", "2021-01-01", None)
    assert "ts >= ?" in clause and params == ["2021-01-01"]
    clause, params = _build_date_filter("ts", None, "2021-01-02")
    assert "ts <= ?" in clause and params == ["2021-01-02"]
    clause, params = _build_date_filter("ts", "a", "b")
    assert "AND" in clause and params == ["a", "b"]


def test_fmt_float_and_int_none_and_values():
    assert _fmt_float(None) == "N/A"
    assert _fmt_float(1.23456, decimals=2, suffix="ms") == "1.23ms"
    assert _fmt_int(None) == "N/A"
    assert _fmt_int(5) == "5"


def make_signal_example():
    signals = [
        {"code": "1301", "side": "buy", "target_size": 10, "target_weight": 0.05, "signal_rank": 1},
        {"code": "1332", "side": "sell", "target_size": None, "target_weight": None, "signal_rank": None},
    ]
    return signals


def test_signal_queue_build_format_and_save(tmp_path):
    signals = make_signal_example()
    report = sqr.build_report(signals, report_date=date(2026, 4, 28))
    assert report.total_count == 2
    assert report.status == sqr.STATUS_READY
    cli = sqr.format_cli_summary(report)
    assert "1301" in cli and "1332" in cli
    js = sqr.format_json(report)
    parsed = json.loads(js)
    assert parsed["report_date"] == "2026-04-28"
    # save_report to tmp dir
    run_dir = sqr.save_report(report, output_dir=tmp_path)
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "report.md").exists()
    # invalid report_date
    bad = report
    bad.report_date = "not-a-date"
    with pytest.raises(ValueError):
        sqr.save_report(bad, output_dir=tmp_path)


def test_execution_startup_build_and_format_and_save(tmp_path):
    # craft fake reconcile_result
    class D:
        def __init__(self, code, b, l, diff):
            self.code = code
            self.broker_qty = b
            self.local_qty = l
            self.diff = diff

    rec = SimpleNamespace(
        orders_synced=5,
        orders_no_status=0,
        position_discrepancies=[D("1301", 10, 10, 0), D("1332", 5, 3, 2)],
    )
    report = esr.build_report(rec, startup_date=date(2026, 4, 28))
    assert report.orders_synced == 5
    # since one discrepancy, expect READY_WITH_WARNINGS
    assert report.status == esr.STATUS_READY_WITH_WARNINGS
    cli = esr.format_cli_summary(report)
    assert "Execution Startup Summary" in cli
    js = esr.format_json(report)
    parsed = json.loads(js)
    assert parsed["startup_date"] == "2026-04-28"
    # saving
    out = esr.save_report(report, output_dir=tmp_path)
    assert (out / "summary.json").exists()
    # invalid startup_date -> raise
    bad = report
    bad.startup_date = "bad-date"
    with pytest.raises(ValueError):
        esr.save_report(bad, output_dir=tmp_path)


def test_pre_market_build_and_format_variants():
    r_ready = pmr.build_report(
        report_date=date(2026, 4, 28),
        data_freshness_ok=True,
        signal_queue_pending=1,
        position_count=5,
        stop_flag_exists=False,
        task_scheduler_ready=True,
    )
    assert r_ready.status == pmr.STATUS_READY
    r_blocked = pmr.build_report(
        report_date=date(2026, 4, 28),
        data_freshness_ok=True,
        signal_queue_pending=0,
        position_count=5,
        stop_flag_exists=False,
        task_scheduler_ready=True,
    )
    assert r_blocked.status == pmr.STATUS_BLOCKED
    r_warn = pmr.build_report(
        report_date=date(2026, 4, 28),
        data_freshness_ok=False,
        signal_queue_pending=1,
        position_count=5,
        stop_flag_exists=False,
        task_scheduler_ready=True,
    )
    assert r_warn.status == pmr.STATUS_READY_WITH_WARNINGS
    cli = pmr.format_cli_summary(r_warn)
    assert "Pre-Market Report" in cli
    js = pmr.format_json(r_warn)
    parsed = json.loads(js)
    assert parsed["report_date"] == "2026-04-28"
    # save report with invalid date should raise
    bad = r_warn
    bad.report_date = "2026-99-99"
    with pytest.raises(ValueError):
        pmr.save_report(bad, output_dir=Path("."))


def make_job(name, status="success", warnings=None, errors=None, duration=1.2):
    started = datetime.now(timezone.utc)
    finished = started
    return nbr.JobRunResult(
        job_name=name,
        status=status,
        started_at=started,
        finished_at=finished,
        duration_sec=duration,
        updated_rows={},
        warnings=warnings or [],
        errors=errors or [],
    )


def test_night_batch_determine_generate_and_save(tmp_path):
    jobs = [make_job(n) for n in nbr.MANDATORY_JOBS]
    uc = nbr.UpdateCounts(prices_daily=10, features=5, signals=1, signal_queue=1)
    nd = nbr.NextDaySummary(buy_count=1, sell_count=0, target_symbols=1, expected_orders=1)
    report = nbr.build_report(jobs, uc, nd, run_date=date(2026, 4, 28), target_date=date(2026, 4, 29))
    assert report.status == nbr.STATUS_READY
    s = nbr.format_cli_summary(report)
    assert "Night Batch Report" in s
    js = nbr.format_json(report)
    parsed = json.loads(js)
    assert parsed["run_date"] == "2026-04-28"
    out = nbr.save_report(report, output_dir=tmp_path)
    assert (out / "summary.json").exists()
    # missing mandatory job leads to BLOCKED
    jobs2 = jobs[:-1]
    report2 = nbr.build_report(jobs2, uc, nd, run_date=date(2026, 4, 28), target_date=date(2026, 4, 29))
    assert report2.status == nbr.STATUS_BLOCKED


def test_position_reconciliation_build_and_format_and_warnings():
    entries = [
        prr.PositionEntry(code="1301", broker_qty=10, local_qty=10, diff=0, status=prr.ENTRY_MATCH),
        prr.PositionEntry(code="1332", broker_qty=5, local_qty=3, diff=2, status=prr.ENTRY_MISMATCH),
    ]
    report = prr.build_report(entries, report_date=date(2026, 4, 28))
    assert report.total_count == 2
    assert report.mismatch_count == 1
    assert report.status == prr.STATUS_DISCREPANCY
    cli = prr.format_cli_summary(report)
    assert "Position Reconciliation" in cli
    js = prr.format_json(report)
    parsed = json.loads(js)
    assert parsed["report_date"] == "2026-04-28"
    # markdown includes code and warning
    md = prr.format_markdown(report)
    assert "1301" in md and "1332" in md
    # warnings generation
    warns = prr._generate_warnings(entries)
    assert any("1332" in w for w in warns)


def test_pre_market_collector_date_normalization_and_checks(monkeypatch):
    # mock conn objects with execute returning different types for MAX(date)
    class RowObj:
        def __init__(self, v):
            self.v = v

        def fetchone(self):
            return (self.v,)

    today = date(2026, 4, 28)

    # datetime case
    dt = datetime(2026, 4, 27, 12, 0, 0)
    conn = SimpleNamespace(execute=lambda q, *args, **kw: RowObj(dt))
    assert pmc.check_data_freshness(conn, today) is True

    # string datetime case
    conn = SimpleNamespace(execute=lambda q, *a, **k: RowObj("2026-04-26T00:00:00"))
    assert pmc.check_data_freshness(conn, today) is True

    # old date beyond freshness window
    conn = SimpleNamespace(execute=lambda q, *a, **k: RowObj("2026-04-01"))
    assert pmc.check_data_freshness(conn, today) is False

    # None result
    conn = SimpleNamespace(execute=lambda q, *a, **k: RowObj(None))
    assert pmc.check_data_freshness(conn, today) is False

    # check_signal_queue and check_position_count behavior
    class C:
        def __init__(self, value):
            self.value = value

        def execute(self, q, *args, **kwargs):
            class R:
                def __init__(self, v):
                    self._v = v

                def fetchone(self):
                    return (self._v,)
            return R(self.value)

    c_sqlite = C(3)
    assert pmc.check_signal_queue(c_sqlite, today) == 3
    c_sqlite2 = C(None)
    assert pmc.check_signal_queue(c_sqlite2, today) == 0
    c_pos = C(7)
    assert pmc.check_position_count(c_pos) == 7

    # check_stop_flag: 存在しないパスを渡すと False を返す
    p = Path(__file__).parent / "_nonexistent_stop_flag_for_test"
    assert pmc.check_stop_flag(p) is False

    # check_task_scheduler success and failure via mocking subprocess.run
    good_csv = '"TaskName","Next Run Time","Status"\n"\\\\MyTask","N/A","Ready"\n'
    mock_res = SimpleNamespace(returncode=0, stdout=good_csv, stderr="")
    with mock.patch("subprocess.run", return_value=mock_res):
        assert pmc.check_task_scheduler("whatever") is True

    bad_res = SimpleNamespace(returncode=1, stdout="", stderr="error")
    with mock.patch("subprocess.run", return_value=bad_res):
        assert pmc.check_task_scheduler("whatever") is False

    # simulate FileNotFoundError
    with mock.patch("subprocess.run", side_effect=FileNotFoundError()):
        assert pmc.check_task_scheduler("whatever") is False


def test_run_monitoring_get_poll_interval(monkeypatch):
    from kabusys.run_monitoring import _get_poll_interval, _DEFAULT_POLL_INTERVAL

    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    assert _get_poll_interval() == _DEFAULT_POLL_INTERVAL
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "10")
    assert _get_poll_interval() == 10
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    assert _get_poll_interval() == _DEFAULT_POLL_INTERVAL
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "-5")
    assert _get_poll_interval() == _DEFAULT_POLL_INTERVAL
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "notint")
    assert _get_poll_interval() == _DEFAULT_POLL_INTERVAL


def test_run_execution_pos_value_behaviour(caplog):
    from kabusys.run_execution import _pos_value

    class P:
        def __init__(self, code, qty, current_price, avg_price):
            self.code = code
            self.qty = qty
            self.current_price = current_price
            self.avg_price = avg_price

    p1 = P("0001", 2, 100.0, 90.0)
    assert _pos_value(p1) == 200.0
    p2 = P("0002", 3, None, 50.0)
    assert _pos_value(p2) == 150.0
    p3 = P("0003", 1, 0, 0)
    caplog.clear()
    val = _pos_value(p3)
    assert val == 0.0
    assert any("ポジション評価額を 0 として扱います" in rec.message for rec in caplog.records)


def test_execution_risk_config_parsing(tmp_path):
    # We will test the _load_risk_config function by creating a valid YAML file.
    # Import function lazily to ensure module is available.
    from kabusys.run_execution import _load_risk_config

    valid = """
risk:
  max_position_pct: 0.3
  max_utilization: 0.5
  rate_limit_per_sec: 5
  circuit_breaker_errors: 3
  circuit_breaker_window_sec: 60
  max_drawdown: 0.2
"""
    p = tmp_path / "risk_config.yaml"
    p.write_text(valid, encoding="utf-8")
    cfg = _load_risk_config(p, initial_portfolio_value=100000)
    assert cfg.max_position_pct == pytest.approx(0.3)
    assert cfg.rate_limit_per_sec == 5

    # invalid YAML
    p.write_text("::: bad yaml :::")
    with pytest.raises(ValueError):
        _load_risk_config(p, initial_portfolio_value=1000)

    # missing risk key
    p.write_text("notrisk: {}")
    with pytest.raises(KeyError):
        _load_risk_config(p, initial_portfolio_value=1000)

    # invalid numeric ranges
    bad = """
risk:
  max_position_pct: 2
  max_utilization: 0.5
  rate_limit_per_sec: 0
  circuit_breaker_errors: 0
  circuit_breaker_window_sec: 0
  max_drawdown: -0.1
"""
    p.write_text(bad)
    with pytest.raises(ValueError):
        _load_risk_config(p, initial_portfolio_value=1000)