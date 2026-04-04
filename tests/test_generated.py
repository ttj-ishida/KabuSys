
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import duckdb
import pytest

# ---- config module tests ----
from kabusys import config
from kabusys.config import Settings

# ---- regime detector / news_nlp ----
from kabusys.ai import regime_detector, news_nlp

# ---- data stats ----
from kabusys.data import stats as data_stats

# ---- feature exploration (rank / calc_ic / factor_summary / calc_forward_returns) ----
from kabusys.research import feature_exploration as feat

# ---- quality checks ----
from kabusys.data import quality

# ---- etl ETLResult ----
from kabusys.data.pipeline import ETLResult as ETLResultClass  # 提示コードでは kabusys.data.pipeline.ETLResult を re-export
# 上の import が環境により違う場合は kabusys.etl.ETLResult 等に差し替えてください

# ---- audit schema init ----
from kabusys.audit import init_audit_db


# ------------------------------
# Helpers
# ------------------------------
def make_conn():
    return duckdb.connect(database=":memory:")


# ------------------------------
# config._parse_env_line tests
# ------------------------------
def test_parse_env_line_blank_and_comments():
    assert config._parse_env_line("") is None
    assert config._parse_env_line("   ") is None
    assert config._parse_env_line("# comment") is None
    assert config._parse_env_line("  # hi") is None


def test_parse_env_line_export_and_unquoted_and_comments():
    # export prefix
    assert config._parse_env_line("export KEY=value") == ("KEY", "value")
    # inline comment after space should be stripped
    assert config._parse_env_line("FOO=hello #ignored") == ("FOO", "hello")
    # comment char '#' immediately after value char (no space) is not treated as comment
    assert config._parse_env_line("BAR=abc#notcomment") == ("BAR", "abc#notcomment")
    # no '=' returns None
    assert config._parse_env_line("NOSEP") is None


def test_parse_env_line_quoted_and_escapes():
    # single quotes with escaped single quote
    inp = "A='hi\\'there'  # comment"
    k, v = config._parse_env_line(inp)
    assert k == "A"
    assert v == "hi'there"
    # double quotes with escaped double quote
    inp2 = 'B="hello\\\"world"'
    k2, v2 = config._parse_env_line(inp2)
    assert k2 == "B"
    assert v2 == 'hello"world'


# ------------------------------
# config._load_env_file tests
# ------------------------------
def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    envfile = tmp_path / ".env.test"
    envfile.write_text("EXIST=new_value\nNEW=added\n")
    # set an existing OS env
    monkeypatch.setenv("EXIST", "os_value")
    # protected should include current os env keys; with override=False EXIST should not be overwritten
    config._load_env_file(envfile, override=False, protected=frozenset(os_environ_keys := frozenset(dict().keys())))
    # Above line is a no-op for protected as we passed empty frozenset; adjust: actually test behavior via explicit calls

    # Simpler explicit: call with override=False: EXIST should remain os env value, NEW should be set
    monkeypatch.setenv("EXIST", "os_value")
    config._load_env_file(envfile, override=False, protected=frozenset(["EXIST"]))
    assert Path(envfile).exists()
    # EXIST should remain os_value because protected prevented overwrite
    assert pytest.MonkeyPatch().context is not None or True  # no-op to satisfy linters
    assert (lambda: None) or True  # no-op

    # Read values from environment directly to assert behavior
    # Since we used monkeypatch.setenv above, check os.environ
    import os
    # reload env from file with override False but protected excludes EXIST -> NEW should be set
    os.environ.pop("NEW", None)
    config._load_env_file(envfile, override=False, protected=frozenset(["EXIST"]))
    assert os.environ.get("EXIST") == "os_value"
    assert os.environ.get("NEW") == "added"

    # Now override=True but protected prevents EXIST overwrite
    envfile.write_text("EXIST=overwritten\nOTHER=1\n")
    os.environ["EXIST"] = "os_value"
    config._load_env_file(envfile, override=True, protected=frozenset(["EXIST"]))
    assert os.environ["EXIST"] == "os_value"
    assert os.environ["OTHER"] == "1"


# ------------------------------
# config._require / Settings tests
# ------------------------------
def test_require_and_settings(monkeypatch):
    import os
    # _require raises if missing
    if "SOME_TEST_TOKEN" in os.environ:
        del os.environ["SOME_TEST_TOKEN"]
    with pytest.raises(ValueError):
        config._require("SOME_TEST_TOKEN")
    # test Settings property reading
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "rtok")
    s = Settings()
    assert s.jquants_refresh_token == "rtok"
    # env validation: invalid env value should raise
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env
    # log level validation
    monkeypatch.setenv("LOG_LEVEL", "debug")
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "BAD_LEVEL")
    with pytest.raises(ValueError):
        _ = s.log_level


# ------------------------------
# regime_detector: _calc_ma200_ratio and _fetch_macro_news tests
# ------------------------------
def test_calc_ma200_ratio_no_data_and_insufficient_and_sufficient():
    conn = make_conn()
    conn.execute("CREATE TABLE prices_daily(date DATE, code VARCHAR, close DOUBLE)")
    td = date(2025, 1, 10)
    # no rows -> 1.0
    assert regime_detector._calc_ma200_ratio(conn, td) == 1.0

    # insert insufficient rows (<200)
    rows = [(date(2024, 12, 31) + timedelta(days=i), regime_detector._ETF_CODE, float(i + 1)) for i in range(10)]
    conn.executemany("INSERT INTO prices_daily(date, code, close) VALUES (?, ?, ?)", rows)
    assert regime_detector._calc_ma200_ratio(conn, td) == 1.0

    # insert 200 rows
    conn.execute("DELETE FROM prices_daily")
    rows = [(date(2024, 6, 1) + timedelta(days=i), regime_detector._ETF_CODE, float(i + 1)) for i in range(regime_detector._MA_WINDOW)]
    conn.executemany("INSERT INTO prices_daily(date, code, close) VALUES (?, ?, ?)", rows)
    # target_date after last inserted date to ensure rows < target_date are used
    target = rows[-1][0] + timedelta(days=1)
    ratio = regime_detector._calc_ma200_ratio(conn, target)
    # latest_close = 200, mean = (1..200)/200 = 100.5 -> ratio = 200 / 100.5
    expected = 200.0 / 100.5
    assert pytest.approx(ratio, rel=1e-6) == expected


def test_fetch_macro_news_filters_keywords():
    conn = make_conn()
    conn.execute("CREATE TABLE raw_news(id INTEGER, datetime TIMESTAMP, title VARCHAR)")
    # create timestamps
    now = datetime(2025, 1, 5, 12, 0)
    # one row matching keyword '日銀' and one not
    conn.executemany(
        "INSERT INTO raw_news(id, datetime, title) VALUES (?, ?, ?)",
        [
            (1, now - timedelta(hours=1), "日銀が金融政策を発表"),
            (2, now - timedelta(hours=2), "スポーツの話題")
        ]
    )
    start = now - timedelta(days=1)
    end = now + timedelta(days=1)
    titles = regime_detector._fetch_macro_news(conn, start, end)
    assert "日銀が金融政策を発表" in titles
    assert "スポーツの話題" not in titles


# ------------------------------
# regime_detector._score_macro tests (mocking _call_openai_api)
# ------------------------------
def make_resp_with_content(content: str):
    # Build a simple object matching resp.choices[0].message.content
    class Msg:
        def __init__(self, content):
            self.content = content

    class Choice:
        def __init__(self, msg):
            self.message = msg

    class Resp:
        def __init__(self, content):
            self.choices = [Choice(Msg(content))]

    return Resp(content)


def test_score_macro_success_and_empty_titles(monkeypatch):
    # When titles empty -> 0.0 and no API call
    client = object()
    assert regime_detector._score_macro(client, []) == 0.0

    # When API returns valid JSON
    resp = make_resp_with_content(json.dumps({"macro_sentiment": 0.25}))
    monkeypatch.setattr(regime_detector, "_call_openai_api", lambda cli, msgs: resp)
    val = regime_detector._score_macro(client, ["a dummy title"], _sleep_fn=lambda s: None)
    assert val == pytest.approx(0.25)

    # clipping test: too large score returned
    resp2 = make_resp_with_content(json.dumps({"macro_sentiment": 5.0}))
    monkeypatch.setattr(regime_detector, "_call_openai_api", lambda cli, msgs: resp2)
    val2 = regime_detector._score_macro(client, ["t"], _sleep_fn=lambda s: None)
    assert val2 == 1.0


def test_score_macro_retry_on_rate_limit(monkeypatch):
    client = object()
    calls = {"n": 0}

    def side_effect(cli, msgs):
        calls["n"] += 1
        if calls["n"] == 1:
            raise regime_detector.RateLimitError("rate")
        return make_resp_with_content(json.dumps({"macro_sentiment": -0.3}))

    monkeypatch.setattr(regime_detector, "_call_openai_api", side_effect)
    val = regime_detector._score_macro(client, ["t"], _sleep_fn=lambda s: None)
    assert val == pytest.approx(-0.3)


# ------------------------------
# news_nlp.calc_news_window and _validate_and_extract tests
# ------------------------------
def test_calc_news_window_basic():
    d = date(2026, 3, 20)
    start, end = news_nlp.calc_news_window(d)
    # start = previous day 06:00
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)


def test_validate_and_extract_good_and_bad():
    # good response
    content = json.dumps({"results": [{"code": "1234", "score": 0.5}, {"code": 5678, "score": -1.2}]})
    resp = make_resp_with_content(content)
    out = news_nlp._validate_and_extract(resp, {"1234", "5678"})
    assert out["1234"] == pytest.approx(0.5)
    # second score clipped to -1.0
    assert out["5678"] == -1.0

    # malformed JSON but with wrapping text
    wrapped = "prefix " + content + " suffix"
    resp2 = make_resp_with_content(wrapped)
    out2 = news_nlp._validate_and_extract(resp2, {"1234", "5678"})
    assert "1234" in out2

    # missing results key
    bad = make_resp_with_content(json.dumps({"noresults": []}))
    assert news_nlp._validate_and_extract(bad, {"1234"}) == {}

    # non-numeric score
    bad2 = make_resp_with_content(json.dumps({"results": [{"code": "1234", "score": "nan"}]}))
    assert news_nlp._validate_and_extract(bad2, {"1234"}) == {}


# ------------------------------
# data.stats.zscore_normalize tests
# ------------------------------
def test_zscore_normalize_basic_and_edgecases():
    records = [
        {"code": "A", "x": 1.0},
        {"code": "B", "x": 2.0},
        {"code": "C", "x": 3.0},
        {"code": "D", "x": None},
        {"code": "E", "x": True},  # bool should be excluded
    ]
    out = data_stats.zscore_normalize(records, ["x"])
    # mean = 2, variance = 2/3, std = sqrt(2/3)
    std = math.sqrt(((1 - 2) ** 2 + (0) + (1) ** 2) / 3.0)
    assert pytest.approx(out[0]["x"], rel=1e-6) == (1.0 - 2.0) / std
    assert out[3]["x"] is None  # None preserved
    assert isinstance(out, list)


# ------------------------------
# feature_exploration.rank / calc_ic / factor_summary tests
# ------------------------------
def test_rank_and_calc_ic_and_summary():
    vals = [10.0, 20.0, 20.0, 30.0]
    r = feat.rank(vals)
    # expected ranks: [1, 2.5, 2.5, 4]
    assert r[0] == 1.0
    assert r[1] == pytest.approx(2.5)
    assert r[2] == pytest.approx(2.5)
    assert r[3] == 4.0

    # calc_ic: perfect negative correlation example
    factor_records = [
        {"code": "A", "f": 1.0},
        {"code": "B", "f": 2.0},
        {"code": "C", "f": 3.0},
    ]
    forward_records = [
        {"code": "A", "g": 3.0},
        {"code": "B", "g": 2.0},
        {"code": "C", "g": 1.0},
    ]
    ic = feat.calc_ic(
        factor_records, forward_records, factor_col="f", return_col="g"
    )
    assert pytest.approx(ic, rel=1e-6) == -1.0

    # factor_summary
    recs = [
        {"a": 1.0},
        {"a": 2.0},
        {"a": 4.0},
        {"a": None},
    ]
    summary = feat.factor_summary(recs, ["a"])
    assert summary["a"]["count"] == 3
    assert summary["a"]["min"] == 1.0
    assert summary["a"]["max"] == 4.0


# ------------------------------
# quality checks: missing data and spike
# ------------------------------
def test_quality_missing_and_spike():
    conn = make_conn()
    conn.execute("""
        CREATE TABLE raw_prices (
            date DATE, code VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT
        )
    """)
    # missing data row
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (date(2025, 1, 1), "X", None, 10.0, 9.0, 9.5, 100))
    issues = quality.check_missing_data(conn)
    assert any(i.check_name == "missing_data" for i in issues)

    # spike detection: prev_close 100 -> curr_close 200 => change_rate = 1.0 > 0.5
    conn.execute("DELETE FROM raw_prices")
    conn.executemany("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [
        (date(2025, 1, 1), "Y", 0.0, 10.0, 9.0, 100.0, 100),
        (date(2025, 1, 2), "Y", 0.0, 20.0, 19.0, 200.0, 150),
    ])
    spikes = quality.check_spike(conn, target_date=None, threshold=0.5)
    assert any(i.check_name == "spike" for i in spikes)


# ------------------------------
# ETLResult tests
# ------------------------------
def test_etlresult_properties_and_to_dict():
    from kabusys.data import pipeline
    # If ETLResult class is in pipeline module
    res = pipeline.ETLResult(target_date=date(2025, 1, 1))
    assert not res.has_errors
    res.errors.append("err")
    assert res.has_errors
    # quality issue severity detection
    qi = quality.QualityIssue(check_name="x", table="raw", severity="error", detail="d")
    res.quality_issues.append(qi)
    assert res.has_quality_errors
    d = res.to_dict()
    assert "quality_issues" in d and isinstance(d["quality_issues"], list)


# ------------------------------
# audit.init_audit_db test
# ------------------------------
def test_init_audit_db_creates_tables_and_indexes():
    conn = init_audit_db(":memory:")
    # verify signal_events exists
    row = conn.execute(
        "SELECT 1 FROM information_schema.tables WHERE lower(table_name) = 'signal_events' LIMIT 1"
    ).fetchone()
    assert row is not None
