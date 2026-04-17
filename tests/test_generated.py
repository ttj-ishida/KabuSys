
import io
import json
import math
import os
import sqlite3
import tempfile
from datetime import datetime, date, timedelta
from pathlib import Path
from unittest import mock

import pytest

# Ensure auto env load is disabled before importing modules that may perform auto actions.
os.environ.setdefault("KABUSYS_DISABLE_AUTO_ENV_LOAD", "1")

import importlib

import kabusys.config as config
import kabusys.validate_config as validate_config
import kabusys.monitoring.monitoring_db as monitoring_db
import kabusys.paper_verification_report as pvr
import kabusys.portfolio.portfolio_builder as pb
import kabusys.portfolio.risk_adjustment as ra
import kabusys.portfolio.position_sizing as ps
import kabusys.utils.process_priority as pp


# ------------------------
# Helpers / fixtures
# ------------------------

@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    """Ensure environment isolation for each test."""
    # copy current env and restore after
    env = dict(os.environ)
    monkeypatch.setenv("KABUSYS_DISABLE_AUTO_ENV_LOAD", "1")
    yield
    os.environ.clear()
    os.environ.update(env)


# ------------------------
# config._parse_env_line / _load_env_file
# ------------------------

def test_parse_env_line_basic_and_comments():
    assert config._parse_env_line("") is None
    assert config._parse_env_line("   # comment ") is None
    assert config._parse_env_line("KEY=val") == ("KEY", "val")
    assert config._parse_env_line("export KEY2=  spaced ") == ("KEY2", "spaced")

def test_parse_env_line_quoted_and_escaped():
    # double quoted with escaped quote
    raw = r'FOO="a\"b\nc"'
    k, v = config._parse_env_line(raw)
    assert k == "FOO"
    # escaped \" should become " in result, \n becomes literal n because parsed as characters
    assert 'a"b' in v

    raw2 = "SINGLE='abc\\'d'"
    k2, v2 = config._parse_env_line(raw2)
    assert k2 == "SINGLE"
    assert "abc'd" in v2

def test_parse_env_line_inline_comment_behavior():
    # '#' after a space should start a comment
    assert config._parse_env_line("A=hello #comment") == ("A", "hello")
    # '#' embedded without space is part of value
    assert config._parse_env_line("B=ab#cd") == ("B", "ab#cd")

def test_parse_env_line_invalids():
    assert config._parse_env_line("NOSEP") is None
    assert config._parse_env_line("=novalue") is None
    assert config._parse_env_line("   =   ") is None


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    p = tmp_path / ".env.test"
    p.write_text("\n".join([
        "A=1",
        "B=two",
        "C=three"
    ]), encoding="utf-8")
    # ensure A exists in os.environ beforehand to test override behavior
    monkeypatch.setenv("A", "orig")
    # protected should prevent overwrite even when override True
    config._load_env_file(p, override=True, protected=frozenset({"A"}))
    assert os.environ["A"] == "orig"
    assert os.environ["B"] == "two"
    assert os.environ["C"] == "three"

    # Now test override=False: only set missing
    monkeypatch.delenv("D", raising=False)
    p2 = tmp_path / ".env2"
    p2.write_text("D=4\nA=9\n", encoding="utf-8")
    # A already exists; override=False => A unchanged
    config._load_env_file(p2, override=False)
    assert os.environ.get("A") == "orig"
    assert os.environ["D"] == "4"


# ------------------------
# Settings class properties
# ------------------------

def test_settings_env_and_log_level_and_paper_fill(monkeypatch):
    # test env validation
    monkeypatch.setenv("KABUSYS_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    s = config.Settings()
    assert s.env == "development"
    assert s.log_level == "INFO"
    assert s.is_dev is True

    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "bad_env")
    with pytest.raises(ValueError):
        _ = config.Settings().env

    # invalid log level
    monkeypatch.setenv("LOG_LEVEL", "nope")
    with pytest.raises(ValueError):
        _ = config.Settings().log_level

    # paper_fill_mode valid and invalid
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    assert config.Settings().paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "INVALID")
    with pytest.raises(ValueError):
        _ = config.Settings().paper_fill_mode


# ------------------------
# validate_config.validate
# ------------------------

def test_validate_config_basic(tmp_path, monkeypatch):
    # point validate_config to tmp config dir
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "token_value")
    monkeypatch.setenv("KABU_API_PASSWORD", "pw_value")
    monkeypatch.setenv("KABUSYS_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    # create config directory and some yaml files to avoid warnings for missing files
    tmp_cfg = tmp_path / "config"
    tmp_cfg.mkdir()
    # only create some files, leave others missing to provoke warnings
    for name in ["system_config.yaml", "data_config.yaml"]:
        (tmp_cfg / name).write_text("{}", encoding="utf-8")
    monkeypatch.setattr(validate_config, "_CONFIG_DIR", tmp_cfg)

    errors, warnings, infos = validate_config.validate()
    # required env vars present → no errors about them
    assert not any("必須環境変数が未設定" in e for e in errors)
    # at least some infos should be present
    assert any("設定済み" in i or "KABUSYS_ENV" in i for i in infos)

def test_validate_config_required_missing(monkeypatch):
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("KABU_API_PASSWORD", raising=False)
    # force config dir to empty tmp to avoid side effects
    with mock.patch.object(validate_config, "_CONFIG_DIR", Path(tempfile.mkdtemp())):
        errors, warnings, infos = validate_config.validate()
    assert any("必須環境変数が未設定です" in e for e in errors)


# ------------------------
# monitoring_db: init and MonitoringDB methods
# ------------------------

def test_init_monitoring_db_and_migrations():
    conn = sqlite3.connect(":memory:")
    # call init to create tables and columns
    monitoring_db.init_monitoring_db(conn)

    # check tables exist by querying PRAGMA table_info
    cur = conn.execute("PRAGMA table_info(dashboard)").fetchall()
    cols = {r[1] for r in cur}
    assert "peak_value" in cols

    trade_cols = {r[1] for r in conn.execute("PRAGMA table_info(trade_logs)").fetchall()}
    assert "latency_ms" in trade_cols
    conn.close()

def test_monitoringdb_logging_and_upsert(tmp_path):
    conn = sqlite3.connect(":memory:")
    monitoring_db.init_monitoring_db(conn)
    mdb = monitoring_db.MonitoringDB(conn)

    # log system status
    now = datetime.utcnow()
    mdb.log_system_status(cpu_percent=10.0, memory_percent=20.0, disk_percent=30.0, process_ok=True, recorded_at=now)
    row = conn.execute("SELECT cpu_percent, memory_percent, disk_percent, process_ok FROM system_status").fetchone()
    assert row[0] == 10.0
    assert row[3] == 1

    # trade event
    mdb.log_trade_event("Created", "cid1", "7203", "BUY", 100, 0.0, filled_qty=0, state="open", logged_at=now, latency_ms=123.4)
    row2 = conn.execute("SELECT event_type, client_order_id, latency_ms FROM trade_logs").fetchone()
    assert row2[0] == "Created"
    assert row2[2] == 123.4

    # upsert position and delete
    mdb.upsert_position("7203", 100, 5000.0, current_price=5050.0, updated_at=now)
    r = conn.execute("SELECT qty, avg_price FROM positions WHERE code = ?", ("7203",)).fetchone()
    assert r[0] == 100
    mdb.delete_position("7203")
    assert conn.execute("SELECT 1 FROM positions WHERE code = ?", ("7203",)).fetchone() is None

    # risk logging dedup behavior
    ok = mdb.log_risk_event("threshold_exceeded", "cpu", 95.0, 90.0, detail="high", logged_at=now, dedup_minutes=60)
    assert ok is True
    # second call within dedup window should return False
    ok2 = mdb.log_risk_event("threshold_exceeded", "cpu", 95.0, 90.0, detail="high", logged_at=now + timedelta(minutes=30), dedup_minutes=60)
    assert ok2 is False

    conn.close()


# ------------------------
# paper_verification_report utilities
# ------------------------

def test_p95_and_build_date_filter_and_formatters():
    assert pvr._p95([]) is None
    vals = [1, 2, 3, 4, 5, 100]
    p95 = pvr._p95(vals)
    assert p95 == sorted(vals)[max(math.ceil(len(vals) * 0.95) - 1, 0)]

    where, params = pvr._build_date_filter("t", None, None)
    assert where == "" and params == []

    where2, params2 = pvr._build_date_filter("t", "2020", "2021")
    assert "t >= ?" in where2 and "t <= ?" in where2 and params2 == ["2020", "2021"]

    assert pvr._fmt_float(None) == "N/A"
    assert pvr._fmt_float(1.23456, 2, " ms") == "1.23 ms"
    assert pvr._fmt_int(None) == "N/A"
    assert pvr._fmt_int(5) == "5"


# ------------------------
# portfolio_builder: select/calc_weights
# ------------------------

def test_select_candidates_and_weights(caplog):
    signals = [
        {"code": "A", "signal_rank": 2, "score": 0.5},
        {"code": "B", "signal_rank": 1, "score": 0.5},
        {"code": "C", "signal_rank": 3, "score": 0.1},
    ]
    top = pb.select_candidates(signals, max_positions=2)
    # A and B have same score; tie-breaker should prefer smaller signal_rank (B)
    assert top[0]["code"] == "B"
    assert top[1]["code"] in {"A", "C"}

    eq = pb.calc_equal_weights(top)
    assert sum(eq.values()) == pytest.approx(1.0)

    # score weights with positive total
    w = pb.calc_score_weights(signals)
    assert math.isclose(sum(w.values()), 1.0)

    # score weights with all zero => fallback to equal and emits warning
    with caplog.at_level("WARNING"):
        zero_signals = [{"code": "X", "score": 0.0}, {"code": "Y", "score": 0.0}]
        w2 = pb.calc_score_weights(zero_signals)
        assert w2 == {"X": 0.5, "Y": 0.5}
        assert any("フォールバック" in rec.message or "フォールバック" in rec.getMessage() for rec in caplog.records)


# ------------------------
# risk_adjustment: sector cap + regime multiplier
# ------------------------

def test_apply_sector_cap_behavior():
    candidates = [{"code": "A", "score": 1}, {"code": "B", "score": 2}, {"code": "C", "score": 3}]
    sector_map = {"A": "tech", "B": "tech", "C": "fin"}
    portfolio_value = 1_000_000.0
    current_positions = {"A": 100, "B": 100}  # value will depend on price_map
    price_map = {"A": 4000.0, "B": 4000.0, "C": 1000.0}
    # tech exposure = (100+100)*4000 = 800_000 -> 80% -> exceeds default 30%
    filtered = ra.apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map)
    # tech sector candidates A and B should be filtered out, leaving C
    assert all(c["code"] == "C" for c in filtered)

    # unknown sector should not be blocked
    sector_map2 = {"A": "unknown", "B": "unknown", "C": "fin"}
    filtered2 = ra.apply_sector_cap(candidates, sector_map2, portfolio_value, current_positions, price_map)
    assert len(filtered2) == 3

def test_calc_regime_multiplier_logs_warning_for_unknown(caplog):
    with caplog.at_level("WARNING"):
        val = ra.calc_regime_multiplier("bull")
        assert val == 1.0
        val2 = ra.calc_regime_multiplier("neutral")
        assert val2 == 0.7
        val3 = ra.calc_regime_multiplier("weird")
        assert val3 == 1.0
        assert any("未知のレジーム" in rec.getMessage() or "未知のレジーム" in rec.message for rec in caplog.records)


# ------------------------
# position_sizing: calc_position_sizes
# ------------------------

def test_calc_position_sizes_risk_based_and_equal_and_scaling():
    # risk_based: basic behavior with lot_size rounding
    candidates = [{"code": "AAA", "score": 1}, {"code": "BBB", "score": 1}]
    open_prices = {"AAA": 1000.0, "BBB": 2000.0}
    current_positions = {"AAA": 0, "BBB": 0}
    pv = 10_000_000.0
    available_cash = 1_000_000.0

    sizes = ps.calc_position_sizes(
        weights={}, candidates=candidates, portfolio_value=pv,
        available_cash=available_cash, current_positions=current_positions,
        open_prices=open_prices, allocation_method="risk_based",
        risk_pct=0.001, stop_loss_pct=0.05, lot_size=10
    )
    # ensure shares are multiples of lot_size
    for v in sizes.values():
        assert v % 10 == 0

    # equal/score path: test aggregate scaling when available_cash small
    weights = {"AAA": 0.5, "BBB": 0.5}
    # set available_cash tiny so scaling occurs
    small_cash = 1000.0
    scaled = ps.calc_position_sizes(
        weights=weights, candidates=candidates, portfolio_value=pv,
        available_cash=small_cash, current_positions=current_positions,
        open_prices=open_prices, allocation_method="equal",
        lot_size=10, max_utilization=1.0, cost_buffer=0.0
    )
    # with small cash, we expect either empty or very small (multiples of lot_size)
    for shares in scaled.values():
        assert shares % 10 == 0

    # ensure function handles missing price by skipping
    open_prices2 = {"AAA": None}
    res = ps.calc_position_sizes(
        weights=weights, candidates=candidates, portfolio_value=pv,
        available_cash=small_cash, current_positions=current_positions,
        open_prices=open_prices2, allocation_method="equal",
    )
    # BBB missing price -> skipped; AAA maybe skipped if None treated as not >0
    assert isinstance(res, dict)


# ------------------------
# process_priority: set_process_priority and set_cpu_affinity (psutil mocked)
# ------------------------

def test_set_process_priority_and_affinity(monkeypatch):
    fake_proc = mock.Mock()
    fake_proc.pid = 9999

    class FakePS:
        def __init__(self):
            pass
        def nice(self, v):
            self._nice = v
        def cpu_affinity(self, pinned):
            self._affinity = pinned

    fake_ps = FakePS()
    monkeypatch.setattr(pp, "psutil", mock.Mock(Process=lambda: fake_ps, cpu_count=lambda: 4, HIGH_PRIORITY_CLASS=1, NORMAL_PRIORITY_CLASS=2, IDLE_PRIORITY_CLASS=3))
    # patch platform.system to return Linux
    monkeypatch.setattr(pp, "platform", mock.Mock(system=lambda: "Linux"))

    # valid levels should not raise
    pp.set_process_priority("high")
    pp.set_process_priority("normal")
    pp.set_process_priority("low")

    # invalid level raises
    with pytest.raises(ValueError):
        pp.set_process_priority("UPSIDE_DOWN")

    # set_cpu_affinity behavior
    # None => no-op
    pp.set_cpu_affinity(None)
    # invalid cpu_count triggers ValueError
    with pytest.raises(ValueError):
        pp.set_cpu_affinity(0)
    # valid sets affinity to first N cores
    pp.set_cpu_affinity(2)
    assert hasattr(fake_ps, "_affinity")
    assert fake_ps._affinity == [0, 1]

