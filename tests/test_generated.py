
import json
import math
from datetime import date, datetime, timedelta
from unittest.mock import Mock, patch

import duckdb
import pytest

# モジュール群をインポート（実際の環境のパッケージ名に合わせて調整してください）
from kabusys.config import _parse_env_line, Settings
from kabusys.ai.regime_detector import _calc_ma200_ratio
from kabusys.ai.news_nlp import (
    calc_news_window,
    _validate_and_extract,
    _score_chunk,
)
from kabusys.data.stats import zscore_normalize
from kabusys.research import rank, calc_ic, factor_summary
from kabusys.data.etl import ETLResult
from kabusys.data.quality import (
    check_missing_data,
    check_date_consistency,
    QualityIssue,
)
import kabusys.ai.news_nlp as news_nlp_module
import kabusys.ai.regime_detector as regime_module


# -----------------------------
# config._parse_env_line
# -----------------------------
@pytest.mark.parametrize(
    "line, expected",
    [
        ("", None),
        ("   # comment", None),
        ("KEY=value", ("KEY", "value")),
        (" export KEY=val", ("KEY", "val")),
        ("KEY = 'a\\'b' # inline comment", ("KEY", "a'b")),
        ('KEY="x\\"y"', ("KEY", 'x"y')),
        ("KEY=unquoted #comment", ("KEY", "unquoted")),
        ("BADLINE", None),
        ("=novalue", None),
    ],
)
def test_parse_env_line_cases(line, expected):
    assert _parse_env_line(line) == expected


# -----------------------------
# Settings env/log level validation
# -----------------------------
def test_settings_env_and_log_level(monkeypatch):
    s = Settings()
    # default env is development -> is_dev True
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert s.env == "development"
    assert s.is_dev is True
    # valid values
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert Settings().env == "live"
    assert Settings().is_live is True
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert Settings().log_level == "DEBUG"
    # invalid values raise
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        Settings().env
    monkeypatch.setenv("LOG_LEVEL", "NOPE")
    with pytest.raises(ValueError):
        Settings().log_level


# -----------------------------
# regime_detector._calc_ma200_ratio
# -----------------------------
def test_calc_ma200_ratio_insufficient_and_ok():
    conn = duckdb.connect(":memory:")
    # create table minimal schema
    conn.execute(
        """
        CREATE TABLE prices_daily (
            code VARCHAR,
            date DATE,
            close DOUBLE
        )
        """
    )
    target = date(2025, 1, 1)

    # 0 rows => returns 1.0
    assert _calc_ma200_ratio(conn, target) == 1.0

    # less than 200 rows => still 1.0
    for i in range(50):
        d = target - timedelta(days=100 + i)
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", ["1321", d, 100.0 + i])
    assert _calc_ma200_ratio(conn, target) == 1.0

    # now insert 200 rows: make first (latest) close 110, others 100 -> ratio = 110 / 100 = 1.1
    conn.execute("DELETE FROM prices_daily")
    base_date = target - timedelta(days=201)
    for i in range(200):
        # ascending dates so the latest (highest date) will be last inserted; query orders DESC
        d = base_date + timedelta(days=i)
        close = 110.0 if i == 199 else 100.0
        conn.execute("INSERT INTO prices_daily VALUES (?, ?, ?)", ["1321", d, close])
    ratio = _calc_ma200_ratio(conn, target)
    assert pytest.approx(ratio, rel=1e-6) == 1.1


# -----------------------------
# news_nlp.calc_news_window
# -----------------------------
def test_calc_news_window():
    td = date(2026, 3, 20)
    start, end = calc_news_window(td)
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)


# -----------------------------
# news_nlp._validate_and_extract
# -----------------------------
def make_resp_with_content(content: str):
    # resp.choices[0].message.content
    m = Mock()
    msg = Mock()
    msg.content = content
    choice = Mock()
    choice.message = msg
    resp = Mock()
    resp.choices = [choice]
    return resp


def test_validate_and_extract_basic_and_extra_text():
    requested_codes = {"1001", "2002"}
    # normal JSON
    resp = make_resp_with_content(json.dumps({"results": [{"code": "1001", "score": 0.5}, {"code": "9999", "score": 1.0}]}))
    out = _validate_and_extract(resp, requested_codes)
    assert out == {"1001": 0.5}

    # JSON with surrounding text (simulate JSON-mode quirks)
    content = "some text\n" + json.dumps({"results": [{"code": 2002, "score": -0.25}]}) + "\ntrailer"
    resp2 = make_resp_with_content(content)
    out2 = _validate_and_extract(resp2, requested_codes)
    assert out2 == {"2002": -0.25}

    # malformed JSON -> empty
    resp3 = make_resp_with_content("no json here")
    assert _validate_and_extract(resp3, {"1"}) == {}


# -----------------------------
# news_nlp._score_chunk (OpenAI call + retry)
# -----------------------------
def test_score_chunk_success_and_retry(monkeypatch):
    # prepare article_map
    article_map = {"9999": ["Title content"]}
    chunk_codes = ["9999"]

    # build a fake successful response content
    resp = make_resp_with_content(json.dumps({"results": [{"code": "9999", "score": 0.75}]}))

    # Patch the module _call_openai_api to simulate a RateLimitError on first call then succeed
    # Use the same RateLimitError class imported by the module
    RateLimitError = news_nlp_module.RateLimitError

    calls = []

    def side_effect(client, messages):
        calls.append(1)
        if len(calls) == 1:
            raise RateLimitError("rate limit")
        return resp

    monkeypatch.setattr(news_nlp_module, "_call_openai_api", side_effect)
    # avoid real sleeping
    monkeypatch.setattr(news_nlp_module.time, "sleep", lambda s: None)

    client = Mock()
    out = _score_chunk(client, chunk_codes, article_map)
    assert out == {"9999": 0.75}


# -----------------------------
# data.stats.zscore_normalize
# -----------------------------
def test_zscore_normalize_basic():
    records = [
        {"code": "A", "f1": 1.0, "f2": None},
        {"code": "B", "f1": 2.0, "f2": 5.0},
        {"code": "C", "f1": 3.0, "f2": float("inf")},
    ]
    res = zscore_normalize(records, ["f1", "f2"])
    # f1 mean = 2.0, std = sqrt(((1-2)^2 + (2-2)^2 + (3-2)^2)/3) = sqrt(2/3)
    mean = 2.0
    std = math.sqrt(((1 - mean) ** 2 + (2 - mean) ** 2 + (3 - mean) ** 2) / 3)
    assert pytest.approx(res[0]["f1"], rel=1e-6) == (1.0 - mean) / std
    # f2: only one valid finite value -> unchanged
    assert res[1]["f2"] == 5.0
    # None preserved
    assert res[0]["f2"] is None


# -----------------------------
# research.rank and calc_ic and factor_summary
# -----------------------------
def test_rank_and_calc_ic_and_summary():
    vals = [1.0, 2.0, 2.0, 4.0]
    ranks = rank(vals)
    # expect ranks: [1.0, 2.5, 2.5, 4.0]
    assert ranks == [1.0, 2.5, 2.5, 4.0]

    # calc_ic: need >=3 valid pairs
    factor_records = [
        {"code": "A", "mom": 0.1},
        {"code": "B", "mom": 0.2},
        {"code": "C", "mom": 0.3},
    ]
    forward_records = [
        {"code": "A", "fwd_1d": 0.01},
        {"code": "B", "fwd_1d": 0.02},
        {"code": "C", "fwd_1d": 0.03},
    ]
    ic = calc_ic(factor_records, forward_records, "mom", "fwd_1d")
    # perfectly monotonic -> positive correlation close to 1
    assert ic is not None and ic > 0.9

    # insufficient valid pairs -> None
    ic2 = calc_ic([{"code": "X", "mom": None}], [{"code": "X", "fwd_1d": None}], "mom", "fwd_1d")
    assert ic2 is None

    # factor_summary
    records = [
        {"a": 1.0, "b": None},
        {"a": 3.0, "b": 5.0},
        {"a": 2.0, "b": 7.0},
    ]
    summary = factor_summary(records, ["a", "b"])
    assert summary["a"]["count"] == 3
    assert summary["a"]["min"] == 1.0
    assert summary["a"]["max"] == 3.0
    assert summary["b"]["count"] == 2


# -----------------------------
# ETLResult dataclass helpers
# -----------------------------
def test_etlresult_properties_and_to_dict():
    issues = [
        QualityIssue("missing", "raw", "error", "detail"),
        QualityIssue("warn", "raw", "warning", "d"),
    ]
    er = ETLResult(target_date=date(2025, 1, 1), quality_issues=issues, errors=["oops"])
    assert er.has_errors is True
    assert er.has_quality_errors is True
    d = er.to_dict()
    assert d["target_date"] == date(2025, 1, 1)
    assert isinstance(d["quality_issues"], list)
    # check quality_issues converted to dicts
    assert all("check_name" in i and "severity" in i for i in d["quality_issues"])


# -----------------------------
# data.quality checks (missing data and date consistency)
# -----------------------------
def test_check_missing_and_future_and_non_trading_day():
    conn = duckdb.connect(":memory:")
    # create raw_prices
    conn.execute(
        """
        CREATE TABLE raw_prices (
            date DATE,
            code VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE
        )
        """
    )
    # insert a row with NULL open
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?)",
                 [date(2025, 1, 2), "1001", None, 10.0, 5.0, 7.0])
    issues = check_missing_data(conn, None)
    assert issues and issues[0].check_name == "missing_data"
    # date consistency: future date
    future_ref = date(2024, 1, 1)
    # insert a future-dated row
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?)",
                 [date(9999, 1, 1), "2002", 1.0, 2.0, 1.0, 1.5])
    issues2 = check_date_consistency(conn, reference_date=future_ref)
    assert any(i.check_name == "future_date" for i in issues2)
    # now add market_calendar and a non-trading day that matches some raw_prices date
    conn.execute(
        "CREATE TABLE market_calendar (date DATE, is_trading_day BOOLEAN, is_sq_day BOOLEAN)"
    )
    conn.execute("INSERT INTO market_calendar VALUES (?, ?, ?)", [date(9999, 1, 1), False, False])
    issues3 = check_date_consistency(conn, reference_date=future_ref)
    assert any(i.check_name == "non_trading_day" for i in issues3)


# -----------------------------
# calendar is_trading_day fallback (weekend)
# -----------------------------
def test_is_trading_day_weekend_fallback():
    from kabusys.data.calendar import is_trading_day
    conn = duckdb.connect(":memory:")
    # no market_calendar => fallback: not weekend => True, weekend => False
    weekday = date(2025, 1, 6)  # Monday
    saturday = date(2025, 1, 4)
    assert is_trading_day(conn, weekday) is True
    assert is_trading_day(conn, saturday) is False
