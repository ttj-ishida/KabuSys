
import json
import math
from datetime import date, datetime, timedelta
from types import SimpleNamespace
from unittest import mock

import duckdb
import pytest

import os

# モジュール下の関数/クラスをインポート
import kabusys.config as config
import kabusys.ai.news_nlp as news_nlp
import kabusys.data.stats as stats
import kabusys.data.calendar as calendar
import kabusys.data.quality as quality


# ---------------------------
# config._parse_env_line
# ---------------------------
@pytest.mark.parametrize(
    "line,expected",
    [
        ("# comment", None),
        ("   ", None),
        ("KEY=val", ("KEY", "val")),
        (" export A =  B  =c  ", ("A", "B  =c")),  # export + spaces + = in value
        ("KEY='quoted\\'inner'", ("KEY", "quoted'inner")),  # single quote with escaped quote
        ('KEY="a\\\"b,c"', ("KEY", 'a"b,c')),  # double quote with escape
        ("KEY=val #notacomment", ("KEY", "val")),  # inline comment because space before #
        ("KEY=val#notacomment", ("KEY", "val#notacomment")),  # no space before #: keep #
        ("=noval", None),  # empty key -> None
        ("KEY_WITH_SPACES =  123  ", ("KEY_WITH_SPACES", "123")),
    ],
)
def test_parse_env_line_various(line, expected):
    res = config._parse_env_line(line)
    assert res == expected


def test_parse_env_line_no_equals():
    assert config._parse_env_line("NOEQUALS") is None


# ---------------------------
# Settings (env/log level validation) and _require
# ---------------------------
def test_require_raises(monkeypatch):
    monkeypatch.delenv("SOME_MISSING_KEY", raising=False)
    with pytest.raises(ValueError):
        config._require("SOME_MISSING_KEY")


def test_settings_env_and_log_level_validation(monkeypatch):
    # Save any existing values to restore later
    monkeypatch.setenv("KABUSYS_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "INFO")

    # Good values should not raise
    s = config.Settings()
    assert s.env == "development"
    assert s.log_level == "INFO"

    # Invalid env -> ValueError
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env

    # Invalid log level -> ValueError
    monkeypatch.setenv("KABUSYS_ENV", "development")
    monkeypatch.setenv("LOG_LEVEL", "nope")
    with pytest.raises(ValueError):
        _ = s.log_level


# ---------------------------
# news_nlp.calc_news_window & _validate_and_extract
# ---------------------------
def test_calc_news_window():
    td = date(2026, 3, 20)
    start, end = news_nlp.calc_news_window(td)
    # start = previous day at 06:00 UTC, end = previous day at 23:30 UTC
    assert isinstance(start, datetime) and isinstance(end, datetime)
    assert start == datetime(2026, 3, 19, 6, 0)
    assert end == datetime(2026, 3, 19, 23, 30)


def make_resp_with_content(content: str):
    """簡易レスポンスオブジェクトを作成"""
    # resp.choices[0].message.content を参照する形に合わせる
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


def test_validate_and_extract_success_and_clipping():
    # content に前後ノイズを含めるケース（JSON extraction fallback）
    content = "noise before {\"results\": [{\"code\": 1234, \"score\": 0.5}, {\"code\": \"5678\", \"score\": -2.0}, {\"code\": \"9999\", \"score\": \"NaN\"}]} extra"
    resp = make_resp_with_content(content)
    res = news_nlp._validate_and_extract(resp, requested_codes={"1234", "5678", "0000"})
    # 1234 -> 0.5, 5678 -> clipped to -1.0 (since -2.0 clipped to -1.0), 9999 ignored (not requested)
    assert res.get("1234") == pytest.approx(0.5)
    assert res.get("5678") == pytest.approx(-1.0)
    assert "9999" not in res
    assert "0000" not in res


def test_validate_and_extract_bad_json():
    # completely invalid JSON -> empty result
    resp = make_resp_with_content("not a json at all")
    res = news_nlp._validate_and_extract(resp, requested_codes={"1"})
    assert res == {}


def test_validate_and_extract_missing_results_key():
    content = '{"other": 1}'
    resp = make_resp_with_content(content)
    res = news_nlp._validate_and_extract(resp, requested_codes={"1"})
    assert res == {}


# ---------------------------
# data.stats.zscore_normalize
# ---------------------------
def test_zscore_normalize_basic():
    records = [
        {"code": "A", "val": 1.0},
        {"code": "B", "val": 2.0},
        {"code": "C", "val": 3.0},
        {"code": "D", "val": None},       # None should be preserved
        {"code": "E", "val": True},       # bool excluded
    ]
    out = stats.zscore_normalize(records, ["val"])
    # Check original list not modified
    assert records[0]["val"] == 1.0
    # Values should be normalized: mean=2.0, std = sqrt(((1+0+1)/3)) = sqrt(2/3)
    normalized_vals = [r for r in out if r["code"] in ("A", "B", "C")]
    vals = [r["val"] for r in normalized_vals]
    # Mean of normalized values should be approximately 0
    assert abs(sum(vals) / len(vals)) < 1e-12
    # None stays None
    assert any(r["code"] == "D" and r["val"] is None for r in out)
    # Bool stays True (not normalized)
    assert any(r["code"] == "E" and r["val"] is True for r in out)


# ---------------------------
# data.calendar fallback behaviors (no market_calendar table)
# ---------------------------
@pytest.fixture
def duck_conn():
    conn = duckdb.connect(database=":memory:")
    yield conn
    conn.close()


def test_is_trading_day_fallback_weekend_and_weekday(duck_conn):
    # no market_calendar table -> fallback on weekday
    # Choose a Monday and Sunday
    monday = date(2026, 3, 16)  # 2026-03-16 is Monday
    sunday = date(2026, 3, 15)
    assert calendar.is_trading_day(duck_conn, monday) is True
    assert calendar.is_trading_day(duck_conn, sunday) is False


def test_next_prev_trading_day_no_table(duck_conn):
    # from Friday -> next trading day should be Monday (skip weekend)
    friday = date(2026, 3, 13)  # Friday
    next_td = calendar.next_trading_day(duck_conn, friday)
    assert next_td.weekday() < 5  # weekday 0..4

    # from Monday -> prev trading day should be previous Friday
    monday = date(2026, 3, 16)
    prev_td = calendar.prev_trading_day(duck_conn, monday)
    assert prev_td.weekday() < 5
    # ensure prev_td is before monday
    assert prev_td < monday


def test_get_trading_days_no_table(duck_conn):
    start = date(2026, 3, 13)  # Friday
    end = date(2026, 3, 17)    # Tuesday
    days = calendar.get_trading_days(duck_conn, start, end)
    # should exclude weekend (14 Sat, 15 Sun)
    assert start in days
    assert date(2026, 3, 14) not in days
    assert date(2026, 3, 15) not in days
    assert date(2026, 3, 16) in days
    assert date(2026, 3, 17) in days


# ---------------------------
# data.quality checks
# ---------------------------
def test_check_missing_data(duck_conn):
    # create raw_prices with a row missing close
    duck_conn.execute(
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
    duck_conn.execute(
        "INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?)",
        [date(2026, 3, 20), "1000", 10.0, None, 9.0, 9.5],
    )
    issues = quality.check_missing_data(duck_conn, target_date=date(2026, 3, 20))
    assert len(issues) == 1
    issue = issues[0]
    assert issue.check_name == "missing_data"
    assert issue.table == "raw_prices"
    assert issue.severity == "error"
    assert "OHLC 欠損" in issue.detail
    assert isinstance(issue.rows, list) and len(issue.rows) >= 1


def test_check_spike(duck_conn):
    # create raw_prices with prev_close and current that triggers spike
    duck_conn.execute(
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
    # insert two consecutive dates for same code
    duck_conn.execute(
        "INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?)",
        [date(2026, 3, 19), "2000", 10.0, 11.0, 9.0, 100.0],
    )
    duck_conn.execute(
        "INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?)",
        [date(2026, 3, 20), "2000", 10.0, 11.0, 9.0, 210.0],  # +110% change
    )
    issues = quality.check_spike(duck_conn, target_date=date(2026, 3, 20), threshold=0.5)
    # Should detect a spike -> one warning
    assert any(i.check_name == "spike" and i.severity == "warning" for i in issues)


def test_check_duplicates(duck_conn):
    duck_conn.execute(
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
    # insert duplicate rows for same (date,code)
    duck_conn.execute(
        "INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?)",
        [date(2026, 3, 20), "3000", 1, 2, 3, 4],
    )
    duck_conn.execute(
        "INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?)",
        [date(2026, 3, 20), "3000", 1, 2, 3, 4],
    )
    issues = quality.check_duplicates(duck_conn, target_date=date(2026, 3, 20))
    assert any(i.check_name == "duplicates" and i.severity == "error" for i in issues)


def test_check_date_consistency_future_and_nontrading(duck_conn):
    # create raw_prices and market_calendar
    duck_conn.execute(
        """
        CREATE TABLE raw_prices (
            date DATE,
            code VARCHAR,
            close DOUBLE
        )
        """
    )
    duck_conn.execute(
        """
        CREATE TABLE market_calendar (
            date DATE,
            is_trading_day BOOLEAN,
            is_sq_day BOOLEAN
        )
        """
    )
    # insert a future date relative to reference_date
    ref = date(2026, 3, 20)
    future = ref + timedelta(days=2)
    duck_conn.execute(
        "INSERT INTO raw_prices VALUES (?, ?, ?)",
        [future, "4000", 10.0],
    )
    # insert non-trading day with raw_prices
    non_trading_day = date(2026, 3, 18)
    # mark that day as non trading in calendar
    duck_conn.execute(
        "INSERT INTO market_calendar VALUES (?, ?, ?)",
        [non_trading_day, False, False],
    )
    # insert raw_prices on that non trading day
    duck_conn.execute(
        "INSERT INTO raw_prices VALUES (?, ?, ?)",
        [non_trading_day, "4000", 9.0],
    )

    issues = quality.check_date_consistency(duck_conn, reference_date=ref)
    # should contain future_date error and non_trading_day warning
    has_future = any(i.check_name == "future_date" and i.severity == "error" for i in issues)
    has_non_trading = any(i.check_name == "non_trading_day" and i.severity == "warning" for i in issues)
    assert has_future and has_non_trading


# ---------------------------
# Additional small tests: quality.run_all_checks aggregates
# ---------------------------
def test_run_all_checks_aggregation(duck_conn):
    # no tables -> all checks return empty list -> run_all_checks returns empty
    issues = quality.run_all_checks(duck_conn)
    assert issues == []
