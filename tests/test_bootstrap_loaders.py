from __future__ import annotations

import csv
import gzip
import io
from pathlib import Path

import duckdb
import pytest

from kabusys.data.bootstrap.loaders import (
    load_calendar,
    load_financials,
    load_master,
    load_prices,
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
    load_prices(conn, path)  # 2回目: 重複挿入なし
    assert conn.execute("SELECT COUNT(*) FROM raw_prices").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM prices_daily").fetchone()[0] == 1


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
    row = conn.execute("SELECT name, market, sector FROM stocks WHERE code='7203'").fetchone()
    assert row == ("トヨタ自動車", "Prime", "輸送用機器")


# ---------------------------------------------------------------------------
# load_financials
# ---------------------------------------------------------------------------


def test_load_financials_inserts_raw_and_processed(conn, tmp_path):
    # J-Quants fins_summary CSV に ROE 列は存在しない。ROE は NP/Eq から計算する。
    rows = [
        {
            "Code": "7203",
            "DiscDate": "2024-01-10",
            "CurPerType": "FY",
            "Sales": "10000000",
            "OP": "1000000",
            "NP": "800000",
            "Eq": "4000000",
            "EPS": "120.5",
        }
    ]
    path = _gz(rows, tmp_path, "fins.csv.gz")
    count = load_financials(conn, path)
    assert count == 1
    assert conn.execute("SELECT COUNT(*) FROM raw_financials").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM fundamentals").fetchone()[0] == 1
    roe = conn.execute("SELECT roe FROM fundamentals WHERE code='7203'").fetchone()[0]
    assert roe is not None
    assert float(roe) == pytest.approx(800000 / 4000000)


def test_load_financials_roe_null_when_eq_zero(conn, tmp_path):
    rows = [
        {
            "Code": "7203",
            "DiscDate": "2024-01-10",
            "CurPerType": "FY",
            "Sales": "1",
            "OP": "1",
            "NP": "100000",
            "Eq": "0",
            "EPS": "1",
        }
    ]
    path = _gz(rows, tmp_path, "fins_eq0.csv.gz")
    load_financials(conn, path)
    roe = conn.execute("SELECT roe FROM fundamentals WHERE code='7203'").fetchone()[0]
    assert roe is None


def test_load_financials_roe_null_when_eq_missing(conn, tmp_path):
    rows = [
        {
            "Code": "7203",
            "DiscDate": "2024-01-10",
            "CurPerType": "FY",
            "Sales": "1",
            "OP": "1",
            "NP": "100000",
            "Eq": "",
            "EPS": "1",
        }
    ]
    path = _gz(rows, tmp_path, "fins_eq_empty.csv.gz")
    load_financials(conn, path)
    roe = conn.execute("SELECT roe FROM fundamentals WHERE code='7203'").fetchone()[0]
    assert roe is None


# ---------------------------------------------------------------------------
# load_calendar
# ---------------------------------------------------------------------------


def test_load_calendar_inserts_market_calendar(conn, tmp_path):
    # 旧形式: HalfDiv/SQDiv/HolName を持つフル列構成
    rows = [
        {"Date": "2024-01-04", "HolDiv": "0", "HalfDiv": "0", "SQDiv": "0", "HolName": ""},
        {"Date": "2024-01-08", "HolDiv": "1", "HalfDiv": "0", "SQDiv": "0", "HolName": "成人の日"},
    ]
    path = _gz(rows, tmp_path, "cal.csv.gz")
    count = load_calendar(conn, path)
    assert count == 2
    row = conn.execute(
        "SELECT is_trading_day, holiday_name FROM market_calendar WHERE date='2024-01-08'"
    ).fetchone()
    assert row[0] is False
    assert row[1] == "成人の日"


def test_load_calendar_holdiv_only_new_format(conn, tmp_path):
    # 新形式: Date + HolDiv のみ（J-Quants 実データ形式）
    # HolDiv: 0=休日, 1=通常取引日, 2=半日取引日, 3=振替休日
    rows = [
        {"Date": "2024-01-01", "HolDiv": "0"},
        {"Date": "2024-01-04", "HolDiv": "1"},
        {"Date": "2024-01-05", "HolDiv": "2"},
        {"Date": "2024-01-06", "HolDiv": "3"},
    ]
    path = _gz(rows, tmp_path, "cal_new.csv.gz")
    count = load_calendar(conn, path)
    assert count == 4

    def get(date):
        return conn.execute(
            "SELECT is_trading_day, is_half_day, is_sq_day, holiday_name "
            "FROM market_calendar WHERE date=?",
            [date],
        ).fetchone()

    r = get("2024-01-01")
    assert r[0] is False and r[1] is False and r[2] is False and r[3] is None  # 休日
    r = get("2024-01-04")
    assert r[0] is True and r[1] is False  # 通常取引日
    r = get("2024-01-05")
    assert r[0] is True and r[1] is True  # 半日取引日
    r = get("2024-01-06")
    assert r[0] is False and r[1] is False  # 振替休日


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
    row = conn.execute("SELECT close FROM topix_daily WHERE date='2024-01-04'").fetchone()
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
