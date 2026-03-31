
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import duckdb
import pytest

# --- adjust imports below to your package layout if needed ---
from kabusys.config import _parse_env_line, _load_env_file, _require, Settings
from kabusys.ai import regime_detector as rd
from kabusys.ai import news_nlp as nn
from kabusys.data import stats as ds
from kabusys.research import feature_exploration as fe
from kabusys.data.etl import ETLResult
from kabusys.data import quality


# ----------------------------
# config module tests
# ----------------------------

def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # a comment ") is None
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    # export prefix
    assert _parse_env_line("export KEY2=  123  ") == ("KEY2", "123")
    # inline comment after value with leading space is trimmed
    assert _parse_env_line("A=hello #comment") == ("A", "hello")
    # equals missing -> invalid
    assert _parse_env_line("NOEQUALS") is None

def test_parse_env_line_quoted_and_escapes():
    # single quotes with escaped quote
    line = "X='a\\'b'#ignored"
    k, v = _parse_env_line(line)
    assert k == "X" and v == "a'b"
    # double quotes with escaped char
    line2 = 'Y="line\\ntext"'
    k2, v2 = _parse_env_line(line2)
    assert k2 == "Y" and "line" in v2

def test_load_env_file_and_override(tmp_path, monkeypatch):
    envfile = tmp_path / ".env.test"
    envfile.write_text("A=1\nB=2\n#C=3\n")
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    # load without override: sets keys not present
    _load_env_file(envfile, override=False, protected=frozenset())
    assert "A" in __import__("os").environ and __import__("os").environ["A"] == "1"
    # override behavior with protected
    __import__("os").environ["P"] = "orig"
    envfile.write_text("P=fromfile\nQ=qq\n")
    _load_env_file(envfile, override=True, protected=frozenset(__import__("os").environ.keys()))
    # P is protected so not overridden
    assert __import__("os").environ["P"] == "orig"
    # Q should be set (not protected existing earlier)
    assert __import__("os").environ.get("Q") == "qq"

def test_require_and_settings_env_log_level(monkeypatch):
    monkeypatch.delenv("SOME_MISSING", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_MISSING")
    monkeypatch.setenv("SOME_MISSING", "ok")
    assert _require("SOME_MISSING") == "ok"

    s = Settings()
    # env default
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert s.env == "development"
    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "INVALID_ENV")
    with pytest.raises(ValueError):
        _ = s.env
    # log level valid/invalid
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "nope")
    with pytest.raises(ValueError):
        _ = s.log_level


# ----------------------------
# regime_detector tests (duckdb + OpenAI mocks)
# ----------------------------

def _make_prices_table(conn):
    conn.execute("""
        CREATE TABLE prices_daily (
            date DATE,
            code VARCHAR,
            close DOUBLE
        )
    """)

def _insert_prices(conn, start_date, code, closes):
    d = start_date
    for c in closes:
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [d, code, c])
        d -= timedelta(days=1)


def test_calc_ma200_ratio_no_data_logs_and_returns_one(caplog):
    conn = duckdb.connect(":memory:")
    _make_prices_table(conn)
    val = rd._calc_ma200_ratio(conn, date(2026, 3, 20))
    assert val == 1.0
    assert "_calc_ma200_ratio" in caplog.text

def test_calc_ma200_ratio_insufficient_rows_returns_one(caplog):
    conn = duckdb.connect(":memory:")
    _make_prices_table(conn)
    # insert fewer than required
    rd._MA_WINDOW  # ensure attribute exists
    _insert_prices(conn, date(2026,3,20), rd._ETF_CODE, [100.0] * (rd._MA_WINDOW - 1))
    val = rd._calc_ma200_ratio(conn, date(2026,3,20))
    assert val == 1.0
    assert "データ不足" in caplog.text or "_calc_ma200_ratio" in caplog.text

def test_calc_ma200_ratio_exact_window_computation():
    conn = duckdb.connect(":memory:")
    _make_prices_table(conn)
    # クエリは date < target_date（排他）のため start_date は target_date の 1 日前にする。
    # これで 200 行すべてが date < date(2026,3,20) に収まる。
    # MA200 = (110 + 100 * 199) / 200 = 100.05; ratio = 110 / 100.05
    closes = [110.0] + [100.0] * (rd._MA_WINDOW - 1)
    _insert_prices(conn, date(2026, 3, 19), rd._ETF_CODE, closes)
    val = rd._calc_ma200_ratio(conn, date(2026, 3, 20))
    expected = 110.0 / ((110.0 + 100.0 * 199) / 200)
    assert pytest.approx(val, rel=1e-6) == expected

def test_fetch_macro_news_filters_keywords_and_window():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE raw_news (
            id INTEGER,
            datetime TIMESTAMP,
            title VARCHAR,
            content VARCHAR
        )
    """)
    window_start = datetime(2026,3,18,0,0)
    window_end = datetime(2026,3,19,0,0)
    # one matching title, one non-matching
    conn.execute("INSERT INTO raw_news VALUES (1, ?, ?, ?)",
                 [window_start + timedelta(hours=1), "日銀が会合", "本文"])
    conn.execute("INSERT INTO raw_news VALUES (2, ?, ?, ?)",
                 [window_start + timedelta(hours=2), "スポーツ", "本文"])
    titles = rd._fetch_macro_news(conn, window_start, window_end)
    assert any("日銀" in t for t in titles)
    assert all(isinstance(t, str) for t in titles)

def test_score_macro_success_and_failures(monkeypatch):
    # prepare a fake client and response
    class FakeChoice:
        def __init__(self, content):
            self.message = mock.Mock()
            self.message.content = content

    class FakeResp:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    def make_client():
        return object()

    # success: valid JSON
    monkeypatch.setattr(rd, "_call_openai_api", lambda client, messages: FakeResp('{"macro_sentiment": 0.5}'))
    score = rd._score_macro(make_client(), ["t1"])
    assert score == 0.5

    # empty titles -> 0.0 and no call
    monkeypatch.setattr(rd, "_call_openai_api", lambda client, messages: (_ for _ in ()).throw(AssertionError("should not be called")))
    score2 = rd._score_macro(make_client(), [])
    assert score2 == 0.0

    # API raises RateLimitError first then succeed; ensure sleep called
    class DummyRateLimit(Exception):
        pass

    monkeypatch.setattr(rd, "RateLimitError", DummyRateLimit)
    calls = {"sleep": 0}
    def sleep_fn(sec):
        calls["sleep"] += 1

    call_seq = [mock.DEFAULT]  # placeholder
    def side_effect(client, messages):
        if not hasattr(side_effect, "cnt"):
            side_effect.cnt = 0
        if side_effect.cnt == 0:
            side_effect.cnt += 1
            raise DummyRateLimit("rate")
        return FakeResp('{"macro_sentiment": -0.3}')
    monkeypatch.setattr(rd, "_call_openai_api", side_effect)
    s = rd._score_macro(make_client(), ["t1"], _sleep_fn=sleep_fn)
    assert pytest.approx(s, rel=1e-6) == -0.3
    assert calls["sleep"] == 1

    # malformed JSON -> fallback 0.0
    monkeypatch.setattr(rd, "_call_openai_api", lambda client, messages: FakeResp("NOT JSON"))
    s2 = rd._score_macro(make_client(), ["t1"])
    assert s2 == 0.0


# ----------------------------
# news_nlp tests
# ----------------------------

def test_calc_news_window_expected():
    target = date(2026,3,20)
    start, end = nn.calc_news_window(target)
    assert start == datetime(2026,3,19,6,0)
    assert end == datetime(2026,3,19,23,30)

def test__validate_and_extract_good_and_bad():
    # build fake resp object
    class FakeMessage:
        def __init__(self, content):
            self.content = content
    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)
    class FakeResp:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    # good JSON
    requested = {"1234"}
    resp = FakeResp(json.dumps({"results":[{"code":"1234","score": 0.7},{"code":"9999","score": 0.1}]}))
    out = nn._validate_and_extract(resp, requested)
    assert out == {"1234": 0.7}

    # surrounding text with braces
    resp2 = FakeResp("prefix " + json.dumps({"results":[{"code":"1234","score": -2.0}]}) + " suffix")
    out2 = nn._validate_and_extract(resp2, requested)
    # clipped to -1.0
    assert out2["1234"] == -1.0

    # invalid JSON -> empty
    resp3 = FakeResp("no json here")
    assert nn._validate_and_extract(resp3, requested) == {}

def test__fetch_articles_and_score_chunk(monkeypatch):
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE raw_news (
            id INTEGER,
            datetime TIMESTAMP,
            title VARCHAR,
            content VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE news_symbols (
            news_id INTEGER,
            code VARCHAR
        )
    """)
    # insert two articles for code '1111' and one for '2222'
    base_dt = datetime(2026,3,19,7,0)
    conn.execute("INSERT INTO raw_news VALUES (1, ?, ?, ?)", [base_dt, "t1", "c1"])
    conn.execute("INSERT INTO raw_news VALUES (2, ?, ?, ?)", [base_dt - timedelta(hours=1), "t2", "c2"])
    conn.execute("INSERT INTO raw_news VALUES (3, ?, ?, ?)", [base_dt, "t3", "c3"])
    conn.execute("INSERT INTO news_symbols VALUES (1, '1111')")
    conn.execute("INSERT INTO news_symbols VALUES (2, '1111')")
    conn.execute("INSERT INTO news_symbols VALUES (3, '2222')")

    start = base_dt - timedelta(days=1)
    end = base_dt + timedelta(days=1)
    article_map = nn._fetch_articles(conn, start, end)
    assert "1111" in article_map and "2222" in article_map
    assert len(article_map["1111"]) == 2

    # prepare client response for _score_chunk
    class FakeMessage:
        def __init__(self, content):
            self.content = content
    class FakeChoice:
        def __init__(self, content):
            self.message = FakeMessage(content)
    class FakeResp:
        def __init__(self, content):
            self.choices = [FakeChoice(content)]

    def fake_call(client, messages):
        return FakeResp(json.dumps({"results":[{"code":"1111","score":0.2},{"code":"2222","score":-0.4}]}))

    monkeypatch.setattr(nn, "_call_openai_api", fake_call)
    res = nn._score_chunk(object(), ["1111","2222"], article_map)
    assert pytest.approx(res["1111"], rel=1e-9) == 0.2
    assert pytest.approx(res["2222"], rel=1e-9) == -0.4

    # test retry path: raise rate error then success
    class DummyRate(Exception):
        pass
    monkeypatch.setattr(nn, "RateLimitError", DummyRate)
    calls = {"sleep":0}
    def sleep_noop(sec):
        calls["sleep"] += 1
    seq = {"cnt":0}
    def call_seq(client, messages):
        if seq["cnt"] == 0:
            seq["cnt"] += 1
            raise DummyRate("rl")
        return FakeResp(json.dumps({"results":[{"code":"1111","score":0.9},{"code":"2222","score":0.1}]}))
    monkeypatch.setattr(nn, "_call_openai_api", call_seq)
    with mock.patch("time.sleep", lambda s: sleep_noop(s)):
        out = nn._score_chunk(object(), ["1111","2222"], article_map)
    assert out["1111"] == pytest.approx(0.9)
    assert calls["sleep"] >= 1


# ----------------------------
# stats & research tests
# ----------------------------

def test_zscore_normalize_basic():
    recs = [
        {"code":"A","val": 10},
        {"code":"B","val": 20},
        {"code":"C","val": 30},
    ]
    out = ds.zscore_normalize(recs, ["val"])
    vals = [r["val"] for r in out]
    # mean should be approximately 0
    assert abs(sum(vals)) < 1e-12
    # std approx 1
    mean = sum(vals)/len(vals)
    var = sum((v-mean)**2 for v in vals)/len(vals)
    assert math.isclose(math.sqrt(var), 1.0, rel_tol=1e-6)

def test_rank_and_calc_ic_and_factor_summary():
    vals = [10.0, 20.0, 20.0, 40.0]
    r = fe.rank(vals)
    # expected ranks: [1, 2.5, 2.5, 4]
    assert pytest.approx(r[0]) == 1.0
    assert pytest.approx(r[1]) == 2.5
    assert pytest.approx(r[2]) == 2.5
    assert pytest.approx(r[3]) == 4.0

    # calc_ic with insufficient pairs -> None
    factor_records = [{"code":"A","f":1.0},{"code":"B","f":None}]
    forward_records = [{"code":"A","fwd":None}]
    assert fe.calc_ic(factor_records, forward_records, "f", "fwd") is None

    # sufficient pairs
    factor_records = [
        {"code":"A","fac":1.0},
        {"code":"B","fac":2.0},
        {"code":"C","fac":3.0},
    ]
    forward_records = [
        {"code":"A","fwd":0.1},
        {"code":"B","fwd":0.2},
        {"code":"C","fwd":0.3},
    ]
    ic = fe.calc_ic(factor_records, forward_records, "fac", "fwd")
    assert isinstance(ic, float)

    # factor_summary
    recs = [
        {"code":"A","x":1.0},
        {"code":"B","x":2.0},
        {"code":"C","x":3.0},
        {"code":"D","x":None},
    ]
    summary = fe.factor_summary(recs, ["x","missing"])
    assert summary["x"]["count"] == 3
    assert summary["missing"]["count"] == 0
    assert summary["x"]["min"] == 1.0
    assert "median" in summary["x"]

# ----------------------------
# ETLResult tests
# ----------------------------

def test_etlresult_properties_and_to_dict():
    er = ETLResult(target_date=date(2026,3,20))
    assert not er.has_errors
    # create a QualityIssue with severity error
    qi = quality.QualityIssue(check_name="missing_data", table="raw_prices", severity="error", detail="d", rows=[])
    er.quality_issues.append(qi)
    assert er.has_quality_errors
    d = er.to_dict()
    assert isinstance(d, dict)
    assert d["quality_issues"][0]["check_name"] == "missing_data"
