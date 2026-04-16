
import importlib
import os
import sqlite3
import math
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import pytest

# Disable auto env load before importing kabusys.config
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"

from kabusys.config import (
    _parse_env_line,
    _load_env_file,
    _require,
    Settings,
)
from kabusys.portfolio.portfolio_builder import (
    select_candidates,
    calc_equal_weights,
    calc_score_weights,
)
from kabusys.portfolio.risk_adjustment import (
    apply_sector_cap,
    calc_regime_multiplier,
)
from kabusys.portfolio.position_sizing import calc_position_sizes
from kabusys.utils import process_priority


# ------------------------
# Tests for config parsing
# ------------------------
def test_parse_env_line_blank_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("# a comment") is None
    assert _parse_env_line("  # another") is None


def test_parse_env_line_simple_key_value():
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    assert _parse_env_line(" KEY = val ") == ("KEY", "val")
    assert _parse_env_line("export FOO=bar") == ("FOO", "bar")


def test_parse_env_line_no_equal():
    assert _parse_env_line("NO_EQUAL") is None


def test_parse_env_line_quotes_and_escapes():
    # single quotes with escaped char
    res = _parse_env_line(r"KEY='a\'b' # comment")
    assert res == ("KEY", "a'b")
    # double quotes
    res = _parse_env_line(r'KEY="he\"llo"')
    assert res == ("KEY", 'he"llo')
    # value with inline comment but no preceding space should keep '#'
    assert _parse_env_line("K=abc#notcomment") == ("K", "abc#notcomment")
    # inline comment preceded by space is treated as comment
    assert _parse_env_line("K=abc #comment") == ("K", "abc")


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    p = tmp_path / ".env.test"
    content = "\n".join(
        [
            "A=1",
            "B=2",
            "C='quoted\\'val'",
            "# comment",
            "INVALID",
            "EXPORT_ME=3",
        ]
    )
    p.write_text(content, encoding="utf-8")
    # initial environment
    monkeypatch.setenv("B", "envB")
    # protected keys should not be overwritten even if override=True
    protected = frozenset({"B", "X"})
    _load_env_file(p, override=False, protected=protected)
    assert os.environ.get("A") == "1"
    # B was present and override=False so should remain envB
    assert os.environ.get("B") == "envB"
    assert os.environ.get("C") == "quoted'val"
    # now override True with protected preventing overwrite of B
    monkeypatch.setenv("B", "envB2")
    _load_env_file(p, override=True, protected=protected)
    # protected prevented overwrite
    assert os.environ.get("B") == "envB2"
    # A will be overwritten by override=True
    assert os.environ.get("A") == "1"
    # missing file should be no-op
    _load_env_file(tmp_path / "does_not_exist.env")


def test_require_raises_when_missing(monkeypatch):
    monkeypatch.delenv("SOME_VAR", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_VAR")
    monkeypatch.setenv("SOME_VAR", "ok")
    assert _require("SOME_VAR") == "ok"


# ------------------------
# Settings property tests
# ------------------------
def test_settings_env_and_flags(monkeypatch):
    # clear env
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    s = Settings()
    # default is development
    assert s.env == "development"
    assert s.is_dev
    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = Settings().env
    # valid paper_trading
    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    assert Settings().is_paper


def test_paper_fill_mode_valid_and_invalid(monkeypatch):
    monkeypatch.delenv("PAPER_FILL_MODE", raising=False)
    s = Settings()
    assert s.paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "partial")
    assert Settings().paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "INVALID")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode


def test_log_level_validation(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert Settings().log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "nope")
    with pytest.raises(ValueError):
        _ = Settings().log_level


# ------------------------
# Portfolio builder tests
# ------------------------
def test_select_candidates_and_weights():
    buy_signals = [
        {"code": "A", "score": 1.0, "signal_rank": 2},
        {"code": "B", "score": 2.0, "signal_rank": 1},
        {"code": "C", "score": 2.0, "signal_rank": 5},
    ]
    # B and C have same score but B has smaller rank -> B first
    selected = select_candidates(buy_signals, max_positions=2)
    assert [s["code"] for s in selected] == ["B", "C"]
    # equal weights
    eq = calc_equal_weights(selected)
    assert math.isclose(eq["B"], 0.5)
    assert math.isclose(eq["C"], 0.5)
    # score weights normal
    sw = calc_score_weights(selected)
    # scores B=2 C=2 => equal weights
    assert math.isclose(sw["B"], 0.5)
    assert math.isclose(sw["C"], 0.5)


def test_calc_score_weights_all_zero(caplog):
    candidates = [{"code": "X", "score": 0.0}, {"code": "Y", "score": 0.0}]
    with caplog.at_level("WARNING"):
        w = calc_score_weights(candidates)
        # fallback to equal weights
        assert w == {"X": 0.5, "Y": 0.5}
        assert "全銘柄のスコアが 0.0" in caplog.text


# ------------------------
# Risk adjustment tests
# ------------------------
def test_apply_sector_cap_basic():
    candidates = [{"code": "A"}, {"code": "B"}, {"code": "C"}]
    sector_map = {"A": "tech", "B": "tech", "C": "other"}
    portfolio_value = 1000.0
    current_positions = {"A": 10, "B": 50}  # exposure depends on price_map
    price_map = {"A": 10.0, "B": 10.0, "C": 1.0}
    # tech exposure = (10+50)*10 = 600 -> 60% of portfolio -> with max_sector_pct=0.3 both A/B should be blocked
    filtered = apply_sector_cap(
        candidates, sector_map, portfolio_value, current_positions, price_map, max_sector_pct=0.3
    )
    # only C remains
    assert filtered == [{"code": "C"}]


def test_apply_sector_cap_unknown_sector_not_blocked():
    candidates = [{"code": "U"}]
    sector_map = {}  # unknown
    portfolio_value = 1000.0
    current_positions = {"U": 100}
    price_map = {"U": 10.0}
    # unknown sector is not subject to cap -> candidate kept
    assert apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map) == candidates


def test_calc_regime_multiplier_known_and_unknown(caplog):
    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == 0.7
    assert calc_regime_multiplier("bear") == 0.3
    with caplog.at_level("WARNING"):
        assert calc_regime_multiplier("weird") == 1.0
        assert "未知のレジーム" in caplog.text


# ------------------------
# Position sizing tests
# ------------------------
def test_calc_position_sizes_empty_candidates():
    assert calc_position_sizes({}, [], 1000.0, 500.0, {}, {}, allocation_method="equal") == {}


def test_calc_position_sizes_equal_and_score_allocation_lot_and_cap():
    # two candidates with small prices so lot rounding matters
    candidates = [{"code": "A"}, {"code": "B"}]
    weights = {"A": 0.6, "B": 0.4}
    portfolio_value = 100000.0
    available_cash = 50000.0
    current_positions = {}
    open_prices = {"A": 50.0, "B": 30.0}
    # use lot_size 10 to see rounding behavior
    res = calc_position_sizes(
        weights,
        candidates,
        portfolio_value,
        available_cash,
        current_positions,
        open_prices,
        allocation_method="score",
        max_utilization=0.6,
        lot_size=10,
    )
    # should produce integer multiples of lot_size
    for v in res.values():
        assert v % 10 == 0
    # total cost should not exceed available_cash
    total_cost = sum(res[c] * open_prices[c] for c in res)
    assert total_cost <= available_cash + 1e-6


def test_calc_position_sizes_risk_based_skips_missing_price_and_respects_lot():
    candidates = [{"code": "A"}, {"code": "B"}]
    portfolio_value = 100000.0
    available_cash = 100000.0
    current_positions = {"A": 0, "B": 0}
    open_prices = {"A": 10.0}  # B price missing -> skip B
    res = calc_position_sizes(
        {},
        candidates,
        portfolio_value,
        available_cash,
        current_positions,
        open_prices,
        allocation_method="risk_based",
        risk_pct=0.01,
        stop_loss_pct=0.1,
        lot_size=100,
    )
    # A should be present and multiple of lot_size
    assert "A" in res
    assert res["A"] % 100 == 0
    assert "B" not in res


# ------------------------
# process_priority tests (mocking psutil & platform)
# ------------------------
class DummyProcess:
    def __init__(self):
        self.pid = 12345
        self._nice_set = None
        self._affinity_set = None

    def nice(self, value):
        self._nice_set = value

    def cpu_affinity(self, pinned):
        self._affinity_set = pinned


def test_set_process_priority_windows(monkeypatch):
    dummy = DummyProcess()
    monkeypatch.setattr(process_priority, "psutil", SimpleNamespace(Process=lambda: dummy, HIGH_PRIORITY_CLASS=11, NORMAL_PRIORITY_CLASS=22, IDLE_PRIORITY_CLASS=33))
    monkeypatch.setattr(process_priority, "platform", SimpleNamespace(system=lambda: "Windows"))
    process_priority.set_process_priority("high")
    assert dummy._nice_set == 11
    # invalid level raises
    with pytest.raises(ValueError):
        process_priority.set_process_priority("nope")


def test_set_process_priority_posix(monkeypatch):
    dummy = DummyProcess()
    monkeypatch.setattr(process_priority, "psutil", SimpleNamespace(Process=lambda: dummy))
    monkeypatch.setattr(process_priority, "platform", SimpleNamespace(system=lambda: "Linux"))
    # Should set to negative nice value for high
    process_priority.set_process_priority("high")
    assert dummy._nice_set == process_priority._LINUX_NICE["high"]


def test_set_cpu_affinity_none_and_invalid_and_large(monkeypatch, caplog):
    dummy = DummyProcess()
    # monkeypatch psutil.Process and cpu_count
    monkeypatch.setattr(process_priority, "psutil", SimpleNamespace(Process=lambda: dummy, cpu_count=lambda: 2))
    # None -> no-op
    process_priority.set_cpu_affinity(None)
    # invalid (<1)
    with pytest.raises(ValueError):
        process_priority.set_cpu_affinity(0)
    # cpu_count > available -> should pin to all cores and not raise
    with caplog.at_level("DEBUG"):
        process_priority.set_cpu_affinity(10)
        # pinned should be [0,1] as cpu_count() reports 2
        assert dummy._affinity_set == [0, 1]
