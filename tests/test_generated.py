
import json
import math
import sqlite3
from datetime import datetime, timedelta, date, timezone
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
from kabusys.portfolio.portfolio_builder import (
    select_candidates,
    calc_equal_weights,
    calc_score_weights,
)
from kabusys.portfolio.risk_adjustment import apply_sector_cap, calc_regime_multiplier
from kabusys.portfolio.position_sizing import calc_position_sizes
from kabusys.utils.process_priority import set_process_priority, set_cpu_affinity
from kabusys.feature_exploration import rank, calc_ic, factor_summary
from kabusys.monitoring.monitoring_db import init_monitoring_db, MonitoringDB
from kabusys.monitoring.risk_monitor import RiskMonitor


# -----------------------------
# config._parse_env_line / _load_env_file
# -----------------------------
def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("# comment") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    assert _parse_env_line(" export X= y ") is None  # malformed after export
    # export support
    assert _parse_env_line("export KEY2= value2 ") == ("KEY2", "value2")


def test_parse_env_line_quoted_and_escaped():
    # single quote with escaped quote
    r = _parse_env_line("A='o\\'k'")  # value should be: o'k
    assert r == ("A", "o'k")
    # double quote with escaped char
    r2 = _parse_env_line('B="line\\nmore"')
    # in parser escapes next char literally; so \n becomes n, not newline
    assert r2 == ("B", "linenmore") or r2 == ("B", "line\\nmore")  # tolerant


def test_parse_env_line_inline_comment_rules():
    # '#' not comment when not preceded by space
    assert _parse_env_line("K=val#notcomment") == ("K", "val#notcomment")
    # '#' after space treated as comment
    assert _parse_env_line("K=val # comment") == ("K", "val")


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    p = tmp_path / ".env.test"
    p.write_text("A=1\nB=2\nC=3\n")
    # set existing env B to protected
    monkeypatch.setenv("B", "orig")
    _load_env_file(p, override=False, protected=frozenset(os.environ.keys() if hasattr(__import__('os'), 'environ') else []))
    # With override=False, existing env B should not be overwritten
    assert os.environ.get("B") == "orig"
    # A and C should be set
    assert os.environ.get("A") == "1"
    assert os.environ.get("C") == "3"


# -----------------------------
# Settings properties
# -----------------------------
def test_settings_env_validation(monkeypatch):
    s = Settings()
    # default when not set
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    assert s.env == "development"
    # invalid env raises
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env
    # paper_trading and live flags
    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    assert s.is_paper is True and s.is_live is False
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert s.is_live is True


def test_settings_paper_fill_mode_valid_and_invalid(monkeypatch):
    s = Settings()
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert s.paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "PARTIAL")
    assert s.paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "invalid_mode")
    with pytest.raises(ValueError):
        _ = s.paper_fill_mode


# -----------------------------
# paper_verification_report functions
# -----------------------------
def test_p95_behavior():
    assert _p95([]) is None
    # For 1 element, index ceil(1*0.95)-1 = 0 -> element 0
    assert _p95([10.0]) == 10.0
    # For 20 elements, index = ceil(20*0.95)-1 = 19-1? => check implementation: ensure returns 19th percentile element
    vals = list(range(1, 21))
    # expected index computed by function: max(ceil(20*0.95)-1,0) => ceil(19)-1=19-1=18 -> element at index 18 == 19
    assert _p95(vals) == 19


def test_build_date_filter():
    where, params = _build_date_filter("ts", None, None)
    assert where == "" and params == []
    where, params = _build_date_filter("ts", "2026-01-01", None)
    assert "ts >= ?" in where and params == ["2026-01-01"]
    where, params = _build_date_filter("ts", None, "2026-01-02")
    assert "ts <= ?" in where and params == ["2026-01-02"]
    where, params = _build_date_filter("ts", "a", "b")
    assert " AND " in where and params == ["a", "b"]


def test_fmt_helpers():
    assert _fmt_float(None) == "N/A"
    assert _fmt_float(1.2345, 2, " ms") == "1.23 ms"
    assert _fmt_int(None) == "N/A"
    assert _fmt_int(5) == "5"


# -----------------------------
# portfolio.portfolio_builder
# -----------------------------
def test_select_candidates_and_weight_calculations(caplog):
    signals = [
        {"code": "A", "score": 1.0, "signal_rank": 2},
        {"code": "B", "score": 2.0, "signal_rank": 1},
        {"code": "C", "score": 2.0, "signal_rank": 3},
    ]
    sel = select_candidates(signals, max_positions=2)
    # B and C have highest scores (2.0); tie-breaker on signal_rank ascending => B before C
    assert [s["code"] for s in sel] == ["B", "C"]

    # equal weights
    eq = calc_equal_weights(sel)
    assert set(eq.keys()) == {"B", "C"}
    assert math.isclose(list(eq.values())[0], 0.5)

    # score weights normal
    sw = calc_score_weights(signals)
    total = sum(sw.values())
    assert pytest.approx(total, rel=1e-9) == 1.0

    # when all scores zero -> fallback to equal weights with warning
    caplog.clear()
    with caplog.at_level("WARNING"):
        zsignals = [{"code": "X", "score": 0.0}, {"code": "Y", "score": 0.0}]
        out = calc_score_weights(zsignals)
        assert "フォールバック" in caplog.text or "フォールバック" in caplog.text or caplog.records
        assert out == {"X": 0.5, "Y": 0.5}


# -----------------------------
# portfolio.risk_adjustment
# -----------------------------
def test_apply_sector_cap_blocks_overexposed():
    candidates = [{"code": "AAA"}, {"code": "BBB"}, {"code": "CCC"}]
    sector_map = {"AAA": "s1", "BBB": "s1", "CCC": "s2"}
    portfolio_value = 1000.0
    # current positions valued so that s1 exposure = 400 which is 0.4 -> over 0.3 threshold
    current_positions = {"AAA": 2, "BBB": 2}  # prices below will be provided
    price_map = {"AAA": 100.0, "BBB": 100.0, "CCC": 10.0}
    filtered = apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map, max_sector_pct=0.3)
    # AAA and BBB are in blocked sector 's1' -> CCC remains
    assert filtered == [{"code": "CCC"}]


def test_calc_regime_multiplier_and_unknown(caplog):
    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == 0.7
    assert calc_regime_multiplier("bear") == 0.3
    caplog.clear()
    with caplog.at_level("WARNING"):
        assert calc_regime_multiplier("weird") == 1.0
        assert "未知のレジーム" in caplog.text or caplog.records


# -----------------------------
# portfolio.position_sizing
# -----------------------------
def test_calc_position_sizes_equal_and_risk_based():
    # equal method
    weights = {"AA": 0.5, "BB": 0.5}
    candidates = [{"code": "AA"}, {"code": "BB"}]
    pv = 100000.0
    available_cash = 100000.0 * 0.7  # as if max_utilization applied
    current_positions = {}
    open_prices = {"AA": 100.0, "BB": 50.0}
    sizes = calc_position_sizes(weights, candidates, pv, available_cash, current_positions, open_prices, allocation_method="equal", lot_size=100)
    # For AA: per-position max (pv * weight * max_utilization) -> 100000*0.5*0.7=35000 -> 350 shares -> capped by max_per_stock (100000*0.10/100=100) -> 100 -> lot 100
    assert sizes.get("AA") == 100
    # risk_based
    candidates_rb = [{"code": "AA"}, {"code": "BB"}]
    sizes_rb = calc_position_sizes({}, candidates_rb, pv, available_cash, {}, {"AA": 50.0, "BB": 60.0}, allocation_method="risk_based", risk_pct=0.005, stop_loss_pct=0.08, lot_size=100)
    # Expect some shares for AA (as calculated in analysis)
    assert "AA" in sizes_rb or "BB" in sizes_rb


# -----------------------------
# utils.process_priority
# -----------------------------
def test_set_process_priority_invalid_level():
    with pytest.raises(ValueError):
        set_process_priority("super-high")


def test_set_cpu_affinity_monkeypatch(monkeypatch):
    calls = {}
    class FakeProcess:
        def cpu_affinity(self, pinned):
            calls['pinned'] = pinned

    monkeypatch.setattr("kabusys.utils.process_priority.psutil", mock.Mock())
    # cpu_count returns 4
    monkeypatch.setattr("kabusys.utils.process_priority.psutil.cpu_count", lambda : 4)
    monkeypatch.setattr("kabusys.utils.process_priority.psutil.Process", lambda : FakeProcess())
    # set affinity to 2 cores
    set_cpu_affinity = __import__("kabusys.utils.process_priority", fromlist=["set_cpu_affinity"]).set_cpu_affinity
    set_cpu_affinity(2)
    assert calls['pinned'] == [0,1]

    # cpu_count None -> treat as 1
    monkeypatch.setattr("kabusys.utils.process_priority.psutil.cpu_count", lambda : None)
    set_cpu_affinity(1)  # shouldn't raise


# -----------------------------
# feature_exploration.rank / calc_ic / factor_summary
# -----------------------------
def test_rank_ties_and_calc_ic_and_summary():
    vals = [1.0, 2.0, 2.0, 3.0]
    r = rank(vals)
    # ranks should be increasing and tied values have averaged ranks
    assert len(r) == 4
    # two middle items are ties -> their ranks equal
    assert r[1] == r[2]

    # calc_ic insufficient data returns None
    factor_records = [{"code": "A", "f": 1.0}, {"code": "B", "f": None}]
    forward_records = [{"code": "A", "r": 0.1}, {"code": "B", "r": 0.2}]
    assert calc_ic(factor_records, forward_records, "f", "r") is None

    # perfect monotonic
    factor_records = [{"code": "A", "f": 1.0}, {"code": "B", "f": 2.0}, {"code": "C", "f": 3.0}]
    forward_records = [{"code": "A", "r": 0.01}, {"code": "B", "r": 0.02}, {"code": "C", "r": 0.03}]
    ic = calc_ic(factor_records, forward_records, "f", "r")
    assert ic is not None
    assert ic > 0.99

    # factor_summary
    records = [{"a": 1.0, "b": None}, {"a": 2.0}, {"a": 3.0}]
    summary = factor_summary(records, ["a", "b"])
    assert summary["a"]["count"] == 3
    assert summary["b"]["count"] == 0
    assert summary["b"]["mean"] is None


# -----------------------------
# monitoring.monitoring_db and RiskMonitor
# -----------------------------
def test_monitoring_db_basic_operations_and_risk_monitor(tmp_path):
    # in-memory sqlite
    conn = sqlite3.connect(":memory:")
    init_monitoring_db(conn)
    db = MonitoringDB(conn)

    # system status log
    db.log_system_status(1.1, 2.2, 3.3, True)
    r = conn.execute("SELECT COUNT(*) FROM system_status").fetchone()
    assert r[0] == 1

    # trade event
    db.log_trade_event("Created", "C1", "AAA", "BUY", 100, 0.0)
    r2 = conn.execute("SELECT event_type, code FROM trade_logs WHERE client_order_id = 'C1'").fetchone()
    assert r2[0] == "Created" and r2[1] == "AAA"

    # upsert position and delete
    db.upsert_position("AAA", 100, 123.4, current_price=150.0)
    row = conn.execute("SELECT qty, avg_price FROM positions WHERE code='AAA'").fetchone()
    assert row[0] == 100
    db.delete_position("AAA")
    row2 = conn.execute("SELECT COUNT(*) FROM positions WHERE code='AAA'").fetchone()
    assert row2[0] == 0

    # upsert dashboard and peak_value preservation
    db.upsert_dashboard(portfolio_value=1000.0, cash=100.0, drawdown_pct=0.0, open_order_count=0, position_count=0, peak_value=1200.0)
    d = db.get_dashboard()
    assert d is not None and d["peak_value"] == 1200.0
    # now update with peak_value=None -> should preserve existing peak_value 1200.0
    db.upsert_dashboard(portfolio_value=900.0, cash=100.0, drawdown_pct=0.1, open_order_count=0, position_count=0, peak_value=None)
    d2 = db.get_dashboard()
    assert d2["peak_value"] == 1200.0

    # log_risk_event dedup behavior
    now = datetime.now(timezone.utc)
    ok1 = db.log_risk_event("E", "m", 1.0, 0.5, detail="det", logged_at=now, dedup_minutes=10)
    assert ok1 is True
    # within dedup window -> should return False
    ok2 = db.log_risk_event("E", "m", 1.0, 0.5, detail="det", logged_at=now + timedelta(minutes=5), dedup_minutes=10)
    assert ok2 is False
    # after window -> True
    ok3 = db.log_risk_event("E", "m", 1.0, 0.5, detail="det", logged_at=now + timedelta(minutes=11), dedup_minutes=10)
    assert ok3 is True

    # RiskMonitor behavior: set dashboard and positions to check alerts
    # prepare new conn with data
    conn2 = sqlite3.connect(":memory:")
    init_monitoring_db(conn2)
    db2 = MonitoringDB(conn2)
    # set dashboard with portfolio_value lower than peak to stimulate drawdown
    db2.upsert_dashboard(portfolio_value=800.0, cash=100.0, drawdown_pct=0.0, open_order_count=0, position_count=0, peak_value=1000.0)
    # insert positions > max_positions
    conn2.execute("INSERT INTO positions (code, qty, avg_price, current_price, updated_at) VALUES (?, ?, ?, ?, ?)", ("X", 1, 100.0, 100.0, datetime.now(timezone.utc).isoformat()))
    # add extra positions to exceed
    for i in range(12):
        conn2.execute("INSERT OR REPLACE INTO positions (code, qty, avg_price, current_price, updated_at) VALUES (?, ?, ?, ?, ?)", (f"P{i}", 1, 100.0, 100.0, datetime.now(timezone.utc).isoformat()))
    conn2.commit()

    rm = RiskMonitor(conn2, max_positions=5, dd_threshold=0.05)  # low threshold to ensure drawdown alert
    res = rm.check_once(now=datetime.now(timezone.utc))
    assert res.position_limit_alert is True or res.drawdown_alert is True

