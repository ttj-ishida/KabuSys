
# tests/test_kabusys_core.py
import os
import sqlite3
import math
from pathlib import Path
from datetime import datetime, timezone

import pytest

from unittest import mock

# --- config tests ---
from kabusys.config import (
    _parse_env_line,
    _load_env_file,
    _require,
    Settings,
)

# --- portfolio tests ---
from kabusys.portfolio.portfolio_builder import (
    select_candidates,
    calc_equal_weights,
    calc_score_weights,
)
from kabusys.portfolio.risk_adjustment import apply_sector_cap, calc_regime_multiplier
from kabusys.portfolio.position_sizing import calc_position_sizes

# --- utils tests ---
from kabusys.utils import process_priority

# --- monitoring db tests ---
from kabusys.monitoring.monitoring_db import init_monitoring_db, MonitoringDB


# -------------------------
# Config parsing tests
# -------------------------
def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("KEY=val\n") == ("KEY", "val")
    assert _parse_env_line(" # comment\n") is None
    assert _parse_env_line("") is None
    # no separator
    assert _parse_env_line("NOSPASE") is None
    # inline comment without space should be preserved
    assert _parse_env_line("X=val#notcomment") == ("X", "val#notcomment")
    # inline comment with preceding space should be stripped
    assert _parse_env_line("Y=val #comment") == ("Y", "val")


def test_parse_env_line_export_and_quoted_and_escapes():
    # export prefix, quoted value, escaped single quote inside
    line = "export FOO='a\\'b'  #ignored\n"
    k, v = _parse_env_line(line)
    assert k == "FOO"
    assert v == "a'b"
    # double quotes and escaped char
    line2 = 'BAR="hello\\nworld"\n'
    k2, v2 = _parse_env_line(line2)
    # note: parser treats backslash escape as taking next char literally
    assert k2 == "BAR"
    assert "n" in v2  # '\n' becomes 'n' in this simplistic parser behavior


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    p = tmp_path / ".env.test"
    p.write_text("A=1\nB=2\nC=3\n")
    # ensure environment starts clean for these keys
    monkeypatch.delenv("A", raising=False)
    monkeypatch.setenv("B", "OLD")
    # first load: override=False -> should not overwrite B
    _load_env_file(p, override=False, protected=frozenset())
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "OLD"
    assert os.environ.get("C") == "3"
    # second load: override=True with protected containing B -> B should stay OLD
    _load_env_file(p, override=True, protected=frozenset({"B"}))
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "OLD"
    assert os.environ.get("C") == "3"


def test_require_and_settings_env_validation(monkeypatch):
    monkeypatch.delenv("SOME_MISSING", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_MISSING")
    monkeypatch.setenv("SOME_KEY", "VALUE")
    assert _require("SOME_KEY") == "VALUE"

    settings = Settings()
    # env validation: set invalid KABUSYS_ENV
    monkeypatch.setenv("KABUSYS_ENV", "INVALID_ENV")
    with pytest.raises(ValueError):
        _ = settings.env
    # log level validation
    monkeypatch.setenv("LOG_LEVEL", "invalid")
    with pytest.raises(ValueError):
        _ = settings.log_level
    # paper_fill_mode validation
    monkeypatch.setenv("PAPER_FILL_MODE", "bad_mode")
    with pytest.raises(ValueError):
        _ = settings.paper_fill_mode


# -------------------------
# Portfolio / weights tests
# -------------------------
def test_select_candidates_tiebreak_and_empty():
    signals = [
        {"code": "A", "score": 1.0, "signal_rank": 2},
        {"code": "B", "score": 1.0, "signal_rank": 1},
        {"code": "C", "score": 0.5, "signal_rank": 1},
    ]
    res = select_candidates(signals, max_positions=2)
    # score same for A/B -> B (signal_rank 1) should come first
    assert [r["code"] for r in res] == ["B", "A"]
    assert select_candidates([], 5) == []


def test_calc_equal_and_score_weights_and_zero_total(caplog):
    candidates = [
        {"code": "A", "score": 0.0},
        {"code": "B", "score": 0.0},
    ]
    eq = calc_equal_weights(candidates)
    assert eq == {"A": 0.5, "B": 0.5}
    # score weights with zero total should fallback and emit a warning
    caplog.clear()
    caplog.set_level("WARNING")
    sw = calc_score_weights(candidates)
    assert sw == eq
    assert any("フォールバック" in rec.message or "フォールバック" in rec.getMessage() or "フォールバック" in rec.msg for rec in caplog.records)


def test_apply_sector_cap_blocking_and_sell_codes():
    candidates = [
        {"code": "A", "score": 1},
        {"code": "B", "score": 2},
        {"code": "C", "score": 3},
        {"code": "U", "score": 4},  # unknown sector
    ]
    sector_map = {"A": "S1", "B": "S1", "C": "S2"}
    price_map = {"A": 100, "B": 100, "C": 50, "U": 10}
    # portfolio value small so that S1 exposure becomes large
    current_positions = {"A": 50}  # exposure = 50*100=5000
    # set portfolio_value so that exposure/portfolio_value >= max_sector_pct
    filtered = apply_sector_cap(candidates, sector_map, portfolio_value=10000, current_positions=current_positions, price_map=price_map, max_sector_pct=0.3)
    # S1 should be blocked -> A and B should be excluded; unknown U remains
    codes = {c["code"] for c in filtered}
    assert "U" in codes
    assert "C" in codes
    assert "A" not in codes and "B" not in codes

    # sell_codes excludes A from exposure calc so S1 not blocked now
    filtered2 = apply_sector_cap(candidates, sector_map, portfolio_value=10000, current_positions=current_positions, price_map=price_map, max_sector_pct=0.3, sell_codes={"A"})
    codes2 = {c["code"] for c in filtered2}
    assert "B" in codes2  # no longer blocked


def test_calc_regime_multiplier_known_and_unknown(caplog):
    assert math.isclose(calc_regime_multiplier("bull"), 1.0)
    assert math.isclose(calc_regime_multiplier("neutral"), 0.7)
    assert math.isclose(calc_regime_multiplier("bear"), 0.3)
    caplog.set_level("WARNING")
    caplog.clear()
    v = calc_regime_multiplier("mystery")
    assert v == 1.0
    assert any("未知" in rec.getMessage() or "fallback" in rec.getMessage().lower() or "フォールバック" in rec.getMessage() for rec in caplog.records)


# -------------------------
# Position sizing tests
# -------------------------
def test_calc_position_sizes_risk_based_lot_rounding():
    candidates = [{"code": "XYZ", "score": 1}]
    open_prices = {"XYZ": 10.0}
    current_positions = {}
    # choose parameters so that base_shares is large and lot rounding matters
    res = calc_position_sizes(
        weights={}, candidates=candidates, portfolio_value=1_000_000,
        available_cash=1_000_000, current_positions=current_positions,
        open_prices=open_prices, allocation_method="risk_based",
        risk_pct=0.005, stop_loss_pct=0.08, lot_size=100
    )
    # earlier analysis: base_shares = floor(1e6*0.005/(10*0.08)) = floor(5000/0.8)=6250 -> floored to lot 6200
    assert "XYZ" in res
    assert res["XYZ"] % 100 == 0
    assert res["XYZ"] > 0


def test_calc_position_sizes_equal_score_scaling():
    candidates = [{"code": "A"}, {"code": "B"}]
    # each price 100
    open_prices = {"A": 100.0, "B": 100.0}
    current_positions = {}
    # weights sum to 1
    weights = {"A": 0.5, "B": 0.5}
    # portfolio_value 100k -> per-position alloc 50k -> base_shares = 500
    # available_cash lower to force scaling to 60k total available
    res = calc_position_sizes(
        weights=weights, candidates=candidates, portfolio_value=100_000,
        available_cash=60_000, current_positions=current_positions,
        open_prices=open_prices, allocation_method="equal",
        max_utilization=1.0, lot_size=100, cost_buffer=0.0
    )
    # expected scaled shares: each 300 shares (300*100*2 = 60k)
    assert res == {"A": 300, "B": 300}


# -------------------------
# process_priority tests (psutil/platform mocked)
# -------------------------
def test_set_process_priority_invalid():
    with pytest.raises(ValueError):
        process_priority.set_process_priority("invalid_level")


def test_set_process_priority_linux_and_access_denied(monkeypatch, caplog):
    # mock platform.system to Linux
    monkeypatch.setattr(process_priority.platform, "system", lambda: "Linux")
    class DummyProc:
        def __init__(self):
            self.pid = 12345
            self.nice_called = []
        def nice(self, val):
            self.nice_called.append(val)
    dummy = DummyProc()
    monkeypatch.setattr(process_priority.psutil, "Process", lambda: dummy)
    # valid call should call nice with linux nice value
    process_priority.set_process_priority("high")
    assert dummy.nice_called and dummy.nice_called[-1] == process_priority._LINUX_NICE["high"]

    # simulate AccessDenied
    def raise_access():
        raise process_priority.psutil.AccessDenied()
    proc2 = mock.MagicMock()
    proc2.nice.side_effect = raise_access
    monkeypatch.setattr(process_priority.psutil, "Process", lambda: proc2)
    caplog.set_level("WARNING")
    process_priority.set_process_priority("normal")
    assert any("権限不足" in rec.getMessage() or "AccessDenied" in rec.getMessage() or "設定に失敗" in rec.getMessage() for rec in caplog.records)


def test_set_cpu_affinity_errors_and_bounds(monkeypatch, caplog):
    # cpu_count None => no-op
    assert process_priority.set_cpu_affinity(None) is None

    with pytest.raises(ValueError):
        process_priority.set_cpu_affinity(0)

    # normal path: available cores mocked
    monkeypatch.setattr(process_priority.psutil, "cpu_count", lambda: 4)
    class DummyP:
        def __init__(self):
            self.pid = 999
            self.pinned = None
        def cpu_affinity(self, pinned):
            self.pinned = pinned
    dp = DummyP()
    monkeypatch.setattr(process_priority.psutil, "Process", lambda: dp)
    process_priority.set_cpu_affinity(2)
    assert dp.pinned == [0, 1]

    # cpu_count > available -> uses all cores
    dp2 = DummyP()
    monkeypatch.setattr(process_priority.psutil, "Process", lambda: dp2)
    process_priority.set_cpu_affinity(10)
    assert dp2.pinned == [0, 1, 2, 3]

    # simulate AccessDenied
    def raise_access_affinity(p):
        raise process_priority.psutil.AccessDenied()
    proc3 = mock.MagicMock()
    proc3.cpu_affinity.side_effect = raise_access_affinity
    monkeypatch.setattr(process_priority.psutil, "Process", lambda: proc3)
    caplog.clear()
    caplog.set_level("WARNING")
    process_priority.set_cpu_affinity(1)
    assert any("権限不足" in rec.getMessage() or "CPU affinity" in rec.getMessage() or "スキップ" in rec.getMessage() for rec in caplog.records)


# -------------------------
# MonitoringDB tests
# -------------------------
def test_init_monitoring_db_and_basic_operations(tmp_path):
    # use a temp sqlite file to persist and inspect schema
    db_path = tmp_path / "test_monitor.db"
    conn = sqlite3.connect(str(db_path))
    init_monitoring_db(conn)
    # tables should exist: dashboard, system_status, positions, risk_logs, trade_logs
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {r[0] for r in cur.fetchall()}
    assert "dashboard" in tables
    assert "system_status" in tables
    # MonitoringDB operations
    mdb = MonitoringDB(conn)
    # upsert dashboard with peak_value and then with None to ensure peak_value preserved
    mdb.upsert_dashboard(portfolio_value=1000.0, cash=500.0, drawdown_pct=0.0, open_order_count=0, position_count=0, peak_value=2000.0)
    d = mdb.get_dashboard()
    assert d is not None
    assert d["peak_value"] == 2000.0
    mdb.upsert_dashboard(portfolio_value=1100.0, cash=400.0, drawdown_pct=0.0, open_order_count=0, position_count=0, peak_value=None)
    d2 = mdb.get_dashboard()
    assert d2["peak_value"] == 2000.0

    # log_system_status writes a row
    mdb.log_system_status(cpu_percent=1.0, memory_percent=2.0, disk_percent=3.0, process_ok=True)
    r = conn.execute("SELECT COUNT(*) FROM system_status").fetchone()
    assert r[0] >= 1

    # log_risk_event dedup: first insertion returns True, immediate second with same detail and dedup_minutes should return False
    now = datetime.now(timezone.utc)
    ok1 = mdb.log_risk_event("TYPE", "metric", 0.1, 0.5, detail="d1", logged_at=now, dedup_minutes=60)
    assert ok1 is True
    ok2 = mdb.log_risk_event("TYPE", "metric", 0.2, 0.5, detail="d1", logged_at=now, dedup_minutes=60)
    assert ok2 is False

    # upsert_position and delete_position
    mdb.upsert_position("AAA", 100, 123.4, current_price=120.0)
    row = conn.execute("SELECT qty, avg_price FROM positions WHERE code = ?", ("AAA",)).fetchone()
    assert row[0] == 100 and row[1] == 123.4
    mdb.delete_position("AAA")
    row2 = conn.execute("SELECT * FROM positions WHERE code = ?", ("AAA",)).fetchone()
    assert row2 is None
