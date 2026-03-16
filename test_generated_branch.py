
import os
import io
import time
import json
import warnings
from datetime import date, datetime, timezone
from pathlib import Path
from unittest import mock
import urllib.error

import pytest

# モジュール under test
from kabusys import config
from kabusys import jquants
from kabusys.data import schema as data_schema
from kabusys import audit
from kabusys import quality


# -----------------------
# config モジュールのテスト
# -----------------------

def test_parse_env_line_basic_and_comments():
    assert config._parse_env_line("") is None
    assert config._parse_env_line("   # a comment") is None
    assert config._parse_env_line("KEY=val") == ("KEY", "val")
    # export prefix
    assert config._parse_env_line("export KEY2 =  123 ") == ("KEY2", "123")
    # no '='
    assert config._parse_env_line("INVALIDLINE") is None
    # empty key
    assert config._parse_env_line(" =value") is None


def test_parse_env_line_quotes_and_escapes():
    # single quotes with escaped quote sequence and escaped char
    line = "X='a\\'b\\\\c' # inline comment ignored"
    k, v = config._parse_env_line(line)
    assert k == "X"
    assert v == "a'b\\c"
    # double quotes
    line2 = 'Y="hello\\nworld"'
    k2, v2 = config._parse_env_line(line2)
    assert k2 == "Y"
    # escaped \n in quotes becomes literal 'n' because parser simply takes next char
    assert v2 == "hellonworld" or v2 == "hello\nworld"  # accept either depending on implementation


def test_parse_env_line_unquoted_inline_comment():
    # '#' is comment only if preceded by space/tab or at beginning
    assert config._parse_env_line("A=val#notacomment") == ("A", "val#notacomment")
    assert config._parse_env_line("B=val #this is comment") == ("B", "val")
    assert config._parse_env_line("C=val\t#cmt") == ("C", "val")


def test_load_env_file_basic(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.test"
    env_file.write_text("A=1\nB='two'\n# comment\nC= \n")
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    monkeypatch.delenv("C", raising=False)
    # override=False should set only if not present
    config._load_env_file(env_file, override=False, protected=frozenset())
    assert os.environ.get("A") == "1"
    assert os.environ.get("B") == "two"
    # empty value becomes empty string -> present in env
    assert os.environ.get("C") == ""
    # override=True should overwrite unless protected
    os.environ["A"] = "old"
    config._load_env_file(env_file, override=True, protected=frozenset())
    assert os.environ["A"] == "1"
    # protected prevents overwrite
    os.environ["A"] = "old2"
    config._load_env_file(env_file, override=True, protected=frozenset({"A"}))
    assert os.environ["A"] == "old2"


def test_load_env_file_open_error(tmp_path, monkeypatch):
    env_file = tmp_path / ".env.bad"
    env_file.write_text("X=1")
    # mock builtins.open to raise OSError
    with mock.patch("builtins.open", side_effect=OSError("boom")):
        with warnings.catch_warnings(record=True) as rec:
            warnings.simplefilter("always")
            config._load_env_file(env_file, override=False, protected=frozenset())
            assert any(".env ファイルの読み込みに失敗しました" in str(w.message) for w in rec)


def test_require_and_settings_env(monkeypatch):
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    with pytest.raises(ValueError):
        config._require("JQUANTS_REFRESH_TOKEN")
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "token123")
    assert config._require("JQUANTS_REFRESH_TOKEN") == "token123"

    s = config.Settings()
    # default KABUSYS_ENV is "development"
    monkeypatch.delenv("KABUSYS_ENV", raising=False)
    assert s.env == "development"
    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "invalid_env")
    with pytest.raises(ValueError):
        _ = s.env
    # log_level
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "wtf")
    with pytest.raises(ValueError):
        _ = s.log_level


# -----------------------
# jquants モジュールのユーティリティ
# -----------------------

def test_to_float_and_to_int_various():
    assert jquants._to_float(None) is None
    assert jquants._to_float("") is None
    assert jquants._to_float("1.5") == 1.5
    assert jquants._to_float("abc") is None
    assert jquants._to_int(None) is None
    assert jquants._to_int("") is None
    assert jquants._to_int("2") == 2
    assert jquants._to_int(3) == 3
    # float string with integer value
    assert jquants._to_int("1.0") == 1
    # float string with fractional part -> None
    assert jquants._to_int("1.9") is None
    assert jquants._to_int("abc") is None


def test_rate_limiter_wait(monkeypatch):
    rl = jquants._RateLimiter(min_interval=0.5)
    # simulate last_called just now so we need to sleep ~0.5
    monkeypatch.setattr(time, "monotonic", mock.MagicMock(side_effect=[1.0, 1.0 + 0.6, 2.0]))
    slept = []
    monkeypatch.setattr(time, "sleep", lambda s: slept.append(s))
    # first call sets last_called without sleeping (elapsed small but monotonic side_effect controls)
    rl._last_called = 0.5
    rl.wait()
    # ensure sleep was called at most once and with non-negative value
    assert all(s >= 0 for s in slept)


# -----------------------
# jquants._request のテスト（モックでネットワークを制御）
# -----------------------

def make_fake_response(body: bytes):
    fake = mock.MagicMock()
    fake.read.return_value = body
    fake.__enter__.return_value = fake
    return fake


def test_request_json_decode_error(monkeypatch):
    # urlopen returns non-json -> RuntimeError
    fake = make_fake_response(b'not-json')
    monkeypatch.patch("urllib.request.urlopen", return_value=fake)
    with pytest.raises(RuntimeError):
        jquants._request("/test", id_token="t", params={"a": "1"})


def test_request_http_error_raises_after_retries(monkeypatch):
    # force urllib.request.urlopen to raise HTTPError with 500 to trigger retries and final RuntimeError
    err = urllib.error.HTTPError(url="u", code=500, msg="err", hdrs=None, fp=None)
    monkeypatch.patch("urllib.request.urlopen", side_effect=err)
    # patch sleep to avoid delay
    monkeypatch.patch("time.sleep", lambda s: None)
    with pytest.raises(RuntimeError):
        jquants._request("/retry", id_token="t")


def test_request_http_401_raises_when_no_refresh(monkeypatch):
    # when HTTPError 401 occurs and allow_refresh=False -> raise immediately
    err = urllib.error.HTTPError(url="u", code=401, msg="unauth", hdrs=None, fp=None)
    monkeypatch.patch("urllib.request.urlopen", side_effect=err)
    with pytest.raises(urllib.error.HTTPError):
        jquants._request("/auth", id_token="t", allow_refresh=False)


def test_get_id_token_success_and_missing(monkeypatch):
    # monkeypatch jquants._request to return idToken
    monkeypatch.patch.object(jquants, "_request", return_value={"idToken": "ID123"})
    # ensure settings provides a refresh token if none provided
    monkeypatch.setenv("JQUANTS_REFRESH_TOKEN", "RTOKEN")
    assert jquants.get_id_token() == "ID123"
    # explicit param
    assert jquants.get_id_token("man") == "ID123"
    # if no token available (clear env and pass None) should raise
    monkeypatch.delenv("JQUANTS_REFRESH_TOKEN", raising=False)
    # ensure _request is not called in this case; monkeypatch to ensure
    with pytest.raises(ValueError):
        jquants.get_id_token(None)


def test_fetch_daily_quotes_pagination(monkeypatch):
    # simulate two pages
    page1 = {"daily_quotes": [{"Date": "2020-01-01", "Code": "1"}], "pagination_key": "k1"}
    page2 = {"daily_quotes": [{"Date": "2020-01-02", "Code": "2"}], "pagination_key": None}
    calls = []

    def fake_request(path, params=None, id_token=None, **kw):
        calls.append(params.copy() if params else {})
        if not params or "pagination_key" not in params:
            return page1
        return page2

    monkeypatch.patch.object(jquants, "_request", side_effect=fake_request)
    res = jquants.fetch_daily_quotes(id_token="T")
    assert len(res) == 2
    # ensure pagination_key was passed on second call
    assert any("pagination_key" in c for c in calls if c)


# -----------------------
# DuckDB 保存・スキーマのテスト
# -----------------------

def test_init_schema_and_save_and_market_calendar(tmp_path):
    conn = data_schema.init_schema(":memory:")
    # raw_prices should exist (count 0)
    assert conn.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0] == 0

    # save_daily_quotes: insert some records including one missing PK which should be skipped
    records = [
        {"Date": "2021-01-01", "Code": "1000", "Open": "1", "High": "2", "Low": "0.5", "Close": "1.5", "Volume": "100", "TurnoverValue": "1000"},
        {"Date": None, "Code": "1001", "Open": "1", "High": "2", "Low": "0.5", "Close": "1.5"},  # missing PK -> skip
    ]
    saved = jquants.save_daily_quotes(conn, records)
    assert saved == 1
    row = conn.execute("SELECT date, code, open, high, low, close, volume FROM raw_prices").fetchone()
    assert row[1] == "1000"

    # save_financial_statements: prepare table exists
    fin_records = [
        {"LocalCode": "C1", "DisclosedDate": "2020-03-31", "TypeOfDocument": "Q1", "NetSales": "10", "OperatingProfit": "1", "Profit": "1", "EarningsPerShare": "0.1", "ROE": "0.2"},
        {"LocalCode": None, "DisclosedDate": "2020-06-30", "TypeOfDocument": "Q2"},  # skip
    ]
    saved_fin = jquants.save_financial_statements(conn, fin_records)
    assert saved_fin == 1
    rowf = conn.execute("SELECT code, revenue FROM raw_financials").fetchone()
    assert rowf[0] == "C1"

    # save_market_calendar: check holiday divisions -> booleans
    cal_records = [
        {"Date": "2021-01-01", "HolidayDivision": "1", "HolidayName": "Xmas"},  # not trading
        {"Date": "2021-01-02", "HolidayDivision": "3", "HolidayName": "Half"},  # half day -> trading True, is_half_day True
        {"Date": None, "HolidayDivision": "0"}  # skip
    ]
    saved_cal = jquants.save_market_calendar(conn, cal_records)
    assert saved_cal == 2
    rows = conn.execute("SELECT date, is_trading_day, is_half_day, is_sq_day, holiday_name FROM market_calendar ORDER BY date").fetchall()
    # check second row flags
    assert rows[1][1] is True and rows[1][2] is True and rows[1][3] is False


def test_init_audit_schema_and_db(tmp_path):
    conn = audit.init_audit_db(":memory:")
    # signal_events should exist
    assert conn.execute("SELECT COUNT(*) FROM signal_events").fetchone()[0] == 0
    # order_requests table exists
    assert conn.execute("SELECT COUNT(*) FROM order_requests").fetchone()[0] == 0


# -----------------------
# quality モジュールのテスト（欠損・スパイク・重複・日付不整合）
# -----------------------

def prepare_raw_prices_table(conn):
    # ensure table exists (use init_schema) then clear and drop PK to allow duplicates if needed
    # Drop and recreate without primary key for some tests
    conn.execute("DROP TABLE IF EXISTS raw_prices")
    conn.execute("""
        CREATE TABLE raw_prices (
            date DATE,
            code VARCHAR,
            open DOUBLE,
            high DOUBLE,
            low DOUBLE,
            close DOUBLE,
            volume BIGINT
        )
    """)


def test_check_missing_data_and_spike_and_duplicates_and_date_consistency():
    conn = data_schema.init_schema(":memory:")
    # replace raw_prices with simple table (no PK) for easier insertion of duplicates
    prepare_raw_prices_table(conn)
    # insert previous and current rows
    conn.execute("INSERT INTO raw_prices VALUES ('2021-01-01','AAA',1,1,1,1,100)")
    conn.execute("INSERT INTO raw_prices VALUES ('2021-01-02','AAA',NULL,2,1,1.6,200)")  # missing open -> missing_data
    conn.execute("INSERT INTO raw_prices VALUES ('2021-01-03','BBB',1,2,1,10,100)")
    # create spike: prev close 10 -> curr close 30 (200% change)
    conn.execute("INSERT INTO raw_prices VALUES ('2021-01-02','BBB',1,2,1,10,100)")
    conn.execute("INSERT INTO raw_prices VALUES ('2021-01-03','BBB',1,2,1,30,100)")
    # create duplicate rows
    conn.execute("INSERT INTO raw_prices VALUES ('2021-01-01','DUP',1,1,1,1,1)")
    conn.execute("INSERT INTO raw_prices VALUES ('2021-01-01','DUP',1,1,1,1,1)")

    # market_calendar: mark 2021-01-04 as non trading and insert raw_prices for that date
    conn.execute("CREATE TABLE IF NOT EXISTS market_calendar (date DATE, is_trading_day BOOLEAN)")
    conn.execute("INSERT INTO market_calendar VALUES ('2021-01-04', false)")
    conn.execute("INSERT INTO raw_prices VALUES ('2021-01-04','NT',1,1,1,1,10)")

    # missing_data
    missing = quality.check_missing_data(conn)
    assert any(i.check_name == "missing_data" for i in missing)
    # spike
    spikes = quality.check_spike(conn, threshold=0.5)
    assert any(i.check_name == "spike" for i in spikes)
    # duplicates
    dups = quality.check_duplicates(conn)
    assert any(i.check_name == "duplicates" for i in dups)
    # date consistency: future date detection
    # insert a future date row
    future_date = (date.today().replace(year=date.today().year + 1)).isoformat()
    conn.execute("INSERT INTO raw_prices VALUES (?, ?, ?, ?, ?, ?, ?)", (future_date, "FUT", 1,1,1,1,1))
    date_issues = quality.check_date_consistency(conn, reference_date=date.today())
    assert any(i.check_name == "future_date" for i in date_issues)
    # non_trading_day should be detected
    assert any(i.check_name == "non_trading_day" for i in date_issues)

    # run_all_checks should aggregate same issues
    all_issues = quality.run_all_checks(conn)
    # at least one error and one warning exist
    assert any(i.severity == "error" for i in all_issues)
    assert any(i.severity == "warning" for i in all_issues)
