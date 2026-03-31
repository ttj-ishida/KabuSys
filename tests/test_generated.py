
import json
import math
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import duckdb
import pytest

# モジュールインポート（提示されたコードのパスに合わせています）
from kabusys import config as config_mod
from kabusys.ai import news_nlp
from kabusys.data import stats as stats_mod
from kabusys.data import jquants_client as jq_mod
from kabusys.data import pipeline as pipeline_mod
from kabusys.data import quality as quality_mod
from kabusys.research import feature_exploration as fe_mod


# -------------------------
# config._parse_env_line / _load_env_file / _require / Settings
# -------------------------
def test_parse_env_line_comments_and_blank():
    assert config_mod._parse_env_line("") is None
    assert config_mod._parse_env_line("   ") is None
    assert config_mod._parse_env_line("# comment") is None


def test_parse_env_line_export_and_no_equal():
    assert config_mod._parse_env_line("export KEY=val") == ("KEY", "val")
    assert config_mod._parse_env_line("NOSEP") is None


def test_parse_env_line_quoted_with_escapes_and_inline_comments():
    # quoted with escaped quote (\"), should preserve the escaped char and stop at closing quote
    line = 'FOO="a\\\"b"  # ignored'
    assert config_mod._parse_env_line(line) == ("FOO", 'a"b')

    # unquoted with '#' without preceding space -> '#' is part of value
    assert config_mod._parse_env_line("K=abc#no") == ("K", "abc#no")
    # unquoted with '#' preceded by space -> treat as comment
    assert config_mod._parse_env_line("K=abc #comment") == ("K", "abc")

    # empty key
    assert config_mod._parse_env_line("=val") is None
    assert config_mod._parse_env_line("export =val") is None


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    env_file.write_text("A=1\nB=2\nC=3\n")

    # ensure clean env
    monkeypatch.delenv("A", raising=False)
    monkeypatch.setenv("B", "old")
    # protected keys should not be overwritten when override=True
    protected = frozenset({"B"})

    config_mod._load_env_file(env_file, override=False, protected=protected)
    assert config_mod.os.environ.get("A") == "1"
    # B existed, override=False -> should not be changed
    assert config_mod.os.environ.get("B") == "old"

    # Now override True: A and C should be set/overwritten, but not B (protected)
    monkeypatch.setenv("B", "old")  # ensure
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("C", raising=False)
    config_mod._load_env_file(env_file, override=True, protected=protected)
    assert config_mod.os.environ.get("A") == "1"
    assert config_mod.os.environ.get("C") == "3"
    assert config_mod.os.environ.get("B") == "old"  # protected


def test_load_env_file_open_failure_warns(monkeypatch, tmp_path):
    broken = tmp_path / "broken.env"
    broken.touch()  # ファイルを作成して path.exists() を通過させる

    # Patch builtins.open to raise OSError when trying to open that specific path
    with mock.patch("builtins.open", side_effect=OSError("fail")):
        # capture warnings.warn by patching
        with mock.patch("warnings.warn") as w:
            # Should not raise
            config_mod._load_env_file(broken)
            assert w.called


def test_require_and_settings_env(monkeypatch):
    # _require raises when missing
    monkeypatch.delenv("SOME_KEY", raising=False)
    with pytest.raises(ValueError):
        config_mod._require("SOME_KEY")

    # _require returns value when present
    monkeypatch.setenv("SOME_KEY", "v1")
    assert config_mod._require("SOME_KEY") == "v1"

    # Settings: env validation and log level
    s = config_mod.Settings()
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert s.env == "live"
    assert s.is_live
    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    assert s.is_paper
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert s.is_dev

    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "INFO")
    assert s.log_level == "INFO"
    monkeypatch.setenv("LOG_LEVEL", "invalid_level")
    with pytest.raises(ValueError):
        _ = s.log_level

    # path expansion
    monkeypatch.setenv("DUCKDB_PATH", "~/mydb.duckdb")
    expanded = s.duckdb_path
    assert isinstance(expanded, Path)
    assert expanded.name == "mydb.duckdb"


# -------------------------
# news_nlp: calc_news_window and _validate_and_extract
# -------------------------
def test_calc_news_window_expected():
    t = date(2026, 3, 20)
    start, end = news_nlp.calc_news_window(t)
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)


def _make_resp(content: str):
    # mimic the shape: resp.choices[0].message.content
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_validate_and_extract_basic_and_noisy():
    content = json.dumps({
        "results": [
            {"code": "1234", "score": 0.5},
            {"code": 5678, "score": "-0.2"}
        ]
    })
    resp = _make_resp(content)
    out = news_nlp._validate_and_extract(resp, {"1234", "5678"})
    assert isinstance(out, dict)
    assert math.isclose(out["1234"], 0.5, rel_tol=1e-9)
    assert math.isclose(out["5678"], -0.2, rel_tol=1e-9)

    # noisy content: extra text before/after JSON - should extract outermost {...}
    noisy = "prefix text " + content + " trailing"
    resp2 = _make_resp(noisy)
    out2 = news_nlp._validate_and_extract(resp2, {"1234", "5678"})
    assert out2 == out

    # invalid JSON -> returns empty dict
    bad = "not a json"
    resp3 = _make_resp(bad)
    out3 = news_nlp._validate_and_extract(resp3, {"1234"})
    assert out3 == {}


# -------------------------
# research.feature_exploration: rank, calc_ic, factor_summary
# -------------------------
def test_rank_ties_average_rank():
    vals = [10.0, 20.0, 20.0, 30.0]
    r = fe_mod.rank(vals)
    # ranks should be [1.0, 2.5, 2.5, 4.0]
    assert len(r) == 4
    assert math.isclose(r[0], 1.0)
    assert math.isclose(r[1], 2.5)
    assert math.isclose(r[2], 2.5)
    assert math.isclose(r[3], 4.0)


def test_calc_ic_positive_and_negative():
    # perfect negative correlation
    factor_records = [
        {"code": "A", "mom_1m": 1.0},
        {"code": "B", "mom_1m": 2.0},
        {"code": "C", "mom_1m": 3.0},
    ]
    forward_records = [
        {"code": "A", "fwd_1d": 3.0},
        {"code": "B", "fwd_1d": 2.0},
        {"code": "C", "fwd_1d": 1.0},
    ]
    ic = fe_mod.calc_ic(factor_records, forward_records, "mom_1m", "fwd_1d")
    assert math.isclose(ic, -1.0, rel_tol=1e-9)

    # insufficient pairs -> None
    ic2 = fe_mod.calc_ic([], forward_records, "mom_1m", "fwd_1d")
    assert ic2 is None


def test_factor_summary_basic():
    records = [
        {"code": "A", "mom": 1.0},
        {"code": "B", "mom": 2.0},
        {"code": "C", "mom": 3.0},
        {"code": "D", "mom": None},
    ]
    summary = fe_mod.factor_summary(records, ["mom"])
    assert "mom" in summary
    s = summary["mom"]
    assert s["count"] == 3
    assert math.isclose(s["mean"], 2.0)
    assert math.isclose(s["min"], 1.0)
    assert math.isclose(s["max"], 3.0)
    # median for 3 sorted values [1,2,3] is 2
    assert math.isclose(s["median"], 2.0)


# -------------------------
# stats.zscore_normalize
# -------------------------
def test_zscore_normalize_basic():
    recs = [
        {"code": "A", "x": 1.0},
        {"code": "B", "x": 2.0},
        {"code": "C", "x": 3.0},
    ]
    out = stats_mod.zscore_normalize(recs, ["x"])
    # mean = 2.0, variance = 2/3, std = sqrt(2/3)
    std = math.sqrt(2.0 / 3.0)
    assert math.isclose(out[0]["x"], (1.0 - 2.0) / std, rel_tol=1e-9)
    assert math.isclose(out[1]["x"], 0.0, rel_tol=1e-9)
    assert math.isclose(out[2]["x"], (3.0 - 2.0) / std, rel_tol=1e-9)


# -------------------------
# pipeline.ETLResult & quality.QualityIssue
# -------------------------
def test_etlresult_properties_and_to_dict():
    qi1 = quality_mod.QualityIssue("missing_data", "raw_prices", "error", "detail1", rows=[{"a": 1}])
    qi2 = quality_mod.QualityIssue("spike", "raw_prices", "warning", "detail2", rows=[{"b": 2}])
    er = pipeline_mod.ETLResult(target_date=date(2026, 1, 1))
    er.quality_issues = [qi1, qi2]
    er.errors = ["err1"]
    assert er.has_errors
    assert er.has_quality_errors
    d = er.to_dict()
    assert "quality_issues" in d
    assert isinstance(d["quality_issues"], list)
    assert d["quality_issues"][0]["check_name"] == "missing_data"


# -------------------------
# jquants_client._RateLimiter.wait
# -------------------------
def test_rate_limiter_wait_calls_sleep():
    limiter = jq_mod._RateLimiter(min_interval=0.5)
    # set last_called to 0.0 so that monotonic=0.2 -> elapsed=0.2 wait=0.3
    limiter._last_called = 0.0
    with mock.patch("kabusys.data.jquants_client.time.monotonic", return_value=0.2):
        with mock.patch("kabusys.data.jquants_client.time.sleep") as sleep_mock:
            limiter.wait()
            # expect sleep called with roughly 0.3
            sleep_mock.assert_called_once()
            args, _ = sleep_mock.call_args
            assert pytest.approx(args[0], rel=1e-3) == 0.3
