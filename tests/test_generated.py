
import json
import math
from datetime import date, datetime
from types import SimpleNamespace
from pathlib import Path

import pytest
from unittest import mock

# ---- config: _parse_env_line, _load_env_file, Settings ----
from kabusys import config as config_mod
from kabusys.config import Settings

# ---- validate_config ----
from kabusys import validate_config as validate_mod

# ---- portfolio builder & risk & position sizing ----
from kabusys.portfolio import portfolio_builder as pb
from kabusys.portfolio import risk_adjustment as ra
from kabusys.portfolio import position_sizing as ps

# ---- feature exploration ----
from kabusys.feature_exploration import rank, calc_ic, factor_summary

# ---- ai news nlp utils ----
from kabusys.ai import news_nlp as news_nlp_mod

# ---- utils process_priority ----
from kabusys.utils import process_priority as pp


# ---------------------------
# Tests for config parsing
# ---------------------------
def test_parse_env_line_basic_and_comments():
    assert config_mod._parse_env_line("") is None
    assert config_mod._parse_env_line("# comment") is None
    # no '='
    assert config_mod._parse_env_line("INVALIDLINE") is None
    # simple key=value
    assert config_mod._parse_env_line("KEY=val") == ("KEY", "val")
    # inline comment after space
    assert config_mod._parse_env_line("KEY=val #comment") == ("KEY", "val")
    # comment char not preceded by space should be preserved
    assert config_mod._parse_env_line("KEY=foo#bar") == ("KEY", "foo#bar")
    # export prefix
    assert config_mod._parse_env_line("export FOO=bar") == ("FOO", "bar")


def test_parse_env_line_quoted_and_escapes():
    # double quotes with escaped quote inside
    s = 'KEY="a\\"b"'
    assert config_mod._parse_env_line(s) == ("KEY", 'a"b')
    # single quotes with escaped single quote
    s2 = "KEY='a\\'b'"
    assert config_mod._parse_env_line(s2) == ("KEY", "a'b")
    # empty value
    assert config_mod._parse_env_line("KEY=") == ("KEY", "")


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    env_path = tmp_path / ".env"
    env_path.write_text("A=1\nB=2\nC=3\n")

    # ensure environment initially contains B=existing and OS-protected set contains B
    monkeypatch.setenv("B", "existing")
    # override=False should not overwrite B, but set A,C
    config_mod._load_env_file(env_path, override=False, protected=frozenset())
    assert Path(config_mod.__file__).exists()  # sanity: module loaded
    assert "A" in __import__("os").environ and __import__("os").environ["A"] == "1"
    assert __import__("os").environ["B"] == "existing"
    assert __import__("os").environ["C"] == "3"

    # Now test override=True with protected preventing overwrite
    env_path.write_text("B=bold\nD=4\n")
    os = __import__("os")
    os.environ["B"] = "existing2"
    protected = frozenset({"B"})
    config_mod._load_env_file(env_path, override=True, protected=protected)
    assert os.environ["B"] == "existing2"  # protected not overwritten
    assert os.environ["D"] == "4"


# ---------------------------
# Tests for Settings
# ---------------------------
def test_settings_env_and_log_level_and_paper_fill_mode(monkeypatch):
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    s = Settings()
    # default env is development
    assert s.env == "development"
    assert s.is_dev
    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "BAD_ENV")
    with pytest.raises(ValueError):
        _ = Settings().env

    # log level valid / invalid
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert Settings().log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "INVALID")
    with pytest.raises(ValueError):
        _ = Settings().log_level

    # paper_fill_mode valid / invalid
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    assert Settings().paper_fill_mode == "instant"
    monkeypatch.setenv("PAPER_FILL_MODE", "PARTIAL")
    assert Settings().paper_fill_mode == "partial"
    monkeypatch.setenv("PAPER_FILL_MODE", "badvalue")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode


# ---------------------------
# Tests for validate_config.validate (basic parts)
# ---------------------------
def test_validate_config_basic(monkeypatch):
    # Ensure required vars missing -> errors
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("KABU_API_PASSWORD", raising=False)
    monkeypatch.setenv("KABUSYS_ENV", "development")
    errors, warnings, infos = validate_mod.validate()
    assert any("必須環境変数" in e for e in errors)
    # placeholder detection: set token to placeholder to get warning
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "abc_here")
    monkeypatch.setenv("KABU_API_PASSWORD", "your_value")
    errors, warnings, infos = validate_mod.validate()
    # both required set but placeholders produce warnings
    assert any("プレースホルダ" in w or "プレースホルダ値" in w or "プレースホルダ値" for w in warnings) or len(warnings) >= 1


# ---------------------------
# Tests for portfolio builder
# ---------------------------
def test_select_candidates_and_weights():
    signals = [
        {"code": "A", "signal_rank": 2, "score": 1.0},
        {"code": "B", "signal_rank": 1, "score": 1.0},
        {"code": "C", "signal_rank": 3, "score": 0.5},
    ]
    sel = pb.select_candidates(signals, max_positions=2)
    # A and B have same score, tie broken by signal_rank ascending -> B then A
    assert [s["code"] for s in sel] == ["B", "A"]

    # equal weights
    eq = pb.calc_equal_weights(sel)
    assert set(eq.keys()) == {"B", "A"}
    assert math.isclose(eq["B"], 0.5)
    assert math.isclose(eq["A"], 0.5)

    # score weights normal
    sw = pb.calc_score_weights(sel)
    assert set(sw.keys()) == {"B", "A"}
    # B and A have equal score -> equal weights
    assert math.isclose(sw["B"], sw["A"])

    # score weights fallback when total == 0
    zero_signals = [{"code": "X", "score": 0.0}, {"code": "Y", "score": 0.0}]
    with pytest.warns(None) as record:
        res = pb.calc_score_weights(zero_signals)
    # fallback to equal
    assert res == {"X": 0.5, "Y": 0.5}


# ---------------------------
# Tests for risk_adjustment
# ---------------------------
def test_apply_sector_cap_and_sell_codes(caplog):
    candidates = [{"code": "A", "score": 1.0}, {"code": "B", "score": 0.5}, {"code": "C", "score": 0.2}]
    sector_map = {"A": "s1", "B": "s1", "C": "unknown"}
    portfolio_value = 100000.0
    current_positions = {"A": 100, "B": 0}
    price_map = {"A": 400.0, "B": 100.0}
    # exposure for s1 = 100 * 400 = 40000 -> 40% of pv -> blocked if max_sector_pct=0.3
    filtered = ra.apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map, max_sector_pct=0.3)
    # codes in blocked sector s1 should be excluded; C unknown must remain
    assert all(c["code"] == "C" or sector_map.get(c["code"], "unknown") != "s1" for c in filtered)
    # test that sell_codes excludes code from exposure calculation
    filtered2 = ra.apply_sector_cap(candidates, sector_map, portfolio_value, {"A": 100, "B": 0}, price_map, max_sector_pct=0.3, sell_codes={"A"})
    # with A sold, sector exposure becomes 0 and so no blocking -> candidates unchanged
    assert len(filtered2) == 3


def test_calc_regime_multiplier(caplog):
    assert ra.calc_regime_multiplier("bull") == 1.0
    assert math.isclose(ra.calc_regime_multiplier("neutral"), 0.7)
    assert math.isclose(ra.calc_regime_multiplier("bear"), 0.3)
    caplog.clear()
    # unknown regime logs a warning and returns 1.0
    val = ra.calc_regime_multiplier("unknown_regime")
    assert val == 1.0
    assert any("未知のレジーム" in rec.getMessage() for rec in caplog.records)


# ---------------------------
# Tests for position_sizing (basic scenarios)
# ---------------------------
def test_calc_position_sizes_equal_and_scaling():
    # Two candidates, equal weights normalized externally
    candidates = [{"code": "AA", "score": 1}, {"code": "BB", "score": 1}]
    weights = {"AA": 0.5, "BB": 0.5}
    portfolio_value = 100000.0
    available_cash = 50000.0  # intentionally small to force scaling
    current_positions = {}
    open_prices = {"AA": 100.0, "BB": 100.0}
    # With max_utilization default 0.7, per-position alloc = 100000 * 0.5 * 0.7 = 35000 -> 350 shares -> floored to 300 (lot_size=100)
    out = ps.calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, allocation_method="equal", lot_size=100)
    # results should be multiples of lot_size
    for v in out.values():
        assert v % 100 == 0
    # total cost must not exceed available_cash + small epsilon
    total_cost = sum(out[c] * open_prices[c] for c in out)
    assert total_cost <= available_cash + 1e-6


def test_calc_position_sizes_risk_based_skips_missing_price(caplog):
    candidates = [{"code": "X", "score": 1}]
    weights = {}
    portfolio_value = 100000.0
    available_cash = 70000.0
    current_positions = {}
    open_prices = {"X": 0.0}  # missing/zero price -> skip
    out = ps.calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, allocation_method="risk_based")
    assert out == {}


# ---------------------------
# Tests for feature_exploration: rank, calc_ic, factor_summary
# ---------------------------
def test_rank_ties_and_order():
    vals = [1.0, 2.0, 2.0, 4.0]
    r = rank(vals)
    # ranks: 1, (2+3)/2+? -> average ranks for ties: positions 1->1, 2&3 -> 2.5, 4 -> 4
    assert len(r) == 4
    assert math.isclose(r[0], 1.0)
    assert math.isclose(r[1], 2.5)
    assert math.isclose(r[2], 2.5)
    assert math.isclose(r[3], 4.0)


def test_calc_ic_and_threshold():
    factor_records = [{"code": "A", "f": 1.0}, {"code": "B", "f": 2.0}, {"code": "C", "f": 3.0}]
    forward_records = [{"code": "A", "r": 1.0}, {"code": "B", "r": 2.0}, {"code": "C", "r": 3.0}]
    ic = calc_ic(factor_records, forward_records, "f", "r")
    assert ic is not None
    # Perfect rank correlation should give +1.0
    assert pytest.approx(ic, rel=1e-6) == 1.0

    # fewer than 3 valid pairs -> None
    ic2 = calc_ic([{"code": "A", "f": 1}], [{"code": "A", "r": 1}], "f", "r")
    assert ic2 is None


def test_factor_summary_basic():
    recs = [{"code": "A", "x": 1.0}, {"code": "B", "x": 3.0}, {"code": "C", "x": None}, {"code": "D", "x": 5.0}]
    res = factor_summary(recs, ["x"])
    assert "x" in res
    assert res["x"]["count"] == 3
    assert math.isclose(res["x"]["mean"], (1.0 + 3.0 + 5.0) / 3.0)


# ---------------------------
# Tests for news_nlp calc_news_window and _validate_and_extract
# ---------------------------
def test_calc_news_window_expected():
    td = date(2026, 3, 20)
    start, end = news_nlp_mod.calc_news_window(td)
    # start should be previous day at 06:00
    assert start == datetime(2026, 3, 19, 6, 0)
    # end should be previous day at 23:30
    assert end == datetime(2026, 3, 19, 23, 30)


def make_resp(content: str):
    # Build object with .choices[0].message.content attribute
    msg = SimpleNamespace(content=content)
    choice = SimpleNamespace(message=msg)
    resp = SimpleNamespace(choices=[choice])
    return resp


def test_validate_and_extract_basic_and_edge_cases(caplog):
    # valid content with numeric score > clip
    content = json.dumps({"results": [{"code": "1234", "score": 1.5}, {"code": 9999, "score": 0.2}]})
    resp = make_resp(content)
    extracted = news_nlp_mod._validate_and_extract(resp, {"1234", "9999"})
    # score should be clipped to 1.0 for code 1234
    assert extracted["1234"] == 1.0
    assert math.isclose(extracted["9999"], 0.2)

    # malformed JSON returns {}
    bad = "not json"
    resp2 = make_resp(bad)
    ex2 = news_nlp_mod._validate_and_extract(resp2, {"1234"})
    assert ex2 == {}

    # non-numeric score is ignored with warning
    content3 = json.dumps({"results": [{"code": "X", "score": "nan"}, {"code": "Y", "score": "3.14"}]})
    resp3 = make_resp(content3)
    out3 = news_nlp_mod._validate_and_extract(resp3, {"Y"})
    assert "Y" in out3


# ---------------------------
# Tests for process_priority: invalid level handling and delegation
# ---------------------------
def test_set_process_priority_invalid_level():
    with pytest.raises(ValueError):
        pp.set_process_priority("super_high")


def test_set_cpu_affinity_invalid_and_success(monkeypatch, caplog):
    # invalid cpu_count <1
    with pytest.raises(ValueError):
        pp.set_cpu_affinity(0)

    # simulate psutil.Process with cpu_affinity method
    class DummyProc:
        def __init__(self):
            self._affinity = None
            self.pid = 99999

        def cpu_affinity(self, pinned):
            self._affinity = pinned

        def nice(self, val):
            self._nice = val

    dummy = DummyProc()
    monkeypatch.setattr(pp, "psutil", mock.MagicMock(Process=lambda: dummy, cpu_count=lambda: 4))
    # Should not raise
    pp.set_cpu_affinity(2)
    assert dummy._affinity == [0, 1]


# End of tests
