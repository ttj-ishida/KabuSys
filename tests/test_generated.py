
import json
import math
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import duckdb
import pytest

from kabusys.config import _parse_env_line, _load_env_file, _require, Settings
from kabusys.ai.news_nlp import calc_news_window, _validate_and_extract, _score_chunk
from kabusys.ai.regime_detector import _calc_ma200_ratio, _fetch_macro_news, _score_macro
from kabusys.data.stats import zscore_normalize
from kabusys.research.feature_exploration import rank, calc_ic, factor_summary
from kabusys.data import quality


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------
class DummyResp:
    def __init__(self, content: str):
        # mimic resp.choices[0].message.content
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=content))]


# ---------------------------------------------------------------------
# config._parse_env_line / _load_env_file / _require / Settings
# ---------------------------------------------------------------------
def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # comment") is None
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    assert _parse_env_line(" export KEY2 =  123 ") == ("KEY2", "123")
    # inline comment only if preceded by space/tab
    assert _parse_env_line("A=1#no_space") == ("A", "1#no_space")
    assert _parse_env_line("B=1 # with comment") == ("B", "1")
    # quoted with escapes
    assert _parse_env_line(r"Q='a\'b'") == ("Q", "a'b")
    assert _parse_env_line(r'Q2="c\"d"') == ("Q2", 'c"d')
    # invalid lines
    assert _parse_env_line("NO_EQUAL_SIGN") is None
    assert _parse_env_line("=novar") is None


def test_load_env_file_override_and_protected(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    content = "\n".join(
        [
            "A=1",
            "B=2",
            "C='quoted value'",
            "D=with # comment",
        ]
    )
    env_file.write_text(content, encoding="utf-8")

    monkeypatch.delenv("A", raising=False)
    monkeypatch.setenv("B", "orig")
    protected = frozenset(os.environ.keys())
    # override=False should not overwrite existing B
    _load_env_file(env_file, override=False, protected=protected)
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "orig"
    assert os.environ.get("C") == "quoted value"
    # override=True should overwrite B if not protected
    monkeypatch.setenv("B", "orig2")
    # create new env file with B changed
    env_file.write_text("B=NEW\n", encoding="utf-8")
    _load_env_file(env_file, override=True, protected=frozenset())  # no protected
    assert os.environ.get("B") == "NEW"


def test_require_raises_and_returns(monkeypatch):
    monkeypatch.delenv("SOME_KEY", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_KEY")
    monkeypatch.setenv("SOME_KEY", "VALUE")
    assert _require("SOME_KEY") == "VALUE"


def test_settings_properties(monkeypatch, tmp_path):
    s = Settings()
    # default base url when not set
    monkeypatch.delenv("KABU_API_BASE_URL", raising=False)
    assert "kabusapi" in s.kabu_api_base_url
    # paths expanduser
    monkeypatch.setenv("DUCKDB_PATH", "~/mydb.duckdb")
    p = s.duckdb_path
    assert isinstance(p, Path)
    assert "mydb.duckdb" in str(p)
    # env validation
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert s.is_live is True
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert s.log_level == "DEBUG"
    # invalid env value
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env


# ---------------------------------------------------------------------
# news_nlp: calc_news_window, _validate_and_extract, _score_chunk
# ---------------------------------------------------------------------
def test_calc_news_window_fixed_date():
    target = date(2026, 3, 20)
    start, end = calc_news_window(target)
    # According to doc: start = previous day 06:00, end = previous day 23:30
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)


def test_validate_and_extract_happy_path_and_edgecases():
    # valid response
    body = {"results": [{"code": "1234", "score": 0.5}, {"code": 5678, "score": -2.0}, {"code": "9999", "score": "nan"}]}
    resp = DummyResp(json.dumps(body))
    out = _validate_and_extract(resp, {"1234", "5678", "0000"})
    # 1234 -> 0.5, 5678 -> clipped to -1.0
    assert math.isclose(out.get("1234"), 0.5, rel_tol=1e-9)
    assert math.isclose(out.get("5678"), -1.0, rel_tol=1e-9)
    # unknown code 9999 not requested -> absent
    assert "9999" not in out

    # response with extra text around JSON: ensures extraction logic works
    messy = "some preamble\n" + json.dumps(body) + "\ntrailing"
    resp2 = DummyResp(messy)
    out2 = _validate_and_extract(resp2, {"1234", "5678"})
    assert "1234" in out2

    # invalid JSON should return {}
    resp3 = DummyResp("not a json")
    assert _validate_and_extract(resp3, {"1234"}) == {}

    # results key missing -> {}
    resp4 = DummyResp(json.dumps({"no_results": []}))
    assert _validate_and_extract(resp4, {"1234"}) == {}


def test_score_chunk_success_and_error_handling(monkeypatch):
    # prepare article_map and chunk_codes
    article_map = {
        "1001": ["Title1 body1", "Title1 body2"],
        "2002": ["Only one article"],
    }
    chunk_codes = ["1001", "2002"]

    # prepare a valid response returning scores
    body = {"results": [{"code": "1001", "score": 0.2}, {"code": "2002", "score": 1.2}]}
    resp = DummyResp(json.dumps(body))

    # patch _call_openai_api in news_nlp to return our resp
    import kabusys.ai.news_nlp as news_mod

    monkeypatch.setattr(news_mod, "_call_openai_api", lambda client, messages: resp)
    # call _score_chunk
    result = _score_chunk(client=object(), chunk_codes=chunk_codes, article_map=article_map)
    assert "1001" in result and "2002" in result
    # 2002 clipped to 1.0
    assert math.isclose(result["2002"], 1.0, rel_tol=1e-9)
    assert math.isclose(result["1001"], 0.2, rel_tol=1e-9)

    # simulate APIError non-5xx (should return {} and not retry)
    class FakeAPIError(Exception):
        status_code = 400

    def raise_api(client, messages):
        raise FakeAPIError("bad")

    monkeypatch.setattr(news_mod, "_call_openai_api", raise_api)
    res2 = _score_chunk(client=object(), chunk_codes=chunk_codes, article_map=article_map)
    assert res2 == {}


# ---------------------------------------------------------------------
# regime_detector: _calc_ma200_ratio, _fetch_macro_news, _score_macro
# ---------------------------------------------------------------------
def setup_prices_table(conn):
    conn.execute(
        """
        CREATE TABLE prices_daily (
            date DATE,
            code VARCHAR,
            close DOUBLE
        )
        """
    )


def test_calc_ma200_ratio_no_data_logs_and_default(tmp_path):
    conn = duckdb.connect(":memory:")
    setup_prices_table(conn)
    # no rows -> returns 1.0
    r = _calc_ma200_ratio(conn, date(2026, 1, 1))
    assert r == 1.0
    conn.close()


def test_calc_ma200_ratio_insufficient_rows(monkeypatch):
    conn = duckdb.connect(":memory:")
    setup_prices_table(conn)
    # insert fewer than _MA_WINDOW rows (use small number of rows)
    today = date(2026, 1, 10)
    for i in range(50):  # less than 200
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", [today - timedelta(days=i + 1), "1321", 100.0 + i])
    r = _calc_ma200_ratio(conn, today)
    assert r == 1.0
    conn.close()


def test_calc_ma200_ratio_full_window():
    conn = duckdb.connect(":memory:")
    setup_prices_table(conn)
    # insert exactly 200 rows decreasing close so latest is first (we insert ordered by date asc then query uses date < target sorted desc)
    target = date(2026, 8, 1)
    base_close = 100.0
    rows = []
    for i in range(1, 201):
        d = target - timedelta(days=i)
        # create varying closes
        rows.append((d, "1321", base_close + i))
    conn.executemany("INSERT INTO prices_daily VALUES (?, ?, ?)", rows)
    ratio = _calc_ma200_ratio(conn, target)
    # latest close = base_close + 1 (i=1 → most recent date target-1), ma200 = average(base_close+1 .. base_close+200)
    latest = base_close + 1
    ma200 = sum(base_close + i for i in range(1, 201)) / 200.0
    assert math.isclose(ratio, latest / ma200, rel_tol=1e-9)
    conn.close()


def test_fetch_macro_news_and_score_macro(monkeypatch):
    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE raw_news (
            id INTEGER,
            datetime TIMESTAMP,
            title VARCHAR
        )
        """
    )
    # insert some news with macro keywords (use one of the keywords like "金利")
    now = datetime(2026, 3, 1, 12, 0)
    titles = [
        (1, now - timedelta(hours=1), "日銀が金利に言及"),
        (2, now - timedelta(hours=2), "企業決算の話"),
        (3, now - timedelta(hours=3), "為替が動く"),
    ]
    conn.executemany("INSERT INTO raw_news VALUES (?, ?, ?)", titles)

    window_start = now - timedelta(hours=4)
    window_end = now
    fetched = _fetch_macro_news(conn, window_start, window_end)
    # should pick up titles containing macro keywords ("日銀", "為替")
    assert any("日銀" in t for t in fetched)
    assert any("為替" in t for t in fetched)

    # test _score_macro: when titles empty -> 0.0 without calling API
    zero = _score_macro(client=None, titles=[])
    assert zero == 0.0

    # test successful API parse and clipping
    import kabusys.ai.regime_detector as rdmod
    resp = DummyResp(json.dumps({"macro_sentiment": 0.8}))
    monkeypatch.setattr(rdmod, "_call_openai_api", lambda client, messages: resp)
    score = _score_macro(client=object(), titles=["t1"])
    assert math.isclose(score, 0.8, rel_tol=1e-9)

    # test invalid JSON -> 0.0 with warning but not exception
    monkeypatch.setattr(rdmod, "_call_openai_api", lambda client, messages: DummyResp("bad json"))
    score2 = _score_macro(client=object(), titles=["t1"])
    assert score2 == 0.0
    conn.close()


# ---------------------------------------------------------------------
# data.stats.zscore_normalize
# ---------------------------------------------------------------------
def test_zscore_normalize_basic():
    records = [
        {"code": "A", "val": 1.0},
        {"code": "B", "val": 2.0},
        {"code": "C", "val": 3.0},
        {"code": "D", "val": None},
    ]
    out = zscore_normalize(records, ["val"])
    # mean = 2.0, std = sqrt(((1)^2 + 0 + 1)/3) = sqrt(2/3)
    vals = [r["val"] for r in out if r["val"] is not None]
    assert len(vals) == 3
    # check that result mean ~ 0
    mean_after = sum(vals) / len(vals)
    assert abs(mean_after) < 1e-12


# ---------------------------------------------------------------------
# research.feature_exploration: rank, calc_ic, factor_summary
# ---------------------------------------------------------------------
def test_rank_with_ties_and_average():
    vals = [1.0, 2.0, 2.0, 4.0]
    ranks = rank(vals)
    # ranks[1] and ranks[2] should be equal average of positions 2 and 3 => (2+3)/2 = 2.5
    assert math.isclose(ranks[1], 2.5, rel_tol=1e-9)
    assert ranks[1] == ranks[2]
    assert ranks[0] == 1.0
    assert ranks[3] == 4.0


def test_calc_ic_monotonic_reverse():
    # factor increasing, forward decreasing -> Spearman = -1.0
    factor_records = [
        {"code": "a", "mom_1m": 1.0},
        {"code": "b", "mom_1m": 2.0},
        {"code": "c", "mom_1m": 3.0},
    ]
    forward_records = [
        {"code": "a", "fwd_1d": 3.0},
        {"code": "b", "fwd_1d": 2.0},
        {"code": "c", "fwd_1d": 1.0},
    ]
    ic = calc_ic(factor_records, forward_records, "mom_1m", "fwd_1d")
    assert ic is not None
    assert ic < 0
    assert pytest.approx(ic, rel=1e-6) == -1.0


def test_factor_summary_and_empty_columns():
    records = [
        {"code": "a", "f1": 1.0, "f2": None},
        {"code": "b", "f1": 3.0, "f2": 2.0},
        {"code": "c", "f1": 5.0, "f2": 4.0},
    ]
    summary = factor_summary(records, ["f1", "f2", "missing"])
    assert summary["f1"]["count"] == 3
    assert summary["f1"]["min"] == 1.0
    assert summary["missing"]["count"] == 0
    assert summary["f2"]["count"] == 2


# ---------------------------------------------------------------------
# data.quality checks using duckdb in-memory
# ---------------------------------------------------------------------
@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    yield c
    c.close()


def test_check_missing_data(conn):
    conn.execute(
        """
        CREATE TABLE raw_prices (
            date DATE, code VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE
        )
        """
    )
    d = date(2026, 1, 1)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [d, "0001", None, 10.0, 9.0, 9.5, 1000])
    issues = quality.check_missing_data(conn, target_date=d)
    assert len(issues) == 1
    assert issues[0].check_name == "missing_data"
    assert "OHLC" in issues[0].detail


def test_check_spike_and_duplicates(conn):
    conn.execute(
        """
        CREATE TABLE raw_prices (
            date DATE, code VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE
        )
        """
    )
    d1 = date(2026, 1, 1)
    d2 = date(2026, 1, 2)
    # duplicate rows for same date/code
    conn.executemany("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [
        (d1, "X", 1, 2, 1, 1.0, 100),
        (d1, "X", 1, 2, 1, 1.0, 110),
        (d2, "X", 1, 2, 1, 10.0, 200),  # spike vs prev close 1.0 -> 900% > 50%
    ])
    dup = quality.check_duplicates(conn, target_date=d1)
    assert len(dup) == 1 and dup[0].check_name == "duplicates"
    spike = quality.check_spike(conn, target_date=d2, threshold=0.5)
    assert len(spike) == 1 and spike[0].check_name == "spike"


def test_check_date_consistency_future_and_non_trading(conn):
    conn.execute(
        """
        CREATE TABLE raw_prices (date DATE, code VARCHAR, close DOUBLE)
        """
    )
    # insert future date
    future = date.today() + timedelta(days=10)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?)", [future, "Z", 10.0])
    # create market_calendar marking a date as non-trading
    conn.execute("CREATE TABLE market_calendar (date DATE, is_trading_day BOOLEAN, is_sq_day BOOLEAN)")
    bad_day = date(2026, 2, 2)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?)", [bad_day, "Z", 5.0])
    conn.execute("INSERT INTO market_calendar VALUES (?, ?, ?)", [bad_day, False, False])
    issues = quality.check_date_consistency(conn, reference_date=date.today())
    # should contain future_date error and non_trading_day warning
    names = {i.check_name for i in issues}
    assert "future_date" in names
    assert "non_trading_day" in names


def test_run_all_checks_combines(conn):
    # create tables and insert one problematic row to trigger missing_data
    conn.execute(
        """
        CREATE TABLE raw_prices (
            date DATE, code VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE
        )
        """
    )
    d = date(2026, 1, 1)
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", [d, "A", None, 2, 1, 1.5, 10])
    all_issues = quality.run_all_checks(conn, target_date=d, reference_date=d)
    assert any(i.check_name == "missing_data" for i in all_issues)
