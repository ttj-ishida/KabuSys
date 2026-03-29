
import json
import math
from datetime import date, datetime, timedelta
from pathlib import Path
from unittest import mock

import duckdb
import pytest

from kabusys.config import _parse_env_line, _load_env_file, _require, Settings
from kabusys.ai.news_nlp import calc_news_window, _validate_and_extract, _fetch_articles
from kabusys.data.stats import zscore_normalize
from kabusys.research import rank, calc_ic, factor_summary
from kabusys.data.quality import (
    check_missing_data,
    check_spike,
    check_duplicates,
    check_date_consistency,
    run_all_checks,
    QualityIssue,
)


# ---------------------------
# kabusys.config tests
# ---------------------------

def test_parse_env_line_comments_and_blank():
    assert _parse_env_line("") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("# comment") is None
    assert _parse_env_line("export FOO=bar") == ("FOO", "bar")
    assert _parse_env_line("KEY=val#notacomment") == ("KEY", "val#notacomment")
    # inline comment after space should be removed
    assert _parse_env_line("KEY=val # comment") == ("KEY", "val")
    # quoted with single quote and escaped char
    assert _parse_env_line(r"Q='a\'b'") == ("Q", "a'b")
    # double quotes with escaped quote
    assert _parse_env_line(r'R="x\"y"') == ("R", 'x"y')
    # missing '=' returns None
    assert _parse_env_line("NOEQ") is None


def test_load_env_file_override_and_protected(monkeypatch, tmp_path):
    p = tmp_path / ".envtest"
    p.write_text("A=1\nB=two #comment\nC=keep#hash\n")

    # set an existing OS env that should be considered protected
    monkeypatch.setenv("B", "orig")
    # Prepare protected set as snapshot of os.environ keys (what module does)
    protected = frozenset(dict(**__import__("os").environ).keys())

    # When override=False, existing env B must not change; A and C set
    _load_env_file(p, override=False, protected=protected)
    assert __import__("os").environ.get("A") == "1"
    assert __import__("os").environ.get("C") == "keep#hash"
    assert __import__("os").environ.get("B") == "orig"

    # Now test override=True but protected prevents overwriting B
    p.write_text("B=newb\nD=4\n")
    _load_env_file(p, override=True, protected=protected)
    assert __import__("os").environ.get("B") == "orig"  # protected
    assert __import__("os").environ.get("D") == "4"


def test_require_and_settings_env(monkeypatch):
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    with pytest.raises(ValueError):
        _require("JQUANTS_REFRESH_TOKEN")

    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "token123")
    assert _require("JQUANTS_REFRESH_TOKEN") == "token123"

    s = Settings()
    # KABUSYS_ENV default is 'development'
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert s.env == "development"
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert s.is_live is True
    monkeypatch.setenv("KABUSYS_ENV", "paper_trading")
    assert s.is_paper is True

    # invalid env should raise
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env

    # LOG_LEVEL valid / invalid
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "NO_SUCH")
    with pytest.raises(ValueError):
        _ = s.log_level


# ---------------------------
# kabusys.ai.news_nlp tests
# ---------------------------

def test_calc_news_window_example():
    tgt = date(2026, 3, 20)
    start, end = calc_news_window(tgt)
    # As doc: start = 2026-03-19 06:00, end = 2026-03-19 23:30
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)


class DummyMessage:
    def __init__(self, content):
        self.content = content


class DummyResp:
    def __init__(self, content):
        self.choices = [mock.Mock(message=DummyMessage(content))]


def test_validate_and_extract_success():
    resp = DummyResp(json.dumps({"results": [{"code": "1234", "score": 0.5}]}))
    out = _validate_and_extract(resp, {"1234"})
    assert out == {"1234": 0.5}


def test_validate_and_extract_with_noise_and_nonstandard_types():
    # noise before/after JSON
    content = "some pretext\n" + json.dumps({"results": [{"code": 1234, "score": "0.7"}, {"code": "9999", "score": "NaN"}]}) + "\ntrailer"
    resp = DummyResp(content)
    out = _validate_and_extract(resp, {"1234", "8888"})
    # 1234 present and normalized to "1234" str and parsed to float 0.7
    assert out == {"1234": 0.7}
    # invalid numeric (NaN) and unknown code ignored


def test_validate_and_extract_invalid_json():
    resp = DummyResp("not a json")
    out = _validate_and_extract(resp, {"1"})
    assert out == {}


def test_fetch_articles_grouping_and_trimming():
    conn = duckdb.connect(":memory:")
    # create raw_news and news_symbols as expected by query
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
    # insert one news for code '1000' with title & content, datetime such that ORDER works
    now = datetime(2026, 3, 1, 12, 0)
    for i in range(1, 4):
        conn.execute(
            "INSERT INTO raw_news VALUES (?, ?, ?, ?)",
            [i, now - timedelta(hours=i), f"title{i}", f"content{i}"]
        )
        conn.execute("INSERT INTO news_symbols VALUES (?, ?)", [i, "1000"])
    # Insert another code '2000' with a single article
    conn.execute("INSERT INTO raw_news VALUES (?, ?, ?, ?)", [10, now, "t", "c"])
    conn.execute("INSERT INTO news_symbols VALUES (?, ?)", [10, "2000"])

    window_start = now - timedelta(days=1)
    window_end = now + timedelta(days=1)
    article_map = _fetch_articles(conn, window_start, window_end)
    assert "1000" in article_map and "2000" in article_map
    # each text is "title content"
    assert article_map["1000"][0].startswith("title1 ")
    assert any("content3" in t for t in article_map["1000"])


# ---------------------------
# kabusys.data.stats tests
# ---------------------------

def test_zscore_normalize_basic():
    records = [
        {"code": "A", "val": 1.0},
        {"code": "B", "val": 2.0},
        {"code": "C", "val": 3.0},
    ]
    out = zscore_normalize(records, ["val"])
    # mean = 2, std = sqrt(((1+0+1)/3)) = sqrt(0.666666..) = ~0.816496
    vals = [r["val"] for r in out]
    assert pytest.approx(vals, rel=1e-6) == [ (1-2)/math.sqrt(2/3), 0.0, (3-2)/math.sqrt(2/3) ]

    # None or single-record behavior: no change
    rec2 = [{"code":"X","v": None}, {"code":"Y","v": 1.0}]
    out2 = zscore_normalize(rec2, ["v"])
    assert out2[1]["v"] == 1.0


# ---------------------------
# kabusys.research tests
# ---------------------------

def test_rank_with_ties_and_precision():
    vals = [1.0, 2.0, 2.0, 4.0]
    r = rank(vals)
    # ranks: 1, (2+3)/2=2.5, 2.5, 4
    assert r == [1.0, 2.5, 2.5, 4.0]

def test_calc_ic_basic_perfect_correlation():
    factor = [
        {"code": "A", "mom_1m": 1.0},
        {"code": "B", "mom_1m": 2.0},
        {"code": "C", "mom_1m": 3.0},
    ]
    forward = [
        {"code": "A", "fwd_1d": 10.0},
        {"code": "B", "fwd_1d": 20.0},
        {"code": "C", "fwd_1d": 30.0},
    ]
    ic = calc_ic(factor, forward, "mom_1m", "fwd_1d")
    assert pytest.approx(ic, rel=1e-9) == 1.0

def test_calc_ic_insufficient_records():
    factor = [{"code":"A","mom_1m":1.0}, {"code":"B","mom_1m":None}]
    forward = [{"code":"A","fwd_1d":1.0}, {"code":"B","fwd_1d":2.0}]
    assert calc_ic(factor, forward, "mom_1m", "fwd_1d") is None

def test_factor_summary_basic_stats():
    records = [
        {"code":"A","x":1.0},
        {"code":"B","x":2.0},
        {"code":"C","x":3.0},
        {"code":"D","x":None},
    ]
    summary = factor_summary(records, ["x"])
    s = summary["x"]
    assert s["count"] == 3
    assert pytest.approx(s["mean"]) == 2.0
    assert pytest.approx(s["median"]) == 2.0
    assert pytest.approx(s["min"]) == 1.0
    assert pytest.approx(s["max"]) == 3.0
    assert s["std"] is not None


# ---------------------------
# kabusys.data.quality tests (DuckDB-backed)
# ---------------------------

@pytest.fixture
def price_db():
    conn = duckdb.connect(":memory:")
    conn.execute("""
        CREATE TABLE raw_prices (
            date DATE,
            code VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            turnover DOUBLE
        )
    """)
    conn.execute("""
        CREATE TABLE market_calendar (
            date DATE,
            is_trading_day BOOLEAN,
            is_sq_day BOOLEAN
        )
    """)
    yield conn
    conn.close()

def test_check_missing_data(price_db):
    conn = price_db
    d = date(2026,3,1)
    # insert one row missing high
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [d, "0001", 1.0, None, 0.5, 1.0, 100, 1000.0])
    issues = check_missing_data(conn, target_date=d)
    assert issues and issues[0].check_name == "missing_data"
    assert "OHLC 欠損" in issues[0].detail

def test_check_spike(price_db):
    conn = price_db
    d0 = date(2026,2,28)
    d1 = date(2026,3,1)
    # prev day close 100, today close 200 -> 100% change -> spike (threshold default 0.5)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [d0, "0002", 1.0, 1.0, 1.0, 100.0, 10, 1000.0])
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [d1, "0002", 1.0, 1.0, 1.0, 200.0, 20, 2000.0])
    issues = check_spike(conn, target_date=d1)
    assert any(i.check_name == "spike" for i in issues)

def test_check_duplicates(price_db):
    conn = price_db
    d = date(2026,3,2)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [d, "0003", 1.0, 1.0, 1.0, 1.0, 10, 100.0])
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [d, "0003", 1.0, 1.0, 1.0, 1.0, 20, 200.0])
    issues = check_duplicates(conn, target_date=d)
    assert issues and issues[0].check_name == "duplicates"

def test_check_date_consistency_future_and_non_trading(price_db):
    conn = price_db
    ref = date(2026,3,1)
    future = date(2026,3,10)
    # future record
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [future, "0004", 1,1,1,1, 10, 100.0])
    # non trading day: insert calendar marking 2026-03-03 as non-trading AND raw_prices on that date
    nt = date(2026,3,3)
    conn.execute("INSERT INTO market_calendar VALUES (?, ?, ?)", [nt, False, False])
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [nt, "0005", 1,1,1,1, 5, 50.0])
    issues = check_date_consistency(conn, reference_date=ref)
    names = {i.check_name for i in issues}
    assert "future_date" in names
    assert "non_trading_day" in names

def test_run_all_checks_combines(price_db):
    conn = price_db
    # create a missing_data case
    d = date(2026,4,1)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                 [d, "1111", None, 2, 1, 1.5, 100, 150.0])
    issues = run_all_checks(conn, target_date=d, reference_date=d)
    # should include missing_data
    assert any(i.check_name == "missing_data" for i in issues)
