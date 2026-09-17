from __future__ import annotations

from datetime import date

import duckdb
import pytest

from kabusys.operations.manual_trades import (
    DuplicateManualTradeError,
    ManualTradeInput,
    add_manual_trade,
    delete_manual_trade,
    ensure_manual_trade_schema,
    list_manual_trades,
)


class _Settings:
    def __init__(self, path):
        self.duckdb_path = path


@pytest.fixture
def conn():
    c = duckdb.connect(":memory:")
    ensure_manual_trade_schema(c)
    yield c
    c.close()


def test_add_manual_trade_normalizes_and_persists(conn):
    trade_id = add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 18),
            code="7203",
            side="BUY",
            qty=100,
            price=2850.5,
            fees=110,
            source_signal_id="SIG_1",
            note="morning order",
        ),
    )

    rows = list_manual_trades(conn)

    assert trade_id == "MANUAL_2026-09-18_7203_buy"
    assert len(rows) == 1
    assert rows[0].trade_id == trade_id
    assert rows[0].trade_date == date(2026, 9, 18)
    assert rows[0].code == "7203"
    assert rows[0].side == "buy"
    assert rows[0].qty == 100
    assert rows[0].price == 2850.5
    assert rows[0].fees == 110
    assert rows[0].source_signal_id == "SIG_1"
    assert rows[0].note == "morning order"


def test_add_manual_trade_rejects_duplicate_without_force(conn):
    payload = ManualTradeInput(
        trade_date=date(2026, 9, 18),
        code="7203",
        side="buy",
        qty=100,
        price=2850,
    )
    add_manual_trade(conn, payload)

    with pytest.raises(DuplicateManualTradeError):
        add_manual_trade(conn, payload)


def test_add_manual_trade_force_replaces_existing(conn):
    payload = ManualTradeInput(
        trade_date=date(2026, 9, 18),
        code="7203",
        side="buy",
        qty=100,
        price=2850,
    )
    add_manual_trade(conn, payload)

    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 18),
            code="7203",
            side="buy",
            qty=200,
            price=2860,
            fees=55,
        ),
        force=True,
    )

    rows = list_manual_trades(conn)
    assert len(rows) == 1
    assert rows[0].qty == 200
    assert rows[0].price == 2860
    assert rows[0].fees == 55


def test_add_manual_trade_validates_values(conn):
    with pytest.raises(ValueError, match="side"):
        add_manual_trade(
            conn,
            ManualTradeInput(
                trade_date=date(2026, 9, 18),
                code="7203",
                side="hold",
                qty=100,
                price=2850,
            ),
        )
    with pytest.raises(ValueError, match="qty"):
        add_manual_trade(
            conn,
            ManualTradeInput(
                trade_date=date(2026, 9, 18),
                code="7203",
                side="buy",
                qty=0,
                price=2850,
            ),
        )
    with pytest.raises(ValueError, match="price"):
        add_manual_trade(
            conn,
            ManualTradeInput(
                trade_date=date(2026, 9, 18),
                code="7203",
                side="buy",
                qty=100,
                price=-1,
            ),
        )


def test_delete_manual_trade_returns_count(conn):
    trade_id = add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 18),
            code="7203",
            side="buy",
            qty=100,
            price=2850,
        ),
    )

    assert delete_manual_trade(conn, trade_id) == 1
    assert delete_manual_trade(conn, trade_id) == 0
    assert list_manual_trades(conn) == []


def test_cli_add_and_list_records_trade(tmp_path, monkeypatch, capsys):
    from kabusys import manual_trades as cli

    db_path = tmp_path / "manual.duckdb"
    monkeypatch.setattr(cli, "settings", _Settings(db_path))

    assert (
        cli.main(
            [
                "add",
                "--date",
                "2026-09-18",
                "--code",
                "7203",
                "--side",
                "BUY",
                "--qty",
                "100",
                "--price",
                "2850",
                "--fees",
                "110",
                "--note",
                "morning",
                "--apply",
            ]
        )
        == 0
    )

    assert cli.main(["list", "--date", "2026-09-18"]) == 0
    out = capsys.readouterr().out
    assert "MANUAL_2026-09-18_7203_buy" in out
    assert "7203" in out
    assert "buy" in out
    assert "2850" in out


def test_cli_add_requires_apply_for_persistence(tmp_path, monkeypatch):
    from kabusys import manual_trades as cli

    db_path = tmp_path / "manual.duckdb"
    monkeypatch.setattr(cli, "settings", _Settings(db_path))

    assert (
        cli.main(
            [
                "add",
                "--date",
                "2026-09-18",
                "--code",
                "7203",
                "--side",
                "BUY",
                "--qty",
                "100",
                "--price",
                "2850",
            ]
        )
        == 0
    )

    conn = duckdb.connect(str(db_path))
    try:
        ensure_manual_trade_schema(conn)
        assert list_manual_trades(conn) == []
    finally:
        conn.close()


def test_init_schema_creates_manual_trades_table(tmp_path):
    from kabusys.data.schema import init_schema

    conn = init_schema(tmp_path / "schema.duckdb")
    try:
        conn.execute(
            """
            INSERT INTO manual_trades (trade_id, trade_date, code, side, qty, price)
            VALUES ('MANUAL_2026-09-18_7203_buy', DATE '2026-09-18', '7203', 'buy', 100, 2850)
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM manual_trades").fetchone()[0]
    finally:
        conn.close()

    assert count == 1
