"""strategy/holdings.py のテスト"""

from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from kabusys.data.schema import init_schema
from kabusys.strategy.holdings import HeldPosition, load_auto_positions, merge_positions


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def test_load_auto_positions_reads_latest_open_positions_with_entry_dates(conn):
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES "
        "('2026-04-01', '1001', 100, 1000), ('2026-04-02', '1001', 200, 1100), "
        "('2026-04-02', '1002', 0, 500)"
    )
    conn.execute(
        "INSERT INTO position_entries (code, entry_date, sell_date) VALUES "
        "('1001', '2026-03-01', NULL), ('1001', '2026-03-10', NULL), "
        "('1001', '2026-02-01', '2026-02-20')"
    )

    result = load_auto_positions(conn, date(2026, 4, 2))

    assert result == [
        HeldPosition(
            code="1001",
            qty=200,
            avg_price=1100.0,
            first_entry_date=date(2026, 3, 1),
            latest_entry_date=date(2026, 3, 10),
            source="auto",
        )
    ]


def test_load_auto_positions_uses_sqlite_entries_when_given(conn):
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) "
        "VALUES ('2026-04-02', '1001', 100, 1000)"
    )
    sq = sqlite3.connect(":memory:")
    sq.execute("CREATE TABLE position_entries (code TEXT, entry_date TEXT, sell_date TEXT)")
    sq.execute("INSERT INTO position_entries VALUES ('1001', '2026-03-05', NULL)")

    result = load_auto_positions(conn, date(2026, 4, 2), sqlite_conn=sq)

    assert result[0].first_entry_date == date(2026, 3, 5)
    assert result[0].latest_entry_date == date(2026, 3, 5)


def test_load_auto_positions_without_entries_has_none_dates(conn):
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) "
        "VALUES ('2026-04-02', '1001', 100, 1000)"
    )
    result = load_auto_positions(conn, date(2026, 4, 2))
    assert result[0].first_entry_date is None
    assert result[0].latest_entry_date is None


def test_merge_positions_combines_same_code():
    auto = [HeldPosition("1001", 100, 1000.0, date(2026, 3, 1), date(2026, 3, 1), "auto")]
    manual = [
        HeldPosition("1001", 300, 1200.0, date(2026, 2, 1), date(2026, 3, 20), "manual"),
        HeldPosition("2002", 100, 500.0, date(2026, 3, 2), date(2026, 3, 2), "manual"),
    ]

    result = merge_positions(auto, manual)

    assert [p.code for p in result] == ["1001", "2002"]
    merged = result[0]
    assert merged.qty == 400
    assert merged.avg_price == pytest.approx(1150.0)
    assert merged.first_entry_date == date(2026, 2, 1)
    assert merged.latest_entry_date == date(2026, 3, 20)
    assert merged.source == "mixed"
    assert result[1].source == "manual"


def test_merge_positions_keeps_none_dates_when_other_side_missing():
    auto = [HeldPosition("1001", 100, 1000.0, None, None, "auto")]
    manual = [HeldPosition("1001", 100, 1000.0, date(2026, 3, 1), date(2026, 3, 1), "manual")]
    merged = merge_positions(auto, manual)[0]
    assert merged.first_entry_date == date(2026, 3, 1)
    assert merged.latest_entry_date == date(2026, 3, 1)
