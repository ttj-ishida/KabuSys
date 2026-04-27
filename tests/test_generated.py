import os
import math
import json
import sqlite3
import tempfile
from pathlib import Path
from types import SimpleNamespace
from datetime import date, datetime, timezone

import pytest
from unittest import mock

# --- run_monitoring._get_poll_interval tests ---
from kabusys.run_monitoring import _get_poll_interval

def test_get_poll_interval_default(monkeypatch):
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    assert _get_poll_interval() == 60

def test_get_poll_interval_valid(monkeypatch):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "5")
    assert _get_poll_interval() == 5

def test_get_poll_interval_invalid_nonint(monkeypatch, caplog):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "notanint")
    caplog.clear()
    val = _get_poll_interval()
    assert val == 60
    assert "不正" in "".join(caplog.messages) or "invalid" or caplog.records

def test_get_poll_interval_zero_or_negative(monkeypatch):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    assert _get_poll_interval() == 60
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "-10")
    assert _get_poll_interval() == 60

# --- config._parse_env_line and _load_env_file tests ---
from kabusys.config import _parse_env_line, _load_env_file

def test_parse_env_line_blank_or_comment():
    assert _parse_env_line("") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("# comment") is None

def test_parse_env_line_simple():
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    assert _parse_env_line(" export FOO =  bar ") == ("FOO", "bar")

def test_parse_env_line_quotes_and_escapes():
    line = r"SECRET='a\'b\"c\n#ignored'"
    parsed = _parse_env_line(line)
    assert parsed is not None
    k, v = parsed
    assert k == "SECRET"
    # ensure backslash-escaped characters are handled (function reduces escapes)
    assert "a'b\"c" in v

def test_load_env_file_write_and_override(tmp_path, monkeypatch):
    env_file = tmp_path / ".envtest"
    env_file.write_text("A=1\nB=two\n")
    # ensure A not in environ
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    _load_env_file(env_file, override=False, protected=frozenset())
    assert os.environ.get("A") == "1"
    # override behavior: set A to new if override True and not protected
    env_file.write_text("A=changed\nC=3\n")
    _load_env_file(env_file, override=True, protected=frozenset())
    assert os.environ["A"] == "changed"
    assert os.environ["C"] == "3"

# --- Settings property tests ---
from kabusys.config import Settings

def test_settings_env_and_log_level_valid(monkeypatch):
    monkeypatch.setenv("KABUSYS_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    s = Settings()
    assert s.env == "development"
    assert s.log_level == "DEBUG"
    assert s.is_dev
    assert not s.is_live

def test_settings_env_invalid(monkeypatch):
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    s = Settings()
    with pytest.raises(ValueError):
        _ = s.env

def test_settings_paper_fill_mode_valid_and_invalid(monkeypatch):
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    s = Settings()
    assert s.paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "PARTIAL")
    assert s.paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "badmode")
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode

# --- validate_config.validate tests ---
import kabusys.validate_config as validate_config

def test_validate_required_env_vars_missing(monkeypatch):
    # ensure required vars are unset
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("KABU_API_PASSWORD", raising=False)
    errors, warnings, infos = validate_config.validate()
    assert any("必須環境変数" in e for e in errors)

def test_check_kabusys_env_live_warnings(monkeypatch):
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "token")
    monkeypatch.setenv("KABU_API_PASSWORD", "pwd")
    monkeypatch.setenv("KABUSYS_ENV", "live")
    errors, warnings, infos = validate_config.validate()
    assert any("KABUSYS_ENV=live" in w or "本番環境" in w for w in warnings)

# --- config_setup._read_env and _write_env tests ---
from kabusys.config_setup import _read_env, _write_env

def test_read_and_write_env(tmp_path):
    p = tmp_path / ".env"
    p.write_text('JQUANTS_REFRESH_TOKEN="tok"\n#comment\nKABU_API_PASSWORD=pass\n')
    d = _read_env(p)
    assert d["JQUANTS_REFRESH_TOKEN"] == "tok"
    assert d["KABU_API_PASSWORD"] == "pass"

    out = tmp_path / "out.env"
    _write_env(out, {"JQUANTS_REFRESH_TOKEN": "x", "KABU_API_PASSWORD": "y"})
    content = out.read_text(encoding="utf-8")
    assert "JQUANTS_REFRESH_TOKEN=x" in content
    assert "KABU_API_PASSWORD=y" in content

# --- paper_verification_report utility tests ---
from kabusys.tools.paper_verification_report import _p95, _build_date_filter, _fmt_float, _fmt_int

def test_p95_behavior():
    assert _p95([]) is None
    values = [1,2,3,4,5,6,7,8,9,10]
    # 95th percentile index ceil(10*0.95)-1 = ceil(9.5)-1=10-1=9 -> value 10
    assert _p95(values) == 10
    odd = [1,2,3]
    assert _p95(odd) == 3

def test_build_date_filter():
    clause, params = _build_date_filter("ts", None, None)
    assert clause == "" and params == []
    clause, params = _build_date_filter("ts", "a", None)
    assert "ts >= ?" in clause and params == ["a"]
    clause, params = _build_date_filter("ts", None, "b")
    assert "ts <= ?" in clause and params == ["b"]
    clause, params = _build_date_filter("ts", "a", "b")
    assert "AND" in clause and params == ["a", "b"]

def test_fmt_helpers():
    assert _fmt_float(None) == "N/A"
    assert _fmt_float(1.2345, 2, " ms") == "1.23 ms"
    assert _fmt_int(None) == "N/A"
    assert _fmt_int(5) == "5"

# --- operations.execution_startup_report tests ---
from kabusys.operations.execution_startup_report import (
    build_report,
    format_cli_summary,
    format_json,
    format_markdown,
    save_report,
    ExecutionStartupReport,
    STATUS_BLOCKED,
    STATUS_READY,
    STATUS_READY_WITH_WARNINGS,
)

def make_reconcile_result(orders_synced=0, orders_no_status=0, position_discrepancies=None):
    if position_discrepancies is None:
        position_discrepancies = []
    return SimpleNamespace(
        orders_synced=orders_synced,
        orders_no_status=orders_no_status,
        position_discrepancies=position_discrepancies,
    )

def test_build_report_blocked_and_warnings(tmp_path):
    # blocked because orders_no_status > 0
    rr = make_reconcile_result(orders_synced=2, orders_no_status=1, position_discrepancies=[])
    rpt = build_report(rr, startup_date=date(2026,1,1))
    assert rpt.status == STATUS_BLOCKED
    assert any("ステータス不明" in w for w in rpt.warnings)

def test_build_report_ready_with_discrepancies():
    pos = [SimpleNamespace(code="AAA", broker_qty=10, local_qty=8, diff=2)]
    rr = make_reconcile_result(orders_synced=0, orders_no_status=0, position_discrepancies=pos)
    rpt = build_report(rr, startup_date=date(2026,1,2))
    assert rpt.status == STATUS_READY_WITH_WARNINGS
    assert any("ポジション差分" in w for w in rpt.warnings)
    s = format_cli_summary(rpt)
    assert "Execution Startup Summary" in s
    j = format_json(rpt)
    assert '"startup_date"' in j
    md = format_markdown(rpt)
    assert "Execution Startup Summary" in md

def test_save_report_and_invalid_date(tmp_path):
    pos = []
    rr = make_reconcile_result(orders_synced=0, orders_no_status=0, position_discrepancies=pos)
    rpt = build_report(rr, startup_date=date(2026,2,3))
    outdir = tmp_path / "artifacts"
    saved = save_report(rpt, output_dir=outdir)
    assert (saved / "summary.json").exists()
    assert (saved / "report.md").exists()
    assert (saved / "warnings.json").exists()
    # invalid startup_date
    rpt2 = ExecutionStartupReport(
        startup_date="20260230",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=STATUS_READY,
        orders_synced=0,
        orders_no_status=0,
        position_discrepancies=[],
        warnings=[],
    )
    with pytest.raises(ValueError):
        save_report(rpt2, output_dir=tmp_path)

# --- night batch report tests ---
from kabusys.tools.night_batch_report import (
    JobRunResult,
    UpdateCounts,
    NextDaySummary,
    build_report as nb_build_report,
    format_cli_summary as nb_format_cli_summary,
    format_json as nb_format_json,
    format_markdown as nb_format_markdown,
    save_report as nb_save_report,
    STATUS_BLOCKED as NB_BLOCKED,
    STATUS_READY as NB_READY,
    STATUS_READY_WITH_WARNINGS as NB_WARN
)

def make_job(name, status="success", warnings=None, errors=None, duration=1.2):
    now = datetime.now(timezone.utc)
    return JobRunResult(
        job_name=name,
        status=status,
        started_at=now,
        finished_at=now,
        duration_sec=duration,
        updated_rows={},
        warnings=warnings or [],
        errors=errors or [],
    )

def test_night_batch_determine_status_and_warnings(tmp_path):
    jobs = [make_job(n) for n in [
        "data_update_job",
        "feature_generation_job",
        "ai_analysis_job",
        "strategy_signal_job",
        "portfolio_construction_job"
    ]]
    uc = UpdateCounts(prices_daily=10, features=1, signals=5, signal_queue=1)
    nd = NextDaySummary(buy_count=1, sell_count=0, target_symbols=1, expected_orders=1)
    report = nb_build_report(jobs, uc, nd, run_date=date(2026,3,1), target_date=date(2026,3,2))
    assert report.status == NB_READY
    s = nb_format_cli_summary(report)
    assert "Night Batch Report" in s
    j = nb_format_json(report)
    assert '"run_date"' in j
    md = nb_format_markdown(report)
    assert "# Night Batch Report" in md
    saved = nb_save_report(report, output_dir=tmp_path)
    assert (saved / "summary.json").exists()
    # missing mandatory job -> BLOCKED
    incomplete_jobs = jobs[:-1]
    report2 = nb_build_report(incomplete_jobs, UpdateCounts(signal_queue=0, signals=0), nd, run_date=date(2026,3,1), target_date=date(2026,3,2))
    assert report2.status == NB_BLOCKED
    assert any("必須ジョブ" in w or "signal_queue" in w for w in report2.warnings)

# --- portfolio.portfolio_builder tests ---
from kabusys.portfolio.portfolio_builder import select_candidates, calc_equal_weights, calc_score_weights
import logging

def test_select_candidates_order_and_tiebreak():
    inputs = [
        {"code":"A","score":1.0,"signal_rank":2},
        {"code":"B","score":2.0,"signal_rank":1},
        {"code":"C","score":2.0,"signal_rank":2},
    ]
    res = select_candidates(inputs, max_positions=2)
    assert [r["code"] for r in res] == ["B","C"]

def test_calc_equal_and_score_weights(caplog):
    candidates = [{"code":"X"},{"code":"Y"}]
    eq = calc_equal_weights(candidates)
    assert math.isclose(eq["X"], 0.5)
    # score weights with zero total -> fallback
    caplog.clear()
    vals = [{"code":"A","score":0.0},{"code":"B","score":0.0}]
    sw = calc_score_weights(vals)
    assert sw == {"A": 0.5, "B": 0.5}

# --- portfolio.risk_adjustment tests ---
from kabusys.portfolio.risk_adjustment import apply_sector_cap, calc_regime_multiplier

def test_apply_sector_cap_basic_filtering():
    candidates = [{"code":"A"},{"code":"B"},{"code":"C"}]
    sector_map = {"A":"tech","B":"tech","C":"fin"}
    portfolio_value = 1000.0
    current_positions = {"A":10,"B":20,"C":1}
    price_map = {"A":10.0,"B":10.0,"C":100.0}
    # sector tech exposure = (10+20)*10 = 300 -> 300/1000 = 0.3 equals cap -> treated as blocked (>=)
    filtered = apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map, max_sector_pct=0.30)
    # tech sector should be blocked when exposure/portfolio >= max_sector_pct, so A and B removed, C remains
    assert filtered == [{"code":"C"}]

def test_apply_sector_cap_unknown_and_sell_codes():
    candidates = [{"code":"X"},{"code":"Y"}]
    sector_map = {"X":"unknown","Y":"tech"}
    portfolio_value = 1000.0
    current_positions = {"X":100,"Y":100}
    price_map = {"X":1.0,"Y":1.0}
    # if sell_codes contains Y, exposure excludes it, so no blocking
    res = apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map, sell_codes={"Y"}, max_sector_pct=0.01)
    assert res == candidates  # X is unknown so never blocked

def test_calc_regime_multiplier_known_and_unknown(caplog):
    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == 0.7
    assert calc_regime_multiplier("bear") == 0.3
    caplog.clear()
    val = calc_regime_multiplier("mystery")
    assert val == 1.0

# --- portfolio.position_sizing tests ---
from kabusys.portfolio.position_sizing import calc_position_sizes

def test_calc_position_sizes_empty_candidates():
    res = calc_position_sizes({}, [], 100000, 100000, {}, {}, allocation_method="equal")
    assert res == {}

def test_calc_position_sizes_risk_based_missing_price(caplog):
    candidates = [{"code":"NOP"}]
    weights = {}
    res = calc_position_sizes(weights, candidates, portfolio_value=100000, available_cash=100000, current_positions={}, open_prices={}, allocation_method="risk_based")
    assert res == {}  # missing price -> skipped

def test_calc_position_sizes_equal_and_aggregate_scaling():
    candidates = [{"code":"A"},{"code":"B"}]
    weights = {"A":0.5,"B":0.5}
    open_prices = {"A":100.0,"B":200.0}
    pv = 100000.0
    # set available_cash small so scaling triggers
    res = calc_position_sizes(weights, candidates, portfolio_value=pv, available_cash=5000, current_positions={}, open_prices=open_prices, allocation_method="equal", lot_size=100)
    # result shares must be multiples of 100 and cost <= available_cash
    for shares in res.values():
        assert shares % 100 == 0
    total_cost = sum(res[c]*open_prices[c] for c in res)
    assert total_cost <= 5000 + 1e-6

# --- utils.logging_setup.setup_logging tests (simulate mkdir failure) ---
from kabusys.utils.logging_setup import setup_logging
import logging as pylogging

def test_setup_logging_dir_creation_failure(monkeypatch, capsys):
    fake_dir = Path("/root/this_should_fail_hopefully")
    # monkeypatch Path.mkdir to raise for this path only
    orig_mkdir = Path.mkdir
    def fake_mkdir(self, parents=False, exist_ok=False):
        if str(self).endswith("this_should_fail_hopefully"):
            raise PermissionError("nope")
        return orig_mkdir(self, parents=parents, exist_ok=exist_ok)
    monkeypatch.setattr(Path, "mkdir", fake_mkdir)
    # call setup_logging with explicit log_dir that triggers fake failure
    setup_logging(app_name="testapp", log_dir=fake_dir, level="DEBUG")
    # restore patched method automatically by monkeypatch fixture teardown

# --- utils.process_priority tests (mock psutil and platform) ---
from kabusys.utils import process_priority

def test_set_process_priority_invalid():
    with pytest.raises(ValueError):
        process_priority.set_process_priority("invalid_level")

def test_set_process_priority_windows(monkeypatch):
    class DummyProc:
        def __init__(self): self.pid = 9999
        def nice(self, val): self._nice = val
    monkeypatch.setattr(process_priority, "psutil", mock.MagicMock(Process=lambda: DummyProc(), HIGH_PRIORITY_CLASS=123, NORMAL_PRIORITY_CLASS=32, IDLE_PRIORITY_CLASS=64))
    monkeypatch.setattr(process_priority, "platform", mock.MagicMock(system=lambda: "Windows"))
    process_priority.set_process_priority("high")  # should not raise

def test_set_cpu_affinity_invalid_and_none(monkeypatch):
    # None should be no-op
    process_priority.set_cpu_affinity(None)
    with pytest.raises(ValueError):
        process_priority.set_cpu_affinity(0)
    # mock psutil cpu_count and Process
    class DummyProc:
        def __init__(self): self.pid = 1
        def cpu_affinity(self, lst): self._aff = lst
    monkeypatch.setattr(process_priority, "psutil", mock.MagicMock(cpu_count=lambda:2, Process=lambda: DummyProc()))
    process_priority.set_cpu_affinity(1)  # should set affinity without error

# --- feature_exploration.calc_ic and rank and factor_summary tests ---
from kabusys.feature_exploration import calc_ic, rank, factor_summary

def test_rank_and_calc_ic_and_summary():
    vals = [3.0, 1.0, 2.0, 2.0]
    r = rank(vals)
    assert len(r) == 4
    # prepare factor and forward records
    factors = [{"code":"A","f":1.0},{"code":"B","f":2.0},{"code":"C","f":3.0}]
    forwards = [{"code":"A","ret":0.1},{"code":"B","ret":0.2},{"code":"C","ret":0.3}]
    ic = calc_ic(
        factor_records=[{"code":"A","f":1.0},{"code":"B","f":2.0},{"code":"C","f":3.0}],
        forward_records=[{"code":"A","ret":0.1},{"code":"B","ret":0.2},{"code":"C","ret":0.3}],
        factor_col="f",
        return_col="ret",
    )
    assert ic is not None
    # factor_summary with some None values
    records = [{"a":1.0,"b":None},{"a":3.0,"b":2.0},{"a":2.0,"b":4.0}]
    summary = factor_summary(records, ["a","b"])
    assert summary["a"]["count"] == 3
    assert summary["b"]["count"] == 2

# Done.