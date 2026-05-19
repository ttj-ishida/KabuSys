from __future__ import annotations

import pytest

from kabusys.data.schema import init_schema


@pytest.fixture
def schema_conn(tmp_path):
    db = tmp_path / "test.duckdb"
    conn = init_schema(str(db))
    yield conn
    conn.close()


def test_dividends_table_exists(schema_conn):
    rows = schema_conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='dividends'"
    ).fetchall()
    cols = {r[0] for r in rows}
    assert cols == {
        "code",
        "pub_date",
        "ref_no",
        "ex_date",
        "record_date",
        "pay_date",
        "div_rate",
        "fetched_at",
    }


def test_topix_daily_table_exists(schema_conn):
    rows = schema_conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='topix_daily'"
    ).fetchall()
    cols = {r[0] for r in rows}
    assert cols == {"date", "open", "high", "low", "close", "ma25", "ma75", "ma200"}


def test_bootstrap_load_history_table_exists(schema_conn):
    rows = schema_conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_name='bootstrap_load_history'"
    ).fetchall()
    cols = {r[0] for r in rows}
    assert cols == {
        "file_key",
        "endpoint",
        "file_name",
        "status",
        "row_count",
        "error_msg",
        "loaded_at",
    }


def test_raw_prices_has_adj_factor(schema_conn):
    rows = schema_conn.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='raw_prices' AND column_name='adj_factor'"
    ).fetchall()
    assert len(rows) == 1


def test_bootstrap_load_history_upsert_idempotent(schema_conn):
    schema_conn.execute(
        "INSERT INTO bootstrap_load_history (file_key, endpoint, file_name, status) "
        "VALUES ('k1', '/equities/bars/daily', 'f.csv.gz', 'pending')"
    )
    schema_conn.execute(
        "INSERT INTO bootstrap_load_history (file_key, endpoint, file_name, status) "
        "VALUES ('k1', '/equities/bars/daily', 'f.csv.gz', 'loaded') "
        "ON CONFLICT (file_key) DO UPDATE SET status = EXCLUDED.status"
    )
    row = schema_conn.execute(
        "SELECT status FROM bootstrap_load_history WHERE file_key='k1'"
    ).fetchone()
    assert row[0] == "loaded"
