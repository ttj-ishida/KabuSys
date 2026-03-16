
import os
from datetime import date, datetime, timezone
from unittest import mock

import duckdb
import pytest

# import target modules / functions
from kabusys.config import _parse_env_line, _require, settings
from kabusys.jquants import (
    _to_float,
    _to_int,
    fetch_daily_quotes,
    _get_cached_token,
    get_id_token,
    save_daily_quotes,
    save_financial_statements,
    save_market_calendar,
)
from kabusys.data.schema import init_schema, get_connection
from kabusys.quality import (
    QualityIssue,
    check_missing_data,
    check_spike,
    check_duplicates,
    check_date_consistency,
    run_all_checks,
)


# -----------------------
# config._parse_env_line
# -----------------------
def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   ") is None
    assert _parse_env_line("# comment") is None

    assert _parse_env_line("KEY=val") == ("KEY", "val")
    assert _parse_env_line(" export KEY2 =  value2  ") == ("KEY2", "value2")

    # inline comment only if preceded by space/tab
    assert _parse_env_line("K=foo #comment") == ("K", "foo")
    assert _parse_env_line("K=foo#bar") == ("K", "foo#bar")

    # no '='
    assert _parse_env_line("INVALIDLINE") is None


def test_parse_env_line_quoted_and_escapes():
    # double quotes with escaped quote
    parsed = _parse_env_line('Q="a\\\"b c"')
    assert parsed == ("Q", 'a"b c')

    # single quotes with escaped sequences
    parsed2 = _parse_env_line("S='x\\'y\\nz'")
    # parser treats backslash + next char as literal; newline escape becomes 'n' here
    assert parsed2 == ("S", "x'ynz") or parsed2 == ("S", "x'ynz")  # tolerant


# -----------------------
# simple conversion utils
# -----------------------
@pytest.mark.parametrize("inp,exp", [(None, None), ("", None), ("1.23", 1.23), (1, 1.0), ("abc", None)])
def test_to_float(inp, exp):
    assert _to_float(inp) == exp


@pytest.mark.parametrize(
    "inp,exp",
    [
        (None, None),
        ("", None),
        ("2", 2),
        ("2.0", 2),
        ("2.5", None),
        (2.0, 2),
        ("abc", None),
    ],
)
def test_to_int(inp, exp):
    assert _to_int(inp) == exp


# -----------------------
# jquants token cache
# -----------------------
def test_get_cached_token_and_force_refresh(monkeypatch):
    # mock get_id_token to control returned token
    with mock.patch("kabusys.jquants.get_id_token", autospec=True) as mock_get:
        mock_get.side_effect = ["t1", "t2"]
        # first call -> uses cache, calls get_id_token once
        tok1 = _get_cached_token(force_refresh=False)
        assert tok1 == "t1"
        assert mock_get.call_count == 1

        # second call without force_refresh -> should use cache, not call again
        tok2 = _get_cached_token(force_refresh=False)
        assert tok2 == "t1"
        assert mock_get.call_count == 1

        # force_refresh should call get_id_token again
        tok3 = _get_cached_token(force_refresh=True)
        assert tok3 == "t2"
        assert mock_get.call_count == 2


# -----------------------
# fetch_daily_quotes pagination
# -----------------------
def test_fetch_daily_quotes_pagination(monkeypatch):
    # simulate two-page API via mocking _request
    responses = [
        {"daily_quotes": [{"Date": "2021-01-01", "Code": "0001", "Close": "100"}], "pagination_key": "k1"},
        {"daily_quotes": [{"Date": "2021-01-02", "Code": "0001", "Close": "110"}], "pagination_key": None},
    ]

    def fake_request(path, params=None, id_token=None, method="GET", json_body=None, allow_refresh=True):
        # on first call, params should not have pagination_key
        if "pagination_key" not in (params or {}):
            return responses[0]
        else:
            return responses[1]

    monkeypatch.setattr("kabusys.jquants._request", fake_request)

    res = fetch_daily_quotes(id_token="dummy", code="0001")
    assert isinstance(res, list)
    assert len(res) == 2
    dates = [r["Date"] for r in res]
    assert "2021-01-01" in dates and "2021-01-02" in dates


# -----------------------
# Save functions -> use DuckDB in-memory
# -----------------------
@pytest.fixture
def db_conn():
    conn = init_schema(":memory:")
    yield conn
    try:
        conn.close()
    except Exception:
        pass


def test_save_daily_quotes_inserts_and_skips(db_conn):
    # records: one valid, one missing PK
    records = [
        {"Date": "2021-01-01", "Code": "0001", "Open": "10", "High": "11", "Low": "9", "Close": "10.5", "Volume": "1000", "TurnoverValue": "12345"},
        {"Date": None, "Code": "0002", "Open": "1", "High": "1", "Low": "1", "Close": "1", "Volume": "10", "TurnoverValue": "10"},
        {"Date": "2021-01-02", "Code": "", "Open": "1", "High": "1", "Low": "1", "Close": "1", "Volume": "10", "TurnoverValue": "10"},
    ]
    count = save_daily_quotes(db_conn, records)
    assert count == 1
    rows = db_conn.execute("SELECT date, code, open, close, volume FROM raw_prices").fetchall()
    assert len(rows) == 1
    assert str(rows[0][1]) == "0001"


def test_save_financials_and_market_calendar(db_conn):
    financials = [
        {"LocalCode": "0001", "DisclosedDate": "2021-03-31", "TypeOfDocument": "Q", "NetSales": "100", "OperatingProfit": "10", "Profit": "8", "EarningsPerShare": "1.23", "ROE": "0.05"},
        {"LocalCode": "", "DisclosedDate": "2021-06-30", "TypeOfDocument": "Q", "NetSales": "200"},  # missing code -> skip
    ]
    fin_count = save_financial_statements(db_conn, financials)
    assert fin_count == 1
    rows_fin = db_conn.execute("SELECT code, report_date, revenue, eps FROM raw_financials").fetchall()
    assert len(rows_fin) == 1
    assert rows_fin[0][0] == "0001"

    cal = [
        {"Date": "2021-12-31", "HolidayDivision": "0", "HolidayName": "Normal"},
        {"Date": None, "HolidayDivision": "1", "HolidayName": "Holiday"},  # missing PK -> skip
        {"Date": "2021-12-30", "HolidayDivision": "3", "HolidayName": "Half"},
    ]
    cal_count = save_market_calendar(db_conn, cal)
    assert cal_count == 2
    rows_cal = db_conn.execute("SELECT date, is_trading_day, is_half_day, is_sq_day, holiday_name FROM market_calendar ORDER BY date").fetchall()
    assert len(rows_cal) == 2
    # check boolean flags: "0" => trading day True, "3" => half-day True
    assert rows_cal[0][1] in (True, 1) and rows_cal[0][3] in (False, 0)
    assert rows_cal[1][2] in (True, 1)


# -----------------------
# Quality checks: missing, spike, duplicates, date consistency
# -----------------------
def test_quality_checks_all(db_conn):
    # prepare raw_prices but first recreate raw_prices without PK to allow duplicates test
    # drop and recreate raw_prices without PRIMARY KEY for duplicate test
    db_conn.execute("DROP TABLE IF EXISTS raw_prices")
    db_conn.execute(
        """
        CREATE TABLE raw_prices (
            date DATE,
            code VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT,
            turnover DOUBLE,
            fetched_at TIMESTAMP
        )
        """
    )

    # Insert rows to trigger:
    # - missing_data: row with open NULL
    # - spike: prev_close 100 -> 200 (change 100%)
    # - duplicates: two identical rows for same date/code
    # - future_date: row with date after reference
    today = date(2021, 1, 2)
    db_conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2021, 1, 1), "A", None, 1, 1, 1, 10],
    )
    # spike: two consecutive days for code B
    db_conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2021, 1, 1), "B", 1, 1, 1, 100.0, 10],
    )
    db_conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2021, 1, 2), "B", 1, 1, 1, 200.0, 10],
    )
    # duplicates
    db_conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2021, 1, 3), "C", 1, 1, 1, 1, 1],
    )
    db_conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2021, 1, 3), "C", 1, 1, 1, 1, 1],
    )
    # future date relative to reference_date (ref = 2021-01-02)
    db_conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2021, 1, 5), "D", 1, 1, 1, 1, 1],
    )

    # market_calendar with non-trading day for 2021-01-04 and add a raw_prices record for that day
    db_conn.execute(
        "CREATE TABLE IF NOT EXISTS market_calendar (date DATE, is_trading_day BOOLEAN, is_half_day BOOLEAN, is_sq_day BOOLEAN, holiday_name VARCHAR)"
    )
    db_conn.execute(
        "INSERT INTO market_calendar (date, is_trading_day, is_half_day, is_sq_day, holiday_name) VALUES (?, ?, ?, ?, ?)",
        [date(2021, 1, 4), False, False, False, "Holiday"],
    )
    db_conn.execute(
        "INSERT INTO raw_prices (date, code, open, high, low, close, volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [date(2021, 1, 4), "E", 1, 1, 1, 1, 1],
    )

    # run checks
    missing = check_missing_data(db_conn)
    assert any(i.check_name == "missing_data" for i in missing)
    spike = check_spike(db_conn, threshold=0.5)
    assert any(i.check_name == "spike" for i in spike)
    duplicates = check_duplicates(db_conn)
    assert any(i.check_name == "duplicates" for i in duplicates)
    date_consistency = check_date_consistency(db_conn, reference_date=today)
    # should contain future_date and non_trading_day
    names = {i.check_name for i in date_consistency}
    assert "future_date" in names
    assert "non_trading_day" in names

    # run_all_checks should aggregate all
    all_issues = run_all_checks(db_conn, target_date=None, reference_date=today, spike_threshold=0.5)
    assert any(i.check_name == "missing_data" for i in all_issues)
    assert any(i.check_name == "duplicates" for i in all_issues)
    assert any(i.check_name == "spike" for i in all_issues)
    assert any(i.check_name == "future_date" for i in all_issues)


# -----------------------
# Settings getters and validation
# -----------------------
def test_settings_env_and_log_level(monkeypatch):
    # env default: development
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    assert settings.env == "development"
    # set valid env
    monkeypatch.setenv("KABUSYS_ENV", "live")
    assert settings.env == "live"
    # invalid env raises
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = settings.env

    # log level default INFO
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert settings.log_level == "INFO"
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert settings.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "BAD")
    with pytest.raises(ValueError):
        _ = settings.log_level


def test_require_raises_and_returns(monkeypatch):
    monkeypatch.delenv("SOME_VAR", raising=False)
    with pytest.raises(ValueError):
        _require("SOME_VAR")
    monkeypatch.setenv("SOME_VAR", "v")
    assert _require("SOME_VAR") == "v"


# -----------------------
# get_id_token uses _request -> mock it
# -----------------------
def test_get_id_token_uses_request(monkeypatch):
    # ensure settings.jquants_refresh_token is set
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "r_token")

    fake_ret = {"idToken": "ID123"}
    with mock.patch("kabusys.jquants._request", autospec=True) as mock_req:
        mock_req.return_value = fake_ret
        tok = get_id_token(None)
        assert tok == "ID123"
        mock_req.assert_called_once()
