from __future__ import annotations

import csv
import gzip
import io
from pathlib import Path

import duckdb
import pytest

from kabusys.data.bootstrap.loaders import (
    load_prices,
    load_master,
    load_financials,
    load_calendar,
    load_dividend,
    load_topix,
)

# ---------------------------------------------------------------------------
# テスト用 DB フィクスチャ
# ---------------------------------------------------------------------------


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    c.execute("""
        CREATE TABLE raw_prices (
            date DATE NOT NULL, code VARCHAR NOT NULL,
            open DECIMAL(18,4), high DECIMAL(18,4),
            low DECIMAL(18,4), close DECIMAL(18,4),
            volume BIGINT, turnover DECIMAL(18,2),
            adj_factor DECIMAL(18,6),
            fetched_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            PRIMARY KEY (date, code)
        )
    """)
    c.execute("""
        CREATE TABLE prices_daily (
            date DATE NOT NULL, code VARCHAR NOT NULL,
            open DECIMAL(18,4) NOT NULL, high DECIMAL(18,4) NOT NULL,
            low DECIMAL(18,4) NOT NULL CHECK (low <= high),
            close DECIMAL(18,4) NOT NULL, volume BIGINT NOT NULL,
            turnover DECIMAL(18,2),
            PRIMARY KEY (date, code)
        )
    """)
    c.execute("""
        CREATE TABLE stocks (
            code VARCHAR NOT NULL PRIMARY KEY,
            name VARCHAR, market VARCHAR, sector VARCHAR,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)
    c.execute("""
        CREATE TABLE raw_financials (
            code VARCHAR NOT NULL, report_date DATE NOT NULL,
            period_type VARCHAR NOT NULL,
            revenue DECIMAL(20,4), operating_profit DECIMAL(20,4),
            net_income DECIMAL(20,4), eps DECIMAL(18,4), roe DECIMAL(10,6),
            fetched_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            PRIMARY KEY (code, report_date, period_type)
        )
    """)
    c.execute("""
        CREATE TABLE fundamentals (
            code VARCHAR NOT NULL, report_date DATE NOT NULL,
            period_type VARCHAR NOT NULL,
            revenue DECIMAL(20,4), operating_profit DECIMAL(20,4),
            net_income DECIMAL(20,4), eps DECIMAL(18,4), roe DECIMAL(10,6),
            PRIMARY KEY (code, report_date, period_type)
        )
    """)
    c.execute("""
        CREATE TABLE market_calendar (
            date DATE NOT NULL PRIMARY KEY,
            is_trading_day BOOLEAN NOT NULL,
            is_half_day BOOLEAN NOT NULL DEFAULT false,
            is_sq_day BOOLEAN NOT NULL DEFAULT false,
            holiday_name VARCHAR
        )
    """)
    c.execute("""
        CREATE TABLE dividends (
            code VARCHAR NOT NULL, pub_date DATE NOT NULL,
            ref_no VARCHAR NOT NULL,
            ex_date DATE, record_date DATE, pay_date DATE,
            div_rate DECIMAL(18,4),
            fetched_at TIMESTAMP NOT NULL DEFAULT current_timestamp,
            PRIMARY KEY (code, pub_date, ref_no)
        )
    """)
    c.execute("""
        CREATE TABLE topix_daily (
            date DATE NOT NULL PRIMARY KEY,
            open DECIMAL(18,4) NOT NULL, high DECIMAL(18,4) NOT NULL,
            low DECIMAL(18,4) NOT NULL, close DECIMAL(18,4) NOT NULL
        )
    """)
    yield c
    c.close()


def _gz(rows: list[dict], tmp_path: Path, name: str) -> Path:
    """rows を gzip CSV として tmp_path に保存してパスを返す。"""
    p = tmp_path / name
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    p.write_bytes(gzip.compress(buf.getvalue().encode("utf-8")))
    return p


# ---------------------------------------------------------------------------
# load_prices
# ---------------------------------------------------------------------------


def test_load_prices_inserts_raw_and_processed(conn, tmp_path):
    rows = [
        {
            "Date": "2024-01-10",
            "Code": "7203",
            "O": "2800",
            "H": "2850",
            "L": "2780",
            "C": "2830",
            "Vo": "1000000",
            "Va": "2830000000",
            "AdjFactor": "1.0",
        }
    ]
    path = _gz(rows, tmp_path, "prices.csv.gz")
    count = load_prices(conn, path)
    assert count == 1
    assert conn.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM prices_daily").fetchone()[0] == 1


def test_load_prices_skips_invalid_rows(conn, tmp_path):
    rows = [
        {
            "Date": "2024-01-10",
            "Code": "7203",
            "O": "2800",
            "H": "2850",
            "L": "2780",
            "C": "2830",
            "Vo": "1000000",
            "Va": "",
            "AdjFactor": "1.0",
        },
        {
            "Date": "2024-01-11",
            "Code": "",
            "O": "100",
            "H": "110",
            "L": "90",
            "C": "105",
            "Vo": "500",
            "Va": "",
            "AdjFactor": "1.0",
        },  # code 欠損
    ]
    path = _gz(rows, tmp_path, "prices_skip.csv.gz")
    count = load_prices(conn, path)
    assert count == 1  # code 欠損行はスキップ


def test_load_prices_idempotent(conn, tmp_path):
    rows = [
        {
            "Date": "2024-01-10",
            "Code": "7203",
            "O": "2800",
            "H": "2850",
            "L": "2780",
            "C": "2830",
            "Vo": "1000000",
            "Va": "",
            "AdjFactor": "1.0",
        }
    ]
    path = _gz(rows, tmp_path, "prices_idem.csv.gz")
    load_prices(conn, path)
    count = load_prices(conn, path)
    assert conn.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM prices_daily").fetchone()[0] == 1
    assert count == 1


# ---------------------------------------------------------------------------
# load_master
# ---------------------------------------------------------------------------


def test_load_master_inserts_stocks(conn, tmp_path):
    rows = [
        {
            "Code": "7203",
            "CoName": "トヨタ自動車",
            "MktNm": "Prime",
            "S33Nm": "輸送用機器",
        }
    ]
    path = _gz(rows, tmp_path, "master.csv.gz")
    count = load_master(conn, path)
    assert count == 1
    row = conn.execute(
        "SELECT name, market, sector FROM stocks WHERE code='7203'"
    ).fetchone()
    assert row == ("トヨタ自動車", "Prime", "輸送用機器")


# ---------------------------------------------------------------------------
# load_financials
# ---------------------------------------------------------------------------


def test_load_financials_inserts_raw_and_processed(conn, tmp_path):
    rows = [
        {
            "Code": "7203",
            "DiscDate": "2024-01-10",
            "CurPerType": "FY",
            "Sales": "10000000",
            "OP": "1000000",
            "NP": "800000",
            "EPS": "120.5",
            "ROE": "0.12",
        }
    ]
    path = _gz(rows, tmp_path, "fins.csv.gz")
    count = load_financials(conn, path)
    assert count == 1
    assert conn.execute("SELECT COUNT(*) FROM raw_financials").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM fundamentals").fetchone()[0] == 1


# ---------------------------------------------------------------------------
# load_calendar
# ---------------------------------------------------------------------------


def test_load_calendar_inserts_market_calendar(conn, tmp_path):
    rows = [
        {
            "Date": "2024-01-04",
            "HolDiv": "0",
            "HalfDiv": "0",
            "SQDiv": "0",
            "HolName": "",
        },
        {
            "Date": "2024-01-08",
            "HolDiv": "1",
            "HalfDiv": "0",
            "SQDiv": "0",
            "HolName": "成人の日",
        },
    ]
    path = _gz(rows, tmp_path, "cal.csv.gz")
    count = load_calendar(conn, path)
    assert count == 2
    row = conn.execute(
        "SELECT is_trading_day, holiday_name FROM market_calendar WHERE date='2024-01-08'"
    ).fetchone()
    assert row[0] is False
    assert row[1] == "成人の日"


# ---------------------------------------------------------------------------
# load_dividend
# ---------------------------------------------------------------------------


def test_load_dividend_inserts_dividends(conn, tmp_path):
    rows = [
        {
            "Code": "7203",
            "PubDate": "2024-01-15",
            "RefNo": "001",
            "ExDate": "2024-03-27",
            "RecDate": "2024-03-31",
            "PayDate": "2024-06-05",
            "DivRate": "30.0",
        }
    ]
    path = _gz(rows, tmp_path, "div.csv.gz")
    count = load_dividend(conn, path)
    assert count == 1
    row = conn.execute("SELECT div_rate FROM dividends WHERE code='7203'").fetchone()
    assert float(row[0]) == 30.0


# ---------------------------------------------------------------------------
# load_topix
# ---------------------------------------------------------------------------


def test_load_topix_inserts_topix_daily(conn, tmp_path):
    rows = [
        {
            "Date": "2024-01-04",
            "O": "2500.5",
            "H": "2510.0",
            "L": "2490.0",
            "C": "2505.0",
        }
    ]
    path = _gz(rows, tmp_path, "topix.csv.gz")
    count = load_topix(conn, path)
    assert count == 1
    row = conn.execute(
        "SELECT close FROM topix_daily WHERE date='2024-01-04'"
    ).fetchone()
    assert float(row[0]) == 2505.0


def test_load_topix_skips_low_gt_high(conn, tmp_path):
    rows = [
        {"Date": "2024-01-05", "O": "100.0", "H": "90.0", "L": "110.0", "C": "95.0"},
        {"Date": "2024-01-06", "O": "100.0", "H": "110.0", "L": "90.0", "C": "105.0"},
    ]
    path = _gz(rows, tmp_path, "topix_bad.csv.gz")
    count = load_topix(conn, path)
    assert count == 1
    assert conn.execute("SELECT COUNT(*) FROM topix_daily").fetchone()[0] == 1
