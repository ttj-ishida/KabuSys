import os
import sqlite3
import json
import math
import tempfile
from pathlib import Path
from datetime import date, datetime, timezone
import pytest
from unittest import mock

# Tests for kabusys.config (_parse_env_line, _load_env_file, Settings)
from kabusys import config as config_mod
from kabusys.run_monitoring import _get_poll_interval
from kabusys.run_execution import _pos_value, _load_risk_config
from kabusys.operations import signal_queue_report as sqr
from kabusys.tools import paper_verification_report as pvr
from kabusys.operations import execution_startup_report as esr
from kabusys.operations import market_close_report as mcr


# -------------------------
# config._parse_env_line
# -------------------------
@pytest.mark.parametrize(
    "line,expected",
    [
        ("", None),
        ("# comment", None),
        ("export KEY=val", ("KEY", "val")),
        ("KEY = value", ("KEY", "value")),
        ("KEY='a\\'b'", ("KEY", "a'b")),
        ('KEY="a\\"b"', ("KEY", 'a"b')),
        ("KEY=unquoted#notacomment", ("KEY", "unquoted#notacomment")),
        ("KEY=unquoted #comment", ("KEY", "unquoted")),
        ("=noval", None),
        ("NOVAL", None),
    ],
)
def test_parse_env_line_various(line, expected):
    assert config_mod._parse_env_line(line) == expected


# -------------------------
# config._load_env_file
# -------------------------
def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    p = tmp_path / ".envtest"
    p.write_text("A=1\nB=2\nP=protected\n")
    # set existing OS env and protected set
    monkeypatch.setenv("A", "osval")
    protected = frozenset(os.environ.keys())
    # override=False should not overwrite A, should set B and P only if not present
    config_mod._load_env_file(p, override=False, protected=protected)
    assert os.environ.get("A") == "osval"
    assert os.environ.get("B") == "2"
    assert os.environ.get("P") == "protected"
    # Now test override=True but protected blocks overwriting A
    p.write_text("A=changed\nC=3\n")
    config_mod._load_env_file(p, override=True, protected=protected)
    assert os.environ.get("A") == "osval"  # protected prevented overwrite
    assert os.environ.get("C") == "3"


# -------------------------
# Settings: env, paper_fill_mode, log_level validations
# -------------------------
def test_settings_env_valid_and_invalid(monkeypatch):
    # valid
    monkeypatch.setenv("KABUSYS_ENV", "development")
    s = config_mod.Settings()
    assert s.env == "development"
    # invalid
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env_value")
    s2 = config_mod.Settings()
    with pytest.raises(ValueError):
        _ = s2.env


def test_settings_paper_fill_mode_valid_invalid(monkeypatch):
    monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
    s = config_mod.Settings()
    assert s.paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    assert s.paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "BADMODE")
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode


def test_settings_log_level_validation(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    s = config_mod.Settings()
    assert s.log_level == "INFO"
    monkeypatch.setenv("LOG_LEVEL", "WRONG")
    with pytest.raises(ValueError):
        _ = s.log_level


# -------------------------
# run_monitoring._get_poll_interval
# -------------------------
def test_get_poll_interval_default(monkeypatch):
    monkeypatch.delenv("MONITOR_POLL_INTERVAL", raising=False)
    assert _get_poll_interval() == 60


def test_get_poll_interval_valid(monkeypatch):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "5")
    assert _get_poll_interval() == 5


def test_get_poll_interval_invalid_values(monkeypatch):
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "0")
    assert _get_poll_interval() == 60
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "-10")
    assert _get_poll_interval() == 60
    monkeypatch.setenv("MONITOR_POLL_INTERVAL", "notanint")
    assert _get_poll_interval() == 60


# -------------------------
# run_execution._pos_value
# -------------------------
class _DummyPos:
    def __init__(self, qty, current_price=None, avg_price=None, code="X"):
        self.qty = qty
        self.current_price = current_price
        self.avg_price = avg_price
        self.code = code


def test_pos_value_current_price_used():
    p = _DummyPos(qty=10, current_price=50.0, avg_price=40.0)
    assert _pos_value(p) == 10 * 50.0


def test_pos_value_avg_price_used_when_current_none():
    p = _DummyPos(qty=2, current_price=None, avg_price=25.0)
    assert _pos_value(p) == 2 * 25.0


def test_pos_value_zero_or_negative_price_warns_and_zero(monkeypatch):
    p1 = _DummyPos(qty=5, current_price=0, avg_price=0)
    assert _pos_value(p1) == 0.0
    p2 = _DummyPos(qty=3, current_price=-10, avg_price=100)
    # current_price negative -> avg_price used (100) because current_price not None and >0 check fails -> falls back to avg_price
    assert _pos_value(p2) == 3 * 100.0
    p3 = _DummyPos(qty=1, current_price=None, avg_price=None)
    assert _pos_value(p3) == 0.0


# -------------------------
# run_execution._load_risk_config
# -------------------------
def _write_yaml(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def test_load_risk_config_valid(tmp_path):
    ym = tmp_path / "risk.yaml"
    content = """
risk:
  max_position_pct: 0.5
  max_utilization: 0.6
  rate_limit_per_sec: 5
  circuit_breaker_errors: 3
  circuit_breaker_window_sec: 60
  max_drawdown: 0.2
"""
    _write_yaml(ym, content)
    cfg = _load_risk_config(ym, initial_portfolio_value=100000.0)
    # check attributes exist and types
    assert getattr(cfg, "max_position_pct") == pytest.approx(0.5)
    assert getattr(cfg, "initial_portfolio_value") == 100000.0


def test_load_risk_config_missing_file(tmp_path):
    ym = tmp_path / "noexist.yaml"
    with pytest.raises(FileNotFoundError):
        _load_risk_config(ym, 1000.0)


def test_load_risk_config_bad_yaml(tmp_path):
    ym = tmp_path / "bad.yaml"
    ym.write_text("::: not yaml :::")
    with pytest.raises(ValueError):
        _load_risk_config(ym, 1000.0)


def test_load_risk_config_missing_keys(tmp_path):
    ym = tmp_path / "nokey.yaml"
    ym.write_text("notrisk: {}\n")
    with pytest.raises(KeyError):
        _load_risk_config(ym, 1000.0)


def test_load_risk_config_invalid_ranges(tmp_path):
    ym = tmp_path / "badvals.yaml"
    # max_position_pct > max_utilization
    ym.write_text(
        """
risk:
  max_position_pct: 0.9
  max_utilization: 0.5
  rate_limit_per_sec: 1
  circuit_breaker_errors: 1
  circuit_breaker_window_sec: 1
  max_drawdown: 0.5
"""
    )
    with pytest.raises(ValueError):
        _load_risk_config(ym, 1000.0)
    # rate_limit_per_sec < 1
    ym.write_text(
        """
risk:
  max_position_pct: 0.5
  max_utilization: 0.6
  rate_limit_per_sec: 0
  circuit_breaker_errors: 1
  circuit_breaker_window_sec: 1
  max_drawdown: 0.5
"""
    )
    with pytest.raises(ValueError):
        _load_risk_config(ym, 1000.0)


# -------------------------
# signal_queue_report build/format/save
# -------------------------
def test_signal_queue_build_and_formats_and_save(tmp_path):
    # create signals list with buy lacking target_size
    signals = [
        {"code": "1111", "side": "buy", "target_size": None, "target_weight": 0.1, "signal_rank": 1},
        {"code": "2222", "side": "sell", "target_size": 50, "target_weight": None, "signal_rank": 2},
    ]
    rpt = sqr.build_report(signals, report_date=date(2026, 4, 28))
    assert rpt.status == sqr.STATUS_READY
    # warnings should include BUY missing target_size
    assert any("target_size" in w for w in rpt.warnings)
    # format_json valid json
    js = sqr.format_json(rpt)
    parsed = json.loads(js)
    assert parsed["report_date"] == "2026-04-28"
    # format_cli_summary returns string containing code lines
    cli = sqr.format_cli_summary(rpt)
    assert "1111" in cli and "2222" in cli
    # save_report writes files
    outdir = sqr.save_report(rpt, output_dir=tmp_path)
    assert (outdir / "summary.json").exists()
    assert (outdir / "report.md").exists()
    assert (outdir / "warnings.json").exists()


def test_signal_queue_save_invalid_date_raises(tmp_path):
    # create a fake report with invalid date
    rpt = sqr.SignalQueueReport(
        report_date="bad-date",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=sqr.STATUS_EMPTY,
        total_count=0,
        buy_count=0,
        sell_count=0,
        signals=[],
        warnings=[],
    )
    with pytest.raises(ValueError):
        sqr.save_report(rpt, output_dir=tmp_path)


# -------------------------
# paper_verification_report utilities
# -------------------------
def test_p95_empty_and_values():
    assert pvr._p95([]) is None
    vals = [1, 2, 3, 4, 100]
    # 95th percentile index ceil(5*0.95)-1 = ceil(4.75)-1=5-1=4 -> index 4 -> 100
    assert pvr._p95(vals) == 100


def test_build_date_filter():
    clause, params = pvr._build_date_filter("ts", "2020-01-01", None)
    assert "ts >= ?" in clause and params == ["2020-01-01"]
    clause2, params2 = pvr._build_date_filter("ts", None, "2020-12-31")
    assert "ts <= ?" in clause2 and params2 == ["2020-12-31"]
    clause3, params3 = pvr._build_date_filter("ts", None, None)
    assert clause3 == "" and params3 == []


def test_fmt_functions():
    assert pvr._fmt_float(None) == "N/A"
    assert pvr._fmt_float(12.3456, 2, "ms") == "12.35ms"
    assert pvr._fmt_int(None) == "N/A"
    assert pvr._fmt_int(5) == "5"


# -------------------------
# execution_startup_report build/report behaviors
# -------------------------
class _FakeDiscrep:
    def __init__(self, code, broker_qty, local_qty, diff):
        self.code = code
        self.broker_qty = broker_qty
        self.local_qty = local_qty
        self.diff = diff


class _FakeReconcileResult:
    def __init__(self, orders_synced, orders_no_status, position_discrepancies):
        self.orders_synced = orders_synced
        self.orders_no_status = orders_no_status
        self.position_discrepancies = position_discrepancies


def test_execution_startup_report_statuses_and_warnings():
    # BLOCKED when orders_no_status > 0
    res_blocked = _FakeReconcileResult(10, 1, [])
    rpt = esr.build_report(res_blocked, startup_date=date(2026, 4, 28))
    assert rpt.status == esr.STATUS_BLOCKED
    assert any("ステータス不明" in w or "ステータス不明" in w for w in rpt.warnings)
    # READY_WITH_WARNINGS when discrepancies exist but orders_no_status == 0
    disc = [_FakeDiscrep("AAA", 10, 8, -2)]
    res_warn = _FakeReconcileResult(5, 0, disc)
    rpt2 = esr.build_report(res_warn, startup_date=date(2026, 4, 28))
    assert rpt2.status == esr.STATUS_READY_WITH_WARNINGS
    assert any("ポジション差分" in w for w in rpt2.warnings)
    # READY otherwise
    res_ready = _FakeReconcileResult(0, 0, [])
    rpt3 = esr.build_report(res_ready, startup_date=date(2026, 4, 28))
    assert rpt3.status == esr.STATUS_READY


def test_execution_startup_save_invalid_startup_date(tmp_path):
    # create a report with invalid date string
    rpt = esr.ExecutionStartupReport(
        startup_date="bad-date",
        generated_at=datetime.now(timezone.utc).isoformat(),
        status=esr.STATUS_READY,
        orders_synced=0,
        orders_no_status=0,
        position_discrepancies=[],
        warnings=[],
    )
    with pytest.raises(ValueError):
        esr.save_report(rpt, output_dir=tmp_path)


# -------------------------
# market_close_report format helpers
# -------------------------
def test_fmt_return_and_yen():
    assert mcr._fmt_return(None) == "N/A"
    assert mcr._fmt_return(0.05) == "+5.00%"
    assert mcr._fmt_return(-0.01) == "-1.00%"
    assert mcr._fmt_yen(None) == "N/A"
    assert mcr._fmt_yen(123456.78) == "+¥123,456"
    assert mcr._fmt_yen(-500) == "¥-500"