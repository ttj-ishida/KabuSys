
import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# .env / .env.local の自動ロードを無効化してからインポートする
os.environ["KABUSYS_DISABLE_AUTO_ENV_LOAD"] = "1"

from kabusys.config import _parse_env_line, _load_env_file, Settings
from kabusys.tools.paper_verification_report import (
    _p95,
    _build_date_filter,
    _fmt_float,
    _fmt_int,
)
from kabusys.utils import process_priority
from kabusys.portfolio.portfolio_builder import (
    select_candidates,
    calc_equal_weights,
    calc_score_weights,
)
from kabusys.portfolio.risk_adjustment import apply_sector_cap, calc_regime_multiplier
from kabusys.portfolio.position_sizing import calc_position_sizes
from kabusys.ai.news_nlp import calc_news_window
from kabusys.research.feature_exploration import rank, calc_ic, factor_summary


# -------------------------
# config._parse_env_line
# -------------------------
def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # comment") is None
    assert _parse_env_line("NOEQ") is None


def test_parse_env_line_export_and_unquoted_comment():
    tup = _parse_env_line("export KEY=foo # a comment")
    assert tup == ("KEY", "foo")
    tup2 = _parse_env_line("BAR=hello#notacomment")
    # since '#' is immediately after value without preceding space it's part of value
    assert tup2 == ("BAR", "hello#notacomment")
    tup3 = _parse_env_line("BAZ=hello # a comment")
    assert tup3 == ("BAZ", "hello")


def test_parse_env_line_quoted_with_escapes():
    # backslash-escape inside quotes should be unescaped by parser
    # e.g. "a\ b" -> "a b"
    result = _parse_env_line("K='a\\ b' # trailing")
    assert result == ("K", "a b")
    # double quote variant
    result2 = _parse_env_line('Q="line1\\nline2"')
    # parser treats \n as 'n' (it doesn't interpret typical escape sequences),
    # but it appends the next character; so it becomes "linenline2" only if the escape was before 'n'
    # For our string, expect 'line1nline2' because backslash + 'n' -> 'n'
    assert result2 == ("Q", "line1nline2")


# -------------------------
# config._load_env_file
# -------------------------
def test_load_env_file_override_behavior(tmp_path, monkeypatch):
    env_file = tmp_path / ".envtest"
    env_file.write_text(
        "\n# comment\nFOO=bar\nBAZ=qux\n"
    )
    # ensure environment is clean for keys (monkeypatch tracks initial state for teardown)
    monkeypatch.delenv("FOO", raising=False)
    monkeypatch.delenv("BAZ", raising=False)

    # override=False: only set missing keys
    _load_env_file(env_file, override=False, protected=frozenset())

    assert os.environ.get("FOO") == "bar"
    assert os.environ.get("BAZ") == "qux"

    # override=True should overwrite unless key is in protected
    monkeypatch.setenv("FOO", "orig")
    protected = frozenset(["FOO"])
    _load_env_file(env_file, override=True, protected=protected)
    # protected key should remain unchanged
    assert os.environ.get("FOO") == "orig"
    # BAZ should be overwritten to qux
    assert os.environ.get("BAZ") == "qux"


# -------------------------
# Settings validations
# -------------------------
def test_settings_env_and_log_level(monkeypatch):
    monkeypatch.setenv("KABUSYS_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    s = Settings()
    assert s.env == "development"
    assert s.is_dev
    assert s.log_level == "INFO"

    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    s2 = Settings()
    assert s2.is_paper

    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = Settings().env

    # invalid log level
    monkeypatch.setenv("KABUSYS_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "NOPELEVEL")
    with pytest.raises(ValueError):
        _ = Settings().log_level


def test_settings_paper_fill_mode(monkeypatch):
    monkeypatch.setenv("PAPER_FILL_MODE", "instant")
    s = Settings()
    assert s.paper_fill_mode == "instant"

    monkeypatch.setenv("PAPER_FILL_MODE", "PARTIAL")
    assert Settings().paper_fill_mode == "partial"

    monkeypatch.setenv("PAPER_FILL_MODE", "invalid_mode")
    with pytest.raises(ValueError):
        _ = Settings().paper_fill_mode


# -------------------------
# paper_verification_report utils
# -------------------------
def test_p95_and_build_date_filter_and_formatters():
    assert _p95([]) is None
    vals = [1, 2, 3, 4, 5, 100]
    # 95th percentile index calculation: ceil(6*0.95)-1 = ceil(5.7)-1 = 6-1 = 5 -> vals[5] = 100
    assert _p95(vals) == 100

    clause, params = _build_date_filter("ts", None, None)
    assert clause == "" and params == []

    clause2, params2 = _build_date_filter("ts", "2026-01-01", None)
    assert "ts >= ?" in clause2 and params2 == ["2026-01-01"]

    clause3, params3 = _build_date_filter("ts", None, "2026-01-10")
    assert "ts <= ?" in clause3 and params3 == ["2026-01-10"]

    # both
    clause4, params4 = _build_date_filter("ts", "2026-01-01", "2026-01-10")
    assert "AND" in clause4 and params4 == ["2026-01-01", "2026-01-10"]

    assert _fmt_float(None) == "N/A"
    assert _fmt_float(3.14159, 2, " ms") == "3.14 ms"
    assert _fmt_int(None) == "N/A"
    assert _fmt_int(123) == "123"


# -------------------------
# process_priority
# -------------------------
def test_set_process_priority_invalid_level():
    with pytest.raises(ValueError):
        process_priority.set_process_priority("super-high")


def test_set_process_priority_windows(monkeypatch):
    # simulate Windows environment
    with patch("kabusys.utils.process_priority.platform.system", return_value="Windows"):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            process_priority.set_process_priority("high")
            # nice should be called with psutil.HIGH_PRIORITY_CLASS
            mock_proc.nice.assert_called_once_with(process_priority.psutil.HIGH_PRIORITY_CLASS)


def test_set_process_priority_posix(monkeypatch):
    with patch("kabusys.utils.process_priority.platform.system", return_value="Linux"):
        mock_proc = MagicMock()
        with patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
            process_priority.set_process_priority("low")
            mock_proc.nice.assert_called_once_with(process_priority._LINUX_NICE["low"])


def test_set_process_priority_unsupported_os(monkeypatch, caplog):
    with patch("kabusys.utils.process_priority.platform.system", return_value="Solaris"):
        # should log a warning and return without exception
        process_priority.set_process_priority("normal")


def test_set_cpu_affinity_basic_and_errors(monkeypatch):
    # cpu_count None -> no action
    assert process_priority.set_cpu_affinity(None) is None

    # invalid cpu_count
    with pytest.raises(ValueError):
        process_priority.set_cpu_affinity(0)

    # valid call: patch psutil.Process and cpu_count
    mock_proc = MagicMock()
    with patch("kabusys.utils.process_priority.psutil.Process", return_value=mock_proc):
        with patch("kabusys.utils.process_priority.psutil.cpu_count", return_value=4):
            process_priority.set_cpu_affinity(2)
            mock_proc.cpu_affinity.assert_called_once_with([0, 1])


# -------------------------
# portfolio builder
# -------------------------
def test_select_candidates_sort_and_empty():
    assert select_candidates([]) == []
    data = [
        {"code": "A", "score": 1.0, "signal_rank": 2},
        {"code": "B", "score": 2.0, "signal_rank": 5},
        {"code": "C", "score": 2.0, "signal_rank": 1},
    ]
    res = select_candidates(data, max_positions=2)
    # B and C have same score 2.0 -> choose smaller signal_rank first (C then B)
    assert [r["code"] for r in res] == ["C", "B"]


def test_calc_equal_and_score_weights(caplog):
    candidates = [{"code": "X"}, {"code": "Y"}]
    eq = calc_equal_weights(candidates)
    assert set(eq.keys()) == {"X", "Y"}
    assert math.isclose(eq["X"], 0.5) and math.isclose(eq["Y"], 0.5)

    # score weights with zero total -> fallback to equal weights and warn
    caplog.clear()
    with caplog.at_level("WARNING"):
        scores = [{"code": "A", "score": 0.0}, {"code": "B", "score": 0.0}]
        res = calc_score_weights(scores)
        assert "フォールバック" in caplog.text
        assert res == calc_equal_weights(scores)

    # normal score weighting
    scores2 = [{"code": "A", "score": 1.0}, {"code": "B", "score": 3.0}]
    sw = calc_score_weights(scores2)
    assert math.isclose(sw["A"], 1.0 / 4.0)
    assert math.isclose(sw["B"], 3.0 / 4.0)


# -------------------------
# risk_adjustment
# -------------------------
def test_apply_sector_cap_basic_and_unknown_and_sell_codes(caplog):
    candidates = [{"code": "AAA"}, {"code": "BBB"}, {"code": "CCC"}]
    sector_map = {"AAA": "tech", "BBB": "tech", "CCC": "finance"}
    # current positions: AAA and BBB huge exposures -> tech should be blocked
    portfolio_value = 1000.0
    current_positions = {"AAA": 10, "BBB": 10}
    price_map = {"AAA": 100.0, "BBB": 100.0, "CCC": 50.0}
    # exposure for tech = (10*100 + 10*100) = 2000 -> 2000/1000 = 2.0 > default 0.3
    filtered = apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map)
    # tech sector candidates AAA and BBB should be excluded; CCC remains
    assert len(filtered) == 1 and filtered[0]["code"] == "CCC"

    # unknown sector should not be blocked even if present in current_positions
    cand2 = [{"code": "UNK"}]
    sector_map2 = {}  # unknown mapping
    current_positions2 = {"UNK": 1000}
    res2 = apply_sector_cap(cand2, sector_map2, portfolio_value, current_positions2, price_map)
    assert res2 == cand2

    # sell_codes excludes exposures in calculation -> if we exclude large positions sector not blocked
    filtered2 = apply_sector_cap(candidates, sector_map, portfolio_value, current_positions, price_map, sell_codes={"AAA", "BBB"})
    assert len(filtered2) == 3  # no blocking because exposures removed


def test_calc_regime_multiplier_and_unknown(caplog):
    assert calc_regime_multiplier("bull") == 1.0
    assert calc_regime_multiplier("neutral") == 0.7
    assert calc_regime_multiplier("bear") == 0.3
    caplog.clear()
    with caplog.at_level("WARNING"):
        val = calc_regime_multiplier("mystery")
        assert val == 1.0
        assert "未知のレジーム" in caplog.text or "未知のレジーム" in caplog.text


# -------------------------
# position_sizing
# -------------------------
def test_calc_position_sizes_equal_and_score_methods():
    # equal/score mode
    candidates = [{"code": "AAA"}, {"code": "BBB"}]
    weights = {"AAA": 0.5, "BBB": 0.5}
    portfolio_value = 100000.0
    available_cash = 100000.0
    current_positions = {}
    open_prices = {"AAA": 100.0, "BBB": 200.0}
    sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, allocation_method="equal", lot_size=100, max_utilization=1.0, max_position_pct=1.0)
    # AAA: alloc=50k price=100 -> 500 shares -> lot_size 100 -> 500 ; BBB: 50k/200=250 -> 200 (floor to lot)
    assert sizes["AAA"] == 500
    assert sizes["BBB"] == 200

    # score mode is same as equal when weights provided
    sizes2 = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices, allocation_method="score", lot_size=100, max_utilization=1.0, max_position_pct=1.0)
    assert sizes2 == sizes


def test_calc_position_sizes_risk_based_and_scaling():
    # risk_based with lot_size=1 to avoid rounding to zero in small examples
    candidates = [{"code": "X"}, {"code": "Y"}]
    portfolio_value = 100000.0
    available_cash = 2000.0  # small available cash to force scaling step
    current_positions = {}
    open_prices = {"X": 10.0, "Y": 20.0}
    # use risk_pct so base shares are meaningful
    sizes = calc_position_sizes({}, candidates, portfolio_value, available_cash, current_positions, open_prices, allocation_method="risk_based", lot_size=1, risk_pct=0.01, stop_loss_pct=0.1, max_utilization=1.0)
    # initial raw_shares computed then possibly scaled down to fit available_cash -> result should be dict
    assert isinstance(sizes, dict)
    # make sure no negative shares and keys are subset of candidates
    assert all(s >= 0 for s in sizes.values())
    for k in sizes.keys():
        assert k in {"X", "Y"}


# -------------------------
# ai.news_nlp.calc_news_window
# -------------------------
def test_calc_news_window_expected():
    target = date(2026, 3, 20)
    start, end = calc_news_window(target)
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)


# -------------------------
# feature_exploration.rank / calc_ic / factor_summary
# -------------------------
def test_rank_with_ties_and_calc_ic_and_factor_summary():
    vals = [1.0, 2.0, 2.0, 3.0]
    ranks = rank(vals)
    # expected ranks: [1.0, 2.5, 2.5, 4.0]
    assert pytest.approx(ranks[0], rel=1e-9) == 1.0
    assert pytest.approx(ranks[1], rel=1e-9) == 2.5
    assert pytest.approx(ranks[2], rel=1e-9) == 2.5
    assert pytest.approx(ranks[3], rel=1e-9) == 4.0

    # calc_ic: less than 3 valid pairs -> None
    factor_records = [{"code": "A", "f": 1.0}, {"code": "B", "f": 2.0}]
    forward_records = [{"code": "A", "ret": 0.1}, {"code": "B", "ret": 0.2}]
    assert calc_ic(factor_records, forward_records, "f", "ret") is None

    # With 3 pairs and ordered relation, IC should be close to 1.0
    factor_records = [
        {"code": "A", "f": 1.0},
        {"code": "B", "f": 2.0},
        {"code": "C", "f": 3.0},
    ]
    forward_records = [
        {"code": "A", "r": 0.1},
        {"code": "B", "r": 0.2},
        {"code": "C", "r": 0.3},
    ]
    ic = calc_ic(factor_records, forward_records, "f", "r")
    assert ic is not None
    assert ic > 0.9

    # factor_summary empty
    empty_summary = factor_summary([], ["a", "b"])
    assert empty_summary["a"]["count"] == 0
    assert empty_summary["a"]["mean"] is None

    # factor_summary with values
    records = [{"x": 1.0, "y": 2.0}, {"x": 3.0, "y": 4.0}, {"x": 5.0, "y": None}]
    summ = factor_summary(records, ["x", "y"])
    assert summ["x"]["count"] == 3
    assert pytest.approx(summ["x"]["mean"], rel=1e-9) == (1.0 + 3.0 + 5.0) / 3.0
    assert summ["y"]["count"] == 2  # one None filtered out
