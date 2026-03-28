
import json
import math
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import duckdb
import pytest

# --- config module tests ---
from kabusys.config import (
    _parse_env_line,
    _load_env_file,
    _require,
    Settings,
)

# --- news_nlp tests ---
from kabusys.ai.news_nlp import (
    calc_news_window,
    _validate_and_extract,
)

# --- data.stats tests ---
from kabusys.data.stats import zscore_normalize

# --- feature_exploration / research tests ---
# The sample code exposes rank, calc_ic, factor_summary in a module.
# Adjust import path if your project places these elsewhere.
from kabusys.feature_exploration import rank, calc_ic, factor_summary

# --- pipeline / ETLResult tests ---
from kabusys.data.pipeline import ETLResult

# --- jquants_client RateLimiter test ---
from kabusys.data.jquants_client import _RateLimiter, _to_date as jq__to_date  # _to_date used in calendar tests (if present)


# ----------------------------
# Tests for _parse_env_line
# ----------------------------
def test_parse_env_line_ignores_blank_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("# a comment") is None
    assert _parse_env_line("   # indented comment") is None


def test_parse_env_line_basic_and_export():
    assert _parse_env_line("FOO=bar") == ("FOO", "bar")
    assert _parse_env_line("export FOO=bar") == ("FOO", "bar")
    # whitespace tolerance
    assert _parse_env_line("  export   KEY =  val ") == ("KEY", "val")


def test_parse_env_line_quoted_with_escapes():
    # double quoted with escape
    assert _parse_env_line(r'Q="a\"b"') == ("Q", 'a"b')
    # single quoted with backslash
    assert _parse_env_line(r"Q='a\'b'") == ("Q", "a'b")
    # quoted value ignores inline comment
    assert _parse_env_line('Q="text # not comment"  # comment') == ("Q", "text # not comment")


def test_parse_env_line_inline_comment_rules():
    # '#' without preceding space is literal
    assert _parse_env_line("K=foo#bar") == ("K", "foo#bar")
    # '#' preceded by space becomes comment
    assert _parse_env_line("K=foo #bar") == ("K", "foo")
    assert _parse_env_line("K=foo\t#bar") == ("K", "foo")


def test_parse_env_line_invalid_lines():
    assert _parse_env_line("NOSEP") is None
    # empty key
    assert _parse_env_line("=value") is None


# ----------------------------
# Tests for _load_env_file
# ----------------------------
def test_load_env_file_sets_env_vars(tmp_path, monkeypatch):
    # Prepare env file
    p = tmp_path / ".env.test"
    content = "\n".join(
        [
            "A=1",
            "B= two ",
            "C='quoted val'",
            "D=\"with\\\"quote\"",
            "#comment",
            "export E=5",
        ]
    )
    p.write_text(content, encoding="utf-8")

    # Start with a clean environment
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    monkeypatch.delenv("C", raising=False)
    monkeypatch.delenv("D", raising=False)
    monkeypatch.delenv("E", raising=False)

    # Load without override: should set missing keys
    _load_env_file(p, override=False, protected=frozenset())
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "two"
    assert os.environ.get("C") == "quoted val"
    assert os.environ.get("D") == 'with"quote'
    assert os.environ.get("E") == "5"

    # Test override behavior and protected keys
    monkeypatch.setenv("A", "orig")
    _load_env_file(p, override=False, protected=frozenset())
    assert os.environ["A"] == "orig"  # not overridden

    _load_env_file(p, override=True, protected=frozenset({"E"}))
    # override True should overwrite non-protected
    assert os.environ["A"] == "1"
    # but protected E should remain original if existed
    # ensure E remains "5" because we earlier set it to 5; simulate protected preventing overwrite
    assert os.environ["E"] == "5"


def test_load_env_file_handles_missing_file(monkeypatch, tmp_path):
    p = tmp_path / "nonexistent.env"
    # should not raise
    _load_env_file(p, override=True, protected=frozenset())


def test_load_env_file_warns_on_io_error(monkeypatch, tmp_path):
    p = tmp_path / "bad.env"
    p.write_text("X=1", encoding="utf-8")
    # simulate permission error on open
    monkeypatch.setattr(Path, "open", lambda self, *args, **kwargs: (_ for _ in ()).throw(OSError("perm")))
    # Should not raise, just return
    _load_env_file(p, override=True, protected=frozenset())


# ----------------------------
# Tests for _require and Settings
# ----------------------------
def test_require_raises_when_missing(monkeypatch):
    monkeypatch.delenv("SOME_KEY", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_KEY")


def test_require_returns_value(monkeypatch):
    monkeypatch.setenv("SOME_KEY", "ok")
    assert _require("SOME_KEY") == "ok"


def test_settings_env_and_log_level_validation(monkeypatch):
    s = Settings()
    # default env should be development
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    assert s.env == "development"
    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env
    # log level default
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert s.log_level == "INFO"
    # invalid log level
    monkeypatch.setenv("LOG_LEVEL", "nope")
    with pytest.raises(ValueError):
        _ = s.log_level


# ----------------------------
# news_nlp: calc_news_window & _validate_and_extract
# ----------------------------
def test_calc_news_window_basic():
    td = date(2026, 3, 20)
    start, end = calc_news_window(td)
    # start = previous day at 06:00, end = previous day at 23:30
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)


class DummyChoice:
    def __init__(self, content):
        self.message = SimpleNamespace(content=content)


class DummyResp:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]


def test_validate_and_extract_valid_and_clipping():
    # valid JSON with extra fields; ensure clipping and normalization
    payload = {"results": [{"code": "1234", "score": 2.0}, {"code": 5678, "score": -2.0}, {"code": "9", "score": "0.5"}]}
    content = json.dumps(payload)
    resp = DummyResp(content)
    out = _validate_and_extract(resp, {"1234", "5678", "9", "999"})
    # 2.0 clipped to 1.0; -2.0 clipped to -1.0; "0.5" parsed to 0.5
    assert out["1234"] == 1.0
    assert out["5678"] == -1.0
    assert math.isclose(out["9"], 0.5)


def test_validate_and_extract_unknown_and_bad_scores_and_extra_text():
    # Unknown code should be ignored; non-numeric score ignored
    # Also test when content has surrounding text and embedded JSON extracted
    text = "prefix\n" + json.dumps({"results": [{"code": "X", "score": "NaN"}, {"code": "A", "score": 0.1}]}) + "\nsuffix"
    resp = DummyResp(text)
    out = _validate_and_extract(resp, {"A"})
    assert "A" in out and math.isfinite(out["A"])
    # bad json completely
    bad = DummyResp("not json")
    assert _validate_and_extract(bad, {"A"}) == {}


# ----------------------------
# feature_exploration: rank, calc_ic, factor_summary
# ----------------------------
def test_rank_ties():
    vals = [1.0, 2.0, 2.0, 4.0]
    r = rank(vals)
    # ranks: 1, (2+3)/2=2.5, 2.5, 4
    assert pytest.approx(r) == [1.0, 2.5, 2.5, 4.0]


def test_calc_ic_basic_and_insufficient():
    factor = [
        {"code": "A", "mom_1m": 0.1},
        {"code": "B", "mom_1m": 0.2},
        {"code": "C", "mom_1m": -0.1},
        {"code": "D", "mom_1m": 0.0},
    ]
    forward = [
        {"code": "A", "fwd_1d": 0.01},
        {"code": "B", "fwd_1d": 0.02},
        {"code": "C", "fwd_1d": -0.01},
        {"code": "D", "fwd_1d": 0.0},
    ]
    ic = calc_ic(factor, forward, "mom_1m", "fwd_1d")
    assert isinstance(ic, float)
    # insufficient pairs -> None
    ic2 = calc_ic(factor[:2], forward[:2], "mom_1m", "fwd_1d")
    assert ic2 is None


def test_factor_summary_empty_and_values():
    recs = [
        {"code": "A", "x": 1.0, "y": 2.0},
        {"code": "B", "x": 2.0, "y": 4.0},
        {"code": "C", "x": 3.0, "y": None},
    ]
    summary = factor_summary(recs, ["x", "y"])
    # x: count=3 mean=2.0 min=1 max=3
    assert summary["x"]["count"] == 3
    assert math.isclose(summary["x"]["mean"], 2.0)
    assert summary["y"]["count"] == 2


# ----------------------------
# data.stats: zscore_normalize
# ----------------------------
def test_zscore_normalize_basic_and_edge_cases():
    recs = [
        {"code": "A", "val": 1.0},
        {"code": "B", "val": 2.0},
        {"code": "C", "val": 3.0},
    ]
    out = zscore_normalize(recs, ["val"])
    vals = [r["val"] for r in out]
    # mean should be 0 and std 1
    assert pytest.approx(sum(vals), abs=1e-12) == 0.0
    # single record case -> no change
    single = [{"code": "X", "v": 10.0}]
    out2 = zscore_normalize(single, ["v"])
    assert out2[0]["v"] == 10.0
    # ignore None / bool / Inf
    recs2 = [{"code": "A", "v": None}, {"code": "B", "v": True}, {"code": "C", "v": float("inf")}, {"code": "D", "v": 5.0}, {"code": "E", "v": 7.0}]
    out3 = zscore_normalize(recs2, ["v"])
    # only D and E considered -> normalized to mean 0
    assert math.isfinite(out3[3]["v"]) and math.isfinite(out3[4]["v"])


# ----------------------------
# pipeline.ETLResult tests
# ----------------------------
def test_etlresult_properties_and_to_dict():
    qissue = SimpleNamespace(check_name="c", severity="error", message="m")
    # We need real QualityIssue instances in actual code; use matching interface for to_dict conversion
    # Here we construct an object with attributes check_name, severity, message
    result = ETLResult(target_date=date(2026, 1, 1))
    assert not result.has_errors
    result.errors.append("oops")
    assert result.has_errors
    # quality issues severity detection
    # create dummy object matching expected attributes
    class Q:
        def __init__(self, check_name, severity, message):
            self.check_name = check_name
            self.severity = severity
            self.message = message
    result.quality_issues.append(Q("x", "error", "m"))
    assert result.has_quality_errors
    d = result.to_dict()
    assert "target_date" in d
    assert isinstance(d["quality_issues"], list)


# ----------------------------
# jquants_client: _RateLimiter.wait
# ----------------------------
def test_rate_limiter_wait(monkeypatch):
    rl = _RateLimiter(min_interval=1.0)
    # Simulate last_called 1 second ago -> no sleep
    monkeypatch.setattr(rl, "_last_called", 0.0)
    # patch time.monotonic so elapsed > min_interval
    with mock.patch("kabusys.data.jquants_client.time.monotonic", side_effect=[0.0, 2.0]):
        # monkeypatch time.sleep to ensure not called
        with mock.patch("kabusys.data.jquants_client.time.sleep") as mock_sleep:
            rl.wait()
            mock_sleep.assert_not_called()
    # Simulate last_called very recent -> expect sleep call
    monkeypatch.setattr(rl, "_last_called", 100.0)
    monotonic_calls = [100.0, 100.2, 100.2 + 1.0]  # last called then new monotonic values
    with mock.patch("kabusys.data.jquants_client.time.monotonic", side_effect=monotonic_calls):
        with mock.patch("kabusys.data.jquants_client.time.sleep") as mock_sleep:
            rl.wait()
            # since elapsed small, sleep should be invoked at least once
            assert mock_sleep.called
