import os
import json
import sqlite3
import math
from pathlib import Path
from types import SimpleNamespace
from datetime import date, datetime, timezone
import tempfile

import pytest
from unittest import mock

# Config module tests
from kabusys import config as config_mod


def test_parse_env_line_basic_and_comments():
    assert config_mod._parse_env_line("") is None
    assert config_mod._parse_env_line("# comment") is None
    assert config_mod._parse_env_line("export FOO=bar") == ("FOO", "bar")
    # unquoted with inline '#' that is not preceded by space -> keep it
    assert config_mod._parse_env_line("K=foo#bar") == ("K", "foo#bar")
    # inline comment when preceded by space
    assert config_mod._parse_env_line("K=foo #comment") == ("K", "foo")
    # quoted with escaped quote and inline comment ignored
    line = "A='ab\\'c'  # inline"
    assert config_mod._parse_env_line(line) == ("A", "ab'c")
    # no separator
    assert config_mod._parse_env_line("NOSEP") is None
    # empty key
    assert config_mod._parse_env_line("=value") is None


def test_load_env_file_sets_env_vars(tmp_path, monkeypatch):
    p = tmp_path / ".env"
    p.write_text(
        "\n".join(
            [
                "FOO=bar",
                "BAZ='qux\\'x'",
                "IGNORED=will",
                "# comment",
                "EXPORT_TEST=val",
            ]
        ),
        encoding="utf-8",
    )
    # existing env should not be overwritten when override=False
    monkeypatch.delenv("FOO", raising=False)
    os.environ["IGNORED"] = "existing"
    config_mod._load_env_file(p, override=False, protected=frozenset())
    assert os.environ["FOO"] == "bar"
    assert os.environ["BAZ"] == "qux'x"
    # IGNORED existed, should not be overwritten
    assert os.environ["IGNORED"] == "existing"
    # override True should overwrite unless protected
    config_mod._load_env_file(p, override=True, protected=frozenset({"IGNORED"}))
    assert os.environ["FOO"] == "bar"
    assert os.environ["IGNORED"] == "existing"  # protected, still existing


def test_settings_env_and_paths(monkeypatch):
    # ensure defaults are used when env vars not set
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    monkeypatch.delenv("SQLITE_PATH", raising=False)
    s = config_mod.Settings()
    assert isinstance(s.duckdb_path, Path)
    assert str(s.duckdb_path).endswith("data/kabusys.duckdb")
    assert isinstance(s.sqlite_path, Path)
    assert str(s.sqlite_path).endswith("data/monitoring.db")
    # test env validation
    monkeypatch.setenv("KABUSYS_ENV", "live")
    s2 = config_mod.Settings()
    assert s2.env == "live"
    monkeypatch.setenv("KABUSYS_ENV", "invalid-env")
    with pytest.raises(ValueError):
        _ = config_mod.Settings().env
    # log level invalid
    monkeypatch.setenv("LOG_LEVEL", "FOO")
    with pytest.raises(ValueError):
        _ = config_mod.Settings().log_level
    # paper_fill_mode valid/invalid
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert config_mod.Settings().paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "INVALID")
    with pytest.raises(ValueError):
        _ = config_mod.Settings().paper_fill_mode


# run_monitoring tests
from kabusys.run_monitoring import _get_poll_interval


def test_get_poll_interval_env(monkeypatch):
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    # default
    assert _get_poll_interval() == 60
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "10")
    assert _get_poll_interval() == 10
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    assert _get_poll_interval() == 60
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "-5")
    assert _get_poll_interval() == 60
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "abc")
    assert _get_poll_interval() == 60


# run_execution tests (_load_risk_config and _pos_value)
from kabusys.run_execution import _load_risk_config, _pos_value
from pathlib import Path as P


def write_yaml(path: P, data: str):
    path.write_text(data, encoding="utf-8")


def test_load_risk_config_valid(tmp_path):
    yaml_path = tmp_path / "risk_config.yaml"
    yaml_text = """
risk:
  max_position_pct: 0.5
  max_utilization: 0.6
  rate_limit_per_sec: 10
  circuit_breaker_errors: 5
  circuit_breaker_window_sec: 60
  max_drawdown: 0.2
"""
    write_yaml(yaml_path, yaml_text)
    cfg = _load_risk_config(yaml_path, initial_portfolio_value=100000.0)
    # Check numeric fields exist
    assert cfg.max_position_pct == pytest.approx(0.5)
    assert cfg.initial_portfolio_value == 100000.0


def test_load_risk_config_errors(tmp_path):
    missing = tmp_path / "no.yaml"
    with pytest.raises(FileNotFoundError):
        _load_risk_config(missing, initial_portfolio_value=0.0)
    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("!!not: yaml: ::::")
    with pytest.raises(ValueError):
        _load_risk_config(bad_yaml, initial_portfolio_value=0.0)
    no_r_key = tmp_path / "norisk.yaml"
    no_r_key.write_text("notrisk: {}\n", encoding="utf-8")
    with pytest.raises(KeyError):
        _load_risk_config(no_r_key, initial_portfolio_value=0.0)
    # out of range numeric
    yaml_path = tmp_path / "badvals.yaml"
    yaml_text = """
risk:
  max_position_pct: 1.5
  max_utilization: 0.6
  rate_limit_per_sec: 10
  circuit_breaker_errors: 5
  circuit_breaker_window_sec: 60
  max_drawdown: 0.2
"""
    write_yaml(yaml_path, yaml_text)
    with pytest.raises(ValueError):
        _load_risk_config(yaml_path, initial_portfolio_value=0.0)
    # max_position_pct > max_utilization
    yaml_path2 = tmp_path / "badvals2.yaml"
    yaml_text2 = """
risk:
  max_position_pct: 0.7
  max_utilization: 0.6
  rate_limit_per_sec: 10
  circuit_breaker_errors: 5
  circuit_breaker_window_sec: 60
  max_drawdown: 0.2
"""
    write_yaml(yaml_path2, yaml_text2)
    with pytest.raises(ValueError):
        _load_risk_config(yaml_path2, initial_portfolio_value=0.0)
    # bad rate limits
    yaml_path3 = tmp_path / "badvals3.yaml"
    yaml_text3 = """
risk:
  max_position_pct: 0.5
  max_utilization: 0.6
  rate_limit_per_sec: 0
  circuit_breaker_errors: 0
  circuit_breaker_window_sec: 0
  max_drawdown: 0.2
"""
    write_yaml(yaml_path3, yaml_text3)
    with pytest.raises(ValueError):
        _load_risk_config(yaml_path3, initial_portfolio_value=0.0)


def test_pos_value_various():
    ns1 = SimpleNamespace(current_price=100.0, avg_price=90.0, qty=2, code="AAA")
    assert _pos_value(ns1) == 200.0
    ns2 = SimpleNamespace(current_price=0.0, avg_price=50.0, qty=3, code="BBB")
    assert _pos_value(ns2) == 150.0
    ns3 = SimpleNamespace(current_price=None, avg_price=None, qty=10, code="CCC")
    assert _pos_value(ns3) == 0.0
    ns4 = SimpleNamespace(current_price=-10.0, avg_price=0.0, qty=5, code="DDD")
    assert _pos_value(ns4) == 0.0


# Signal Queue report tests
from kabusys.operations import signal_queue_report as sqr
from datetime import timezone as tz


def test_signal_queue_build_and_format_and_save(tmp_path):
    signals = [
        {"code": "1001", "side": "buy", "target_size": None, "target_weight": None, "signal_rank": 1},
        {"code": "2002", "side": "sell", "target_size": 10, "target_weight": 0.1, "signal_rank": 2},
    ]
    rpt = sqr.build_report(signals, report_date=date(2026, 4, 28))
    assert rpt.status == sqr.STATUS_READY
    assert rpt.total_count == 2
    # warnings should include buy_no_size
    assert any("target_size 未設定" in w for w in rpt.warnings)
    txt = sqr.format_cli_summary(rpt)
    assert "Signal Queue Confirmation" in txt
    js = json.loads(sqr.format_json(rpt))
    assert js["total_count"] == 2
    # save_report to tmp dir
    out = sqr.save_report(rpt, output_dir=tmp_path)
    assert (out / "summary.json").exists()
    assert (out / "report.md").exists()
    assert (out / "warnings.json").exists()
    # invalid report_date
    bad = rpt
    bad.report_date = "2026-13-01"
    with pytest.raises(ValueError):
        sqr.save_report(bad, output_dir=tmp_path)


# Paper verification helpers tests
from kabusys.tools import paper_verification_report as pvr


def test_p95_and_build_date_filter_and_format_helpers():
    assert pvr._p95([]) is None
    assert pvr._p95([1.0]) == 1.0
    vals = list(range(1, 21))  # 1..20 -> p95 should pick index ceil(20*0.95)-1 = 19-1? compute by function
    p95 = pvr._p95(vals)
    # Based on implementation, for len=20 idx = ceil(19)-1 = 19-1 = 18 -> value 19
    assert p95 == 19
    clause, params = pvr._build_date_filter("ts", None, None)
    assert clause == ""
    clause2, params2 = pvr._build_date_filter("ts", "2026-01-01", None)
    assert "ts >= ?" in clause2 and params2 == ["2026-01-01"]
    clause3, params3 = pvr._build_date_filter("ts", None, "2026-01-31")
    assert "ts <= ?" in clause3 and params3 == ["2026-01-31"]
    f = pvr._fmt_float(None)
    assert f == "N/A"
    assert pvr._fmt_float(1.2345, 2, " ms") == "1.23 ms"
    assert pvr._fmt_int(None) == "N/A"
    assert pvr._fmt_int(5) == "5"


# Execution Startup report tests
from kabusys.operations import execution_startup_report as esr


def make_reconcile_result(orders_synced=0, orders_no_status=0, position_discrepancies=None):
    if position_discrepancies is None:
        position_discrepancies = []
    # emulate ReconcileResult with necessary attrs
    return SimpleNamespace(
        orders_synced=orders_synced,
        orders_no_status=orders_no_status,
        position_discrepancies=[SimpleNamespace(code=d["code"], broker_qty=d["broker_qty"], local_qty=d["local_qty"], diff=d["diff"]) for d in position_discrepancies],
    )


def test_execution_startup_status_and_warnings_and_format():
    r1 = make_reconcile_result(orders_synced=5, orders_no_status=1, position_discrepancies=[])
    rpt1 = esr.build_report(r1, startup_date=date(2026, 4, 28))
    assert rpt1.status == esr.STATUS_BLOCKED
    assert any("ステータス不明の注文" in w for w in rpt1.warnings)
    # position discrepancy case
    r2 = make_reconcile_result(orders_synced=3, orders_no_status=0, position_discrepancies=[{"code": "A", "broker_qty": 10, "local_qty": 8, "diff": -2}])
    rpt2 = esr.build_report(r2, startup_date=date(2026, 4, 28))
    assert rpt2.status == esr.STATUS_READY_WITH_WARNINGS
    assert any("ポジション差分" in w for w in rpt2.warnings)
    # plain ready
    r3 = make_reconcile_result(orders_synced=1, orders_no_status=0, position_discrepancies=[])
    rpt3 = esr.build_report(r3, startup_date=date(2026, 4, 28))
    assert rpt3.status == esr.STATUS_READY
    # format_json produces valid JSON
    js = json.loads(esr.format_json(rpt3))
    assert js["status"] == "READY"
    # format_markdown contains status string
    md = esr.format_markdown(rpt3)
    assert "Execution Startup Summary" in md


# Night batch report tests
from kabusys.operations import night_batch_report as nbr


def make_job(name, status="success", warnings=None, started=None, finished=None, duration=1.0, updated_rows=None, errors=None):
    if warnings is None:
        warnings = []
    if updated_rows is None:
        updated_rows = {}
    if errors is None:
        errors = []
    started = started or datetime.now(timezone.utc)
    finished = finished or datetime.now(timezone.utc)
    return nbr.JobRunResult(
        job_name=name,
        status=status,
        started_at=started,
        finished_at=finished,
        duration_sec=duration,
        updated_rows=updated_rows,
        warnings=warnings,
        errors=errors,
    )


def test_night_batch_determine_status_and_warnings():
    # missing mandatory job -> BLOCKED
    jobs = [make_job("some_job")]
    uc = nbr.UpdateCounts(prices_daily=10, signals=1, signal_queue=1, features=1, news_articles=0, ai_scores=0, fundamentals=0)
    rep = nbr.build_report(job_results=jobs, update_counts=uc, next_day_summary=nbr.NextDaySummary(), run_date=date(2026,4,28), target_date=date(2026,4,29))
    assert rep.status == nbr.STATUS_BLOCKED
    assert any("必須ジョブが実行されませんでした" in w for w in rep.warnings)
    # mandatory present but one failed -> BLOCKED
    jobs2 = [make_job(n, status="success") for n in nbr.MANDATORY_JOBS]
    jobs2[0] = make_job(nbr.MANDATORY_JOBS[0], status="failed")
    uc2 = nbr.UpdateCounts(prices_daily=10, signals=1, signal_queue=1, features=1, news_articles=0, ai_scores=0, fundamentals=0)
    rep2 = nbr.build_report(job_results=jobs2, update_counts=uc2, next_day_summary=nbr.NextDaySummary(), run_date=date(2026,4,28), target_date=date(2026,4,29))
    assert rep2.status == nbr.STATUS_BLOCKED
    assert any("必須ジョブが失敗しました" in w for w in rep2.warnings)
    # signals == 0 -> READY_WITH_WARNINGS (assuming signal_queue > 0)
    jobs3 = [make_job(n, status="success") for n in nbr.MANDATORY_JOBS]
    uc3 = nbr.UpdateCounts(prices_daily=10, signals=0, signal_queue=1, features=1, news_articles=0, ai_scores=0, fundamentals=0)
    rep3 = nbr.build_report(job_results=jobs3, update_counts=uc3, next_day_summary=nbr.NextDaySummary(), run_date=date(2026,4,28), target_date=date(2026,4,29))
    assert rep3.status == nbr.STATUS_READY_WITH_WARNINGS
    assert any("signals が生成されていません" in w for w in rep3.warnings)
    # all good -> READY
    uc4 = nbr.UpdateCounts(prices_daily=10, signals=2, signal_queue=1, features=1, news_articles=0, ai_scores=0, fundamentals=0)
    rep4 = nbr.build_report(job_results=jobs3, update_counts=uc4, next_day_summary=nbr.NextDaySummary(buy_count=1), run_date=date(2026,4,28), target_date=date(2026,4,29))
    assert rep4.status == nbr.STATUS_READY
    # format_json returns json
    parsed = json.loads(nbr.format_json(rep4))
    assert parsed["status"] == "READY"


# Performance report build_report tests
from kabusys.operations import performance_report as pr


def test_performance_build_report_daily_and_empty():
    # empty rows
    rpt_empty = pr.build_report([], report_type="daily", env="live", from_date=date(2026,4,1), to_date=date(2026,4,30))
    assert rpt_empty.summary["total_trading_days"] == 0
    # daily rows
    Row = pr.DailyRow
    rows = [
        Row(date=date(2026,4,1), env="live", equity=100.0, daily_return=0.01, drawdown=None, cumulative_return=None),
        Row(date=date(2026,4,2), env="live", equity=110.0, daily_return=0.1, drawdown=-0.05, cumulative_return=None),
    ]
    rpt = pr.build_report(rows, report_type="daily", env="live", from_date=date(2026,4,1), to_date=date(2026,4,2))
    assert rpt.summary["total_trading_days"] == 2
    assert "equity_start" in rpt.summary and rpt.summary["equity_start"] == 100.0
    md = pr.format_markdown(rpt)
    assert "運用成績レポート" in md
    # weekly/monthly with WeeklyRow/MonthlyRow
    WR = pr.WeeklyRow
    weekly = [WR(week_label="2026-W17", trading_days=2, equity_start=100.0, equity_end=110.0, weekly_return=0.1, max_drawdown=-0.05, win_days=1)]
    rpt_w = pr.build_report(weekly, report_type="weekly", env="live", from_date=date(2026,4,1), to_date=date(2026,4,2))
    assert rpt_w.summary["total_trading_days"] == 2
    MR = pr.MonthlyRow
    monthly = [MR(month_label="2026-04", trading_days=2, equity_start=100.0, equity_end=110.0, monthly_return=0.1, max_drawdown=-0.05, win_days=1)]
    rpt_m = pr.build_report(monthly, report_type="monthly", env="live", from_date=date(2026,4,1), to_date=date(2026,4,2))
    assert rpt_m.summary["equity_end"] == 110.0
    out = pr.save_report(rpt, output_dir=Path(tempfile.gettempdir()))
    assert out.exists()