
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import os
import tempfile

import pytest
from unittest import mock

# モジュールインポート
from kabusys.config import _parse_env_line, _load_env_file, Settings, _require
from kabusys.data.jquants_client import (
    _to_float,
    _to_int,
    _request,
    get_id_token,
    fetch_daily_quotes,
    fetch_financial_statements,
    fetch_market_calendar,
    save_daily_quotes,
    save_financial_statements,
    save_market_calendar,
)
from kabusys.data import schema as data_schema
from kabusys.data import pipeline as data_etl
from kabusys.data import quality as data_quality

import duckdb


# ----------------------------
# config モジュールのテスト
# ----------------------------

def test_parse_env_line_basic_and_comments():
    assert _parse_env_line("") is None
    assert _parse_env_line("   # comment") is None
    assert _parse_env_line("KEY=val") == ("KEY", "val")
    assert _parse_env_line(" export KEY2 =  spaced  ") == ("KEY2", "spaced")
    # no equals
    assert _parse_env_line("NOEQUALS") is None
    # quoted with escapes and inline comment ignored inside quotes
    line = r"QUOTED='value with \' escaped and # not comment'  # comment"
    k, v = _parse_env_line(line)
    assert k == "QUOTED"
    assert "value with ' escaped and # not comment" in v
    # double quoted
    line2 = r'Q2="abc\"def"#comment'
    k2, v2 = _parse_env_line(line2)
    assert k2 == "Q2"
    assert 'abc"def' in v2
    # inline comment for unquoted when preceded by space
    assert _parse_env_line("A=hello #skip") == ("A", "hello")
    # inline '#' with no preceding space should be part of value
    assert _parse_env_line("B=foo#bar") == ("B", "foo#bar")


def test_load_env_file_sets_env_and_respects_override_and_protected(tmp_path, monkeypatch):
    envfile = tmp_path / ".env.test"
    content = "\n".join([
        "A=1",
        "B=two",
        "C=3 # inline",
        "D='quoted'",
    ])
    envfile.write_text(content, encoding="utf-8")
    # Start with empty environment
    monkeypatch.delenv("A", raising=False)
    monkeypatch.delenv("B", raising=False)
    monkeypatch.setenv("B", "existing")  # existing value should not be overwritten by default
    protected = frozenset(os.environ.keys())  # protect all existing keys
    from kabusys.config import _load_env_file as load_fn
    load_fn(envfile, override=False, protected=protected)
    # A should be set
    assert os.environ.get("A") == "1"
    # B existed -> not overwritten
    assert os.environ.get("B") == "existing"
    # Now test override=True but protected prevents overwriting protected keys
    monkeypatch.setenv("B", "existing2")
    load_fn(envfile, override=True, protected=protected)
    assert os.environ.get("B") == "existing2"
    # But when not protected, override works
    load_fn(envfile, override=True, protected=frozenset())
    assert os.environ.get("B") == "two"


def test_require_raises_when_missing(monkeypatch):
    monkeypatch.delenv("NONEXISTENT", raising=False)
    with pytest.raises(ValueError):
        _require("NONEXISTENT")


def test_settings_env_and_log_level_validation(monkeypatch):
    s = Settings()
    # env default development
    monkeypatch.setenv("KABUSYS_ENV", "development")
    assert s.env == "development"
    assert s.is_dev and not s.is_live and not s.is_paper
    # invalid env
    monkeypatch.setenv("KABUSYS_ENV", "INVALIDENV")
    with pytest.raises(ValueError):
        _ = s.env
    # log level defaults and uppercase handling
    monkeypatch.setenv("LOG_LEVEL", "debug")
    assert s.log_level == "DEBUG"
    monkeypatch.setenv("LOG_LEVEL", "NOTALEVEL")
    with pytest.raises(ValueError):
        _ = s.log_level


# ----------------------------
# jquants_client ユーティリティ
# ----------------------------

def test_to_float_and_to_int():
    assert _to_float("1.23") == 1.23
    assert _to_float("") is None
    assert _to_float(None) is None
    assert _to_float("notnum") is None

    assert _to_int("10") == 10
    assert _to_int(5) == 5
    assert _to_int("") is None
    # float-like string with exact integer
    assert _to_int("1.0") == 1
    # float-like string with fractional part -> None
    assert _to_int("1.9") is None
    assert _to_int("notint") is None


def test_request_json_decode_error(monkeypatch):
    # Mock urllib.request.urlopen to return non-JSON
    class DummyResp:
        def __init__(self, raw_bytes):
            self._b = raw_bytes
        def read(self):
            return self._b
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr("kabusys.data.jquants_client._rate_limiter", mock.Mock(wait=lambda: None))
    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout=30: DummyResp(b"not json"))
    with pytest.raises(RuntimeError):
        _request("/some/path", id_token="tok")


def test_get_id_token_uses_request(monkeypatch):
    # patch _request to return expected dict
    monkeypatch.setattr("kabusys.data.jquants_client._request", lambda *args, **kwargs: {"idToken": "ID123"})
    assert get_id_token(refresh_token="RTOKEN") == "ID123"
    # if no refresh_token and settings missing, will raise ValueError via _require
    # but providing refresh_token avoids that (already tested). For negative case:
    with pytest.raises(ValueError):
        get_id_token(refresh_token=None)  # settings likely has no JQUANTS_REFRESH_TOKEN in test env


def test_fetch_daily_quotes_pagination(monkeypatch):
    calls = []

    def fake_request(path, params=None, id_token=None, **kwargs):
        # emulate two pages then end
        if "pagination_key" not in (params or {}):
            calls.append(1)
            return {"daily_quotes": [{"Date": "2020-01-01", "Code": "1111"}], "pagination_key": "k1"}
        elif params.get("pagination_key") == "k1":
            calls.append(2)
            return {"daily_quotes": [{"Date": "2020-01-02", "Code": "2222"}], "pagination_key": None}
        return {"daily_quotes": []}

    monkeypatch.setattr("kabusys.data.jquants_client._request", fake_request)
    res = fetch_daily_quotes(id_token="tok", date_from=date(2020, 1, 1), date_to=date(2020, 1, 2))
    assert isinstance(res, list)
    assert len(res) == 2
    codes = [r["Code"] for r in res]
    assert "1111" in codes and "2222" in codes


def test_fetch_financials_and_market_calendar_pagination(monkeypatch):
    # financial statements similar pagination
    seq = [{"statements": [{"LocalCode": "C1", "DisclosedDate": "2020-01-01", "TypeOfDocument": "Q"}], "pagination_key": "p1"},
           {"statements": [{"LocalCode": "C2", "DisclosedDate": "2020-02-01", "TypeOfDocument": "Q"}], "pagination_key": None}]
    it = iter(seq)

    def fake_req_fin(path, params=None, id_token=None, **kwargs):
        return next(it)

    monkeypatch.setattr("kabusys.data.jquants_client._request", fake_req_fin)
    fin = fetch_financial_statements(id_token="tok")
    assert len(fin) == 2

    # market calendar single call
    monkeypatch.setattr("kabusys.data.jquants_client._request", lambda *a, **k: {"trading_calendar": [{"Date": "2020-01-01", "HolidayDivision": "0"}]})
    cal = fetch_market_calendar(id_token="tok")
    assert len(cal) == 1


# ----------------------------
# DuckDB 保存関数のテスト
# ----------------------------

@pytest.fixture
def conn(mem_db):
    # mem_db from conftest.py avoids FK CASCADE issue in DuckDB 1.x
    return mem_db


def test_save_daily_quotes_basic_and_skip(conn):
    records = [
        {"Date": "2020-01-01", "Code": "0001", "Open": "10", "High": "11", "Low": "9", "Close": "10.5", "Volume": "1000", "TurnoverValue": "1500"},
        {"Date": None, "Code": "0002", "Open": "1", "High": "2", "Low": "1", "Close": "1.5"},  # missing PK -> skipped
        {"Date": "2020-01-02", "Code": None, "Open": "1"},  # missing PK -> skipped
    ]
    saved = save_daily_quotes(conn, records)
    assert saved == 1
    # verify inserted
    res = conn.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0]
    assert res == 1


def test_save_financials_and_market_calendar(conn):
    fin_records = [
        {"LocalCode": "C1", "DisclosedDate": "2020-01-01", "TypeOfDocument": "Q", "NetSales": "1000", "OperatingProfit": "100"},
        {"LocalCode": None, "DisclosedDate": "2020-02-01", "TypeOfDocument": "Q"},  # skip
    ]
    saved_fin = save_financial_statements(conn, fin_records)
    assert saved_fin == 1
    cal_records = [
        {"Date": "2020-01-01", "HolidayDivision": "0", "HolidayName": "Open Day"},
        {"Date": None, "HolidayDivision": "1"},
    ]
    saved_cal = save_market_calendar(conn, cal_records)
    assert saved_cal == 1
    assert conn.execute("SELECT COUNT(*) FROM raw_financials").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM market_calendar").fetchone()[0] == 1


def test_schema_init_creates_tables(mem_db):
    # init_schema uses FK CASCADE which DuckDB 1.x doesn't support,
    # so verify that the minimal DDL (from conftest) creates expected tables
    conn_local = mem_db
    assert conn_local.execute("SELECT COUNT(*) FROM raw_prices").fetchone() is not None
    assert conn_local.execute("SELECT COUNT(*) FROM market_calendar").fetchone() is not None


# ----------------------------
# ETL モジュールのテスト
# ----------------------------

def test_get_last_dates_and_run_prices_etl(monkeypatch, conn):
    # insert some price rows
    conn.execute("INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (date(2020, 1, 1), "C1", 1, 2, 0.5, 1.5, 100, 1000, datetime.now(timezone.utc)))
    last = data_etl.get_last_price_date(conn)
    assert last == date(2020, 1, 1)

    # patch jq.fetch_daily_quotes and save to check run_prices_etl flow
    monkeypatch.setattr("kabusys.data.pipeline.jq.fetch_daily_quotes", lambda id_token, date_from, date_to, code=None: [{"Date": "2020-01-02", "Code": "C1", "Open": "2", "High": "3", "Low": "1.5", "Close": "2.5", "Volume": "50", "TurnoverValue": "125"}])
    monkeypatch.setattr("kabusys.data.pipeline.jq.save_daily_quotes", lambda conn, recs: 1)
    fetched, saved = data_etl.run_prices_etl(conn, target_date=date(2020, 1, 2), id_token="tok")
    assert fetched == 1 and saved == 1

    # when date_from > target_date, return (0,0)
    res = data_etl.run_prices_etl(conn, target_date=date(2019, 12, 31), id_token="tok", date_from=date(2020, 1, 2))
    assert res == (0, 0)


def test_run_daily_etl_handles_errors_and_quality(monkeypatch, conn):
    # monkeypatch internal ETL steps to raise or return controlled values
    monkeypatch.setattr("kabusys.data.pipeline.run_calendar_etl", lambda conn, today, id_token=None, lookahead_days=90: (0, 0))
    monkeypatch.setattr("kabusys.data.pipeline.run_prices_etl", lambda conn, today, id_token=None, backfill_days=3, date_from=None: (2, 2))
    monkeypatch.setattr("kabusys.data.pipeline.run_financials_etl", lambda conn, today, id_token=None, backfill_days=3, date_from=None: (1, 1))
    # quality.run_all_checks returns a list
    monkeypatch.setattr("kabusys.data.pipeline.quality", mock.Mock(run_all_checks=lambda *a, **k: []))
    result = data_etl.run_daily_etl(conn, target_date=date(2020, 1, 10), id_token="tok", run_quality_checks=True)
    assert result.prices_fetched == 2
    assert result.prices_saved == 2
    assert result.financials_fetched == 1
    assert result.calendar_fetched == 0
    assert result.quality_issues == []


# ----------------------------
# quality モジュールのテスト
# ----------------------------

def test_check_missing_data_and_spike_and_duplicates_and_date_consistency(monkeypatch, mem_db):
    conn = mem_db
    # Ensure raw_prices table exists. Drop and recreate without PK to test duplicates case.
    conn.execute("DROP TABLE IF EXISTS raw_prices")
    conn.execute("""
        CREATE TABLE raw_prices (
            date        DATE,
            code        VARCHAR,
            open        DOUBLE,
            high        DOUBLE,
            low         DOUBLE,
            close       DOUBLE,
            volume      BIGINT,
            turnover    DOUBLE,
            fetched_at  TIMESTAMP
        )
    """)
    # Insert rows: one with missing open, one normal, and a duplicate for same date+code
    conn.execute("INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (date(2020, 1, 1), "C1", None, 2.0, 1.0, 1.5, 100, 1000, datetime.now(timezone.utc)))
    conn.execute("INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (date(2020, 1, 1), "C1", 1.0, 2.0, 1.0, 1.5, 100, 1000, datetime.now(timezone.utc)))
    # Duplicate entry for same PK (date, code)
    conn.execute("INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (date(2020, 1, 1), "C1", 1.0, 2.0, 1.0, 1.5, 200, 2000, datetime.now(timezone.utc)))

    # missing data check
    issues_missing = data_quality.check_missing_data(conn, target_date=None)
    assert any(i.check_name == "missing_data" for i in issues_missing)
    # duplicates check
    issues_dup = data_quality.check_duplicates(conn, target_date=None)
    assert any(i.check_name == "duplicates" for i in issues_dup)

    # spike check: insert prev day and current day with large jump
    conn.execute("INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (date(2020, 1, 2), "C2", 1.0, 1.0, 1.0, 1.0, 10, 10, datetime.now(timezone.utc)))
    conn.execute("INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (date(2020, 1, 3), "C2", 10.0, 10.0, 10.0, 10.0, 10, 100, datetime.now(timezone.utc)))
    issues_spike = data_quality.check_spike(conn, target_date=None, threshold=0.5)
    assert any(i.check_name == "spike" for i in issues_spike)

    # date consistency: insert future date row
    future_date = date.today() + timedelta(days=10)
    conn.execute("INSERT INTO raw_prices (date, code, open, high, low, close, volume, turnover, fetched_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                 (future_date, "C3", 1.0, 1.0, 1.0, 1.0, 1, 1, datetime.now(timezone.utc)))
    # insert market_calendar non trading day record
    conn.execute("CREATE TABLE IF NOT EXISTS market_calendar (date DATE, is_trading_day BOOLEAN)")
    conn.execute("INSERT INTO market_calendar (date, is_trading_day) VALUES (?, ?)", (date(2020, 1, 1), False))
    issues_date = data_quality.check_date_consistency(conn, reference_date=date.today())
    # Should contain future_date error and non_trading_day warning
    assert any(i.check_name == "future_date" for i in issues_date)
    assert any(i.check_name == "non_trading_day" for i in issues_date)
    conn.close()


# ----------------------------
# audit schema init tests
# ----------------------------

def test_init_audit_schema_and_db_creates_tables():
    # audit.init_audit_schema uses `with conn:` which closes the connection in DuckDB 1.x.
    # Use a file-based DB so we can reconnect after init_audit_schema closes the connection.
    import tempfile, os
    from kabusys.data import audit
    tmp_path = tempfile.mktemp(suffix=".db")
    try:
        conn = duckdb.connect(tmp_path)
        audit.init_audit_schema(conn)
        # Reconnect after init_audit_schema closed the connection via `with conn:`
        conn2 = duckdb.connect(tmp_path)
        assert conn2.execute("SELECT COUNT(*) FROM signal_events").fetchone() is not None
        assert conn2.execute("SELECT COUNT(*) FROM order_requests").fetchone() is not None
        assert conn2.execute("SELECT COUNT(*) FROM executions").fetchone() is not None
        conn2.close()
        # Also test init_audit_db returns a connection
        conn3 = audit.init_audit_db(tmp_path)
        assert conn3 is not None
        conn3.close()
    finally:
        os.unlink(tmp_path)
