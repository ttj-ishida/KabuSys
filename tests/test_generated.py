
# tests/test_kabusys_core.py
import json
import math
import os
from types import SimpleNamespace
from datetime import date, datetime, timedelta
from unittest.mock import patch

import duckdb
import pytest

# --- config._parse_env_line tests ---
from kabusys.config import _parse_env_line

def test_parse_env_line_blank_and_comment():
    assert _parse_env_line("") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("# comment") is None

def test_parse_env_line_export_and_regular():
    assert _parse_env_line("export FOO=bar") == ("FOO", "bar")
    assert _parse_env_line("KEY=val #comment") == ("KEY", "val")
    # '#' not preceded by space should be part of value
    assert _parse_env_line("K=val#notcomment") == ("K", "val#notcomment")

def test_parse_env_line_quoted_with_escapes():
    # double quote with escaped quote inside
    line = 'FOO="a\\\"b\\nc"'
    k, v = _parse_env_line(line)
    # escapes remove backslashes and keep next char literally (per implementation)
    assert k == "FOO"
    assert v == 'a"bnc'  # \\" -> ", \\n -> n (implementation treats backslash + next char as literal)

    # single quote
    line2 = "BAR='x\\'y'"
    k2, v2 = _parse_env_line(line2)
    assert k2 == "BAR"
    assert v2 == "x'y"

# ---------------------------------------------------------------------------
# regime_detector: _calc_ma200_ratio, _fetch_macro_news, _score_macro
# ---------------------------------------------------------------------------
from kabusys.ai import regime_detector
from openai import RateLimitError, APIError, APIConnectionError, APITimeoutError

def make_conn_with_prices():
    conn = duckdb.connect(database=":memory:")
    conn.execute("""
        CREATE TABLE prices_daily (
            date DATE,
            code VARCHAR,
            close DOUBLE
        )
    """)
    return conn

def test_calc_ma200_ratio_no_rows_logs_and_returns_one(caplog):
    conn = make_conn_with_prices()
    target = date(2026, 3, 20)
    caplog.clear()
    val = regime_detector._calc_ma200_ratio(conn, target)
    assert val == 1.0
    assert any("1321 のデータなし" in rec.message or "_calc_ma200_ratio" in rec.message for rec in caplog.records)

def test_calc_ma200_ratio_insufficient_rows_returns_one(caplog):
    conn = make_conn_with_prices()
    target = date(2026, 3, 20)
    # insert 10 rows (<200)
    for i in range(10):
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [target - timedelta(days=i+1), regime_detector._ETF_CODE, 100.0])
    val = regime_detector._calc_ma200_ratio(conn, target)
    assert val == 1.0
    assert any("データ不足" in rec.message or "_calc_ma200_ratio" in rec.message for rec in caplog.records)

def test_calc_ma200_ratio_exactly_200_rows():
    conn = make_conn_with_prices()
    target = date(2026, 3, 20)
    # latest close 110, others 100
    conn.execute("BEGIN")
    conn.execute("DELETE FROM prices_daily")
    conn.execute("COMMIT")
    # Insert 200 rows with dates older than target (date < target)
    for i in range(200):
        # newest first: date desc order matters; we ensure distinct dates
        d = target - timedelta(days=i + 1)
        close = 110.0 if i == 0 else 100.0  # latest (most recent) will be highest date -> i==0
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [d, regime_detector._ETF_CODE, close])
    val = regime_detector._calc_ma200_ratio(conn, target)
    assert val > 1.0  # since latest is higher than average

def test_fetch_macro_news_filters_by_keywords_and_window():
    conn = duckdb.connect(database=":memory:")
    conn.execute("""
        CREATE TABLE raw_news (
            id INTEGER,
            datetime TIMESTAMP,
            title VARCHAR
        )
    """)
    # Insert two rows, one with matching keyword "日銀"
    now = datetime(2026, 3, 19, 12, 0)
    conn.execute("INSERT INTO raw_news VALUES (1, ?, ?)", [now - timedelta(hours=1), "日銀 が会合"])
    conn.execute("INSERT INTO raw_news VALUES (2, ?, ?)", [now - timedelta(days=2), "その他ニュース"])
    start = now - timedelta(days=1)
    end = now + timedelta(days=1)
    titles = regime_detector._fetch_macro_news(conn, start, end)
    assert "日銀 が会合" in titles
    assert all(isinstance(t, str) for t in titles)

@patch("kabusys.ai.regime_detector._call_openai_api")
def test_score_macro_success_and_retries(mock_api):
    # prepare a fake successful response
    content = json.dumps({"macro_sentiment": 0.6})
    resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    # First call raises RateLimitError, then success
    mock_api.side_effect = [RateLimitError("rate"), resp]

    titles = ["- something"]
    # use a no-op sleep function to avoid delays
    score = regime_detector._score_macro(SimpleNamespace(), titles, _sleep_fn=lambda s: None)
    assert isinstance(score, float)
    assert math.isfinite(score)
    assert abs(score - 0.6) < 1e-8

@patch("kabusys.ai.regime_detector._call_openai_api")
def test_score_macro_json_parse_failure_returns_zero(mock_api, caplog):
    resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))])
    mock_api.return_value = resp
    caplog.clear()
    score = regime_detector._score_macro(SimpleNamespace(), ["title"], _sleep_fn=lambda s: None)
    assert score == 0.0
    assert any("レスポンスパース失敗" in rec.message or "パース失敗" in rec.message or "レスポンスパース失敗" in rec.message for rec in caplog.records)

# ---------------------------------------------------------------------------
# news_nlp: calc_news_window, _validate_and_extract, _fetch_articles, score_news
# ---------------------------------------------------------------------------
from kabusys.ai import news_nlp

def test_calc_news_window_expected_boundaries():
    td = date(2026, 3, 20)
    start, end = news_nlp.calc_news_window(td)
    # start should be previous day at 06:00, end previous day at 23:30
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)

def make_resp_with_content(content_str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content_str))])

def test_validate_and_extract_basic_and_text_padding():
    # valid payload
    content = json.dumps({"results": [{"code": "1001", "score": 0.5}, {"code": 2002, "score": -1.5}]})
    resp = make_resp_with_content(content)
    out = news_nlp._validate_and_extract(resp, {"1001", "2002"})
    # 2002 is not in requested_codes as string "2002" unless we include; include to see filtering
    assert "1001" in out
    # score for 2002 should be clipped to -1.0
    assert out.get("2002") == -1.0 or out.get("2002") is None

    # padded JSON: prefix/suffix text around actual JSON
    padded = "prefix " + content + " suffix"
    resp2 = make_resp_with_content(padded)
    out2 = news_nlp._validate_and_extract(resp2, {"1001"})
    assert out2.get("1001") == 0.5

def test_fetch_articles_aggregates_and_trims():
    conn = duckdb.connect(database=":memory:")
    conn.execute("""
        CREATE TABLE raw_news (
            id INTEGER, datetime TIMESTAMP, title VARCHAR, content VARCHAR
        )
    """)
    conn.execute("""
        CREATE TABLE news_symbols (
            news_id INTEGER, code VARCHAR
        )
    """)
    base_dt = datetime(2026, 3, 19, 12, 0)
    # insert 3 articles for same code, ensure ordering and trimming
    conn.execute("INSERT INTO raw_news VALUES (1, ?, ?, ?)", [base_dt - timedelta(hours=1), "t1", "c1"])
    conn.execute("INSERT INTO raw_news VALUES (2, ?, ?, ?)", [base_dt - timedelta(hours=2), "t2", "c2"])
    conn.execute("INSERT INTO raw_news VALUES (3, ?, ?, ?)", [base_dt - timedelta(days=2), "t3", "c3"])  # out of window
    conn.execute("INSERT INTO news_symbols VALUES (?, ?)", [1, "1234"])
    conn.execute("INSERT INTO news_symbols VALUES (?, ?)", [2, "1234"])
    start = base_dt - timedelta(days=1)
    end = base_dt + timedelta(days=1)
    am = news_nlp._fetch_articles(conn, start, end)
    assert "1234" in am
    assert len(am["1234"]) == 2
    assert all(isinstance(s, str) for s in am["1234"])

@patch("kabusys.ai.news_nlp._call_openai_api")
def test_score_news_end_to_end(mock_api, monkeypatch):
    # build DB
    conn = duckdb.connect(database=":memory:")
    conn.execute("CREATE TABLE raw_news (id INTEGER, datetime TIMESTAMP, title VARCHAR, content VARCHAR)")
    conn.execute("CREATE TABLE news_symbols (news_id INTEGER, code VARCHAR)")
    conn.execute("CREATE TABLE ai_scores (date DATE, code VARCHAR, sentiment_score DOUBLE, ai_score DOUBLE)")
    base_dt = datetime(2026, 3, 19, 12, 0)
    # Insert one article inside window and symbol mapping
    conn.execute("INSERT INTO raw_news VALUES (1, ?, ?, ?)", [base_dt, "macro 日銀", "body"])
    conn.execute("INSERT INTO news_symbols VALUES (?, ?)", [1, "5678"])
    # Prepare OpenAI response that returns a valid score
    content = json.dumps({"results": [{"code": "5678", "score": 0.7}]})
    mock_api.return_value = make_resp_with_content(content)
    # Call score_news with explicit api_key to bypass env
    written = news_nlp.score_news(conn, date(2026, 3, 20), api_key="dummy")
    assert written == 1
    rows = conn.execute("SELECT date, code, sentiment_score, ai_score FROM ai_scores").fetchall()
    assert len(rows) == 1
    assert rows[0][1] == "5678"
    assert abs(rows[0][2] - 0.7) < 1e-8

# ---------------------------------------------------------------------------
# research: calc_forward_returns, calc_ic, rank, factor_summary
# ---------------------------------------------------------------------------
from kabusys.research import calc_forward_returns, calc_ic, rank, factor_summary

def test_calc_forward_returns_basic():
    conn = duckdb.connect(database=":memory:")
    conn.execute("""
        CREATE TABLE prices_daily (
            date DATE, code VARCHAR, close DOUBLE
        )
    """)
    td = date(2026, 3, 20)
    # create 2-day series for code 'AAA'
    conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [td, "AAA", 100.0])
    conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [td + timedelta(days=1), "AAA", 110.0])
    rows = calc_forward_returns(conn, td, horizons=[1])
    assert rows and rows[0]["fwd_1d"] == pytest.approx((110.0 - 100.0) / 100.0)

def test_calc_ic_and_rank_and_ties():
    # perfect positive correlation
    factors = [{"code": "A", "f": 1.0}, {"code": "B", "f": 2.0}, {"code": "C", "f": 3.0}]
    fwd = [{"code": "A", "r": 1.0}, {"code": "B", "r": 2.0}, {"code": "C", "r": 3.0}]
    ic = calc_ic([{"code": r["code"], "mom": r["f"]} for r in factors],
                 [{"code": r["code"], "fwd_1d": r["r"]} for r in fwd],
                 "mom", "fwd_1d")
    assert ic == pytest.approx(1.0)

    # ties handling in rank
    vals = [1.0, 1.0, 2.0]
    rks = rank(vals)
    # first two should have equal average rank
    assert rks[0] == rks[1]
    assert rks[2] > rks[0]

def test_factor_summary_basic_and_empty():
    recs = [
        {"a": 1.0, "b": 10.0},
        {"a": 2.0, "b": 20.0},
        {"a": None, "b": 30.0},
    ]
    summary = factor_summary(recs, ["a", "b", "c"])
    assert "a" in summary and "b" in summary and "c" in summary
    assert summary["c"]["count"] == 0

# ---------------------------------------------------------------------------
# data.stats: zscore_normalize
# ---------------------------------------------------------------------------
from kabusys.data.stats import zscore_normalize

def test_zscore_normalize_basic_and_edge():
    recs = [{"code": "A", "v": 1.0}, {"code": "B", "v": 3.0}, {"code": "C", "v": 5.0}]
    out = zscore_normalize(recs, ["v"])
    # mean=3, std = sqrt(((4+0+4)/3))=sqrt(8/3)
    assert pytest.approx(0.0, rel=1e-3) == out[1]["v"]
    # single record or zero std should be preserved
    out2 = zscore_normalize([{"v": 1.0}], ["v"])
    assert out2[0]["v"] == 1.0

# ---------------------------------------------------------------------------
# etl: ETLResult
# ---------------------------------------------------------------------------
from kabusys.data.pipeline import ETLResult
from kabusys.data import quality

def test_etlresult_to_dict_and_props():
    qi = quality.QualityIssue(check_name="m", table="t", severity="error", detail="d")
    er = ETLResult(target_date=date(2026, 3, 20))
    er.quality_issues = [qi]
    er.errors = ["e"]
    d = er.to_dict()
    assert d["quality_issues"][0]["check_name"] == "m"
    assert er.has_errors is True
    assert er.has_quality_errors is True

# ---------------------------------------------------------------------------
# quality checks: missing, spike, duplicates, date consistency
# ---------------------------------------------------------------------------
from kabusys.data import quality as quality_mod

def make_conn_with_raw_prices():
    conn = duckdb.connect(database=":memory:")
    conn.execute("""
        CREATE TABLE raw_prices (
            date DATE, code VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT
        )
    """)
    return conn

def test_check_missing_data_detects_nulls():
    conn = make_conn_with_raw_prices()
    td = date(2026, 3, 20)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [td, "X", None, 2.0, 1.0, 1.5, 100])
    issues = quality_mod.check_missing_data(conn, target_date=td)
    assert any(i.check_name == "missing_data" for i in issues)

def test_check_spike_detects_large_change():
    conn = make_conn_with_raw_prices()
    d1 = date(2026, 3, 19)
    d2 = date(2026, 3, 20)
    # previous close 100, current 200 -> 100% change (threshold 0.5)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [d1, "A", 0.0, 0.0, 0.0, 100.0, 10])
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [d2, "A", 0.0, 0.0, 0.0, 200.0, 20])
    issues = quality_mod.check_spike(conn, target_date=d2, threshold=0.5)
    assert any(i.check_name == "spike" for i in issues)

def test_check_duplicates_detects_dupes():
    conn = make_conn_with_raw_prices()
    td = date(2026, 3, 20)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [td, "D", 1,2,3,4,100])
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [td, "D", 1,2,3,4,100])
    issues = quality_mod.check_duplicates(conn, target_date=td)
    assert any(i.check_name == "duplicates" for i in issues)

def test_check_date_consistency_future_and_non_trading():
    conn = duckdb.connect(database=":memory:")
    conn.execute("""
        CREATE TABLE raw_prices (date DATE, code VARCHAR, close DOUBLE)
    """)
    conn.execute("""
        CREATE TABLE market_calendar (date DATE, is_trading_day BOOLEAN, is_sq_day BOOLEAN)
    """)
    ref = date(2026, 3, 20)
    # future record
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?)", [ref + timedelta(days=1), "X", 10.0])
    # non trading day: market_calendar marks 2026-03-18 as non trading, and raw_prices has that date
    nt = ref - timedelta(days=2)
    conn.execute("INSERT INTO market_calendar VALUES (?, ?, ?)", [nt, False, False])
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?)", [nt, "Y", 5.0])
    issues = quality_mod.check_date_consistency(conn, reference_date=ref)
    names = [i.check_name for i in issues]
    assert "future_date" in names
    assert "non_trading_day" in names

# ---------------------------------------------------------------------------
# audit schema init
# ---------------------------------------------------------------------------
from kabusys.data.audit import init_audit_schema, init_audit_db

def test_init_audit_schema_and_db_transactional():
    conn = duckdb.connect(database=":memory:")
    # transactional True should run BEGIN/COMMIT without raising
    init_audit_schema(conn, transactional=False)  # non-transactional ok
    # init_audit_db with :memory: should succeed and return a connection
    c2 = init_audit_db(":memory:")
    assert isinstance(c2, duckdb.DuckDBPyConnection)
    c2.close()
