from __future__ import annotations

from datetime import date

import duckdb
import pytest

from kabusys.operations.manual_trades import (
    DuplicateManualTradeError,
    ManualTradeInput,
    OversellError,
    add_manual_trade,
    calculate_manual_positions,
    delete_manual_trade,
    ensure_manual_trade_schema,
    evaluate_manual_positions,
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


def test_add_manual_trade_rejects_duplicate_by_default(conn):
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


def _p(side="buy", qty=100, price=2850, fees=0.0, d=date(2026, 9, 18)):
    return ManualTradeInput(trade_date=d, code="7203", side=side, qty=qty, price=price, fees=fees)


def test_add_manual_trade_has_no_force_argument(conn):
    with pytest.raises(TypeError):
        add_manual_trade(conn, _p(), force=True)


def test_add_manual_trade_split_fills_get_numbered_ids(conn):
    id1 = add_manual_trade(conn, _p(qty=100, price=1000))
    id2 = add_manual_trade(conn, _p(qty=200, price=1300))
    id3 = add_manual_trade(conn, _p(qty=300, price=1100))

    assert id1 == "MANUAL_2026-09-18_7203_buy"
    assert id2 == "MANUAL_2026-09-18_7203_buy_2"
    assert id3 == "MANUAL_2026-09-18_7203_buy_3"
    pos = calculate_manual_positions(conn, as_of=date(2026, 9, 18))[0]
    assert pos.qty == 600
    assert pos.avg_price == pytest.approx((100 * 1000 + 200 * 1300 + 300 * 1100) / 600)


def test_add_manual_trade_reuses_smallest_free_number(conn):
    add_manual_trade(conn, _p(qty=100))
    id2 = add_manual_trade(conn, _p(qty=200))
    add_manual_trade(conn, _p(qty=300))
    delete_manual_trade(conn, id2)

    assert add_manual_trade(conn, _p(qty=400)) == "MANUAL_2026-09-18_7203_buy_2"


def test_add_manual_trade_identical_content_raises_duplicate(conn):
    add_manual_trade(conn, _p())
    with pytest.raises(DuplicateManualTradeError):
        add_manual_trade(conn, _p())
    assert len(list_manual_trades(conn)) == 1


def test_add_manual_trade_allow_duplicate_registers_second(conn):
    add_manual_trade(conn, _p())
    trade_id = add_manual_trade(conn, _p(), allow_duplicate=True)

    assert trade_id == "MANUAL_2026-09-18_7203_buy_2"
    assert len(list_manual_trades(conn)) == 2


def test_sell_entered_before_buy_on_same_day_is_still_applied(conn):
    d = date(2026, 9, 18)
    add_manual_trade(conn, _p(d=date(2026, 9, 17), qty=200, price=1000))
    add_manual_trade(conn, _p(side="sell", qty=100, price=1200, d=d))
    add_manual_trade(conn, _p(side="buy", qty=100, price=1000, d=d))

    pos = calculate_manual_positions(conn, as_of=d)[0]
    assert pos.qty == 200


def test_sell_same_day_as_buy_entered_first_in_sell_order(conn):
    d = date(2026, 9, 18)
    # SELL を先に入力しても、同日 BUY を含めた保有に対して処理される
    add_manual_trade(conn, _p(side="buy", qty=100, price=1000, d=date(2026, 9, 1)))
    add_manual_trade(conn, _p(side="sell", qty=150, price=1000, d=d), allow_oversell=True)
    add_manual_trade(conn, _p(side="buy", qty=100, price=1000, d=d))

    pos = calculate_manual_positions(conn, as_of=d)[0]
    assert pos.qty == 50


def test_oversell_raises_error(conn):
    add_manual_trade(conn, _p(qty=100))
    with pytest.raises(OversellError):
        add_manual_trade(conn, _p(side="sell", qty=101))
    assert issubclass(OversellError, ValueError)
    assert len(list_manual_trades(conn)) == 1


def test_oversell_counts_same_day_buy(conn):
    add_manual_trade(conn, _p(side="buy", qty=100))
    add_manual_trade(conn, _p(side="sell", qty=100))

    assert calculate_manual_positions(conn, as_of=date(2026, 9, 18)) == []


def test_backfilled_sell_that_clamps_later_sell_is_rejected(conn):
    add_manual_trade(conn, _p(qty=100, d=date(2026, 9, 1)))
    add_manual_trade(conn, _p(side="sell", qty=100, d=date(2026, 9, 20)))

    with pytest.raises(OversellError, match="MANUAL_2026-09-20_7203_sell"):
        add_manual_trade(conn, _p(side="sell", qty=100, d=date(2026, 9, 18)))
    assert len(list_manual_trades(conn)) == 2

    trade_id = add_manual_trade(
        conn, _p(side="sell", qty=100, d=date(2026, 9, 18)), allow_oversell=True
    )
    assert trade_id == "MANUAL_2026-09-18_7203_sell"


def test_oversell_message_mentions_gui_label_and_buy_first(conn):
    with pytest.raises(OversellError) as ei:
        add_manual_trade(conn, _p(side="sell", qty=100))
    assert "保有を超える売却を許可する" in str(ei.value)
    assert "BUY" in str(ei.value)


def test_price_and_fees_rounded_to_four_decimals_for_duplicate_check(conn):
    add_manual_trade(conn, _p(price=2850.12345, fees=1.23456))
    with pytest.raises(DuplicateManualTradeError):
        add_manual_trade(conn, _p(price=2850.12345, fees=1.23456))


def test_oversell_without_any_holding_raises(conn):
    with pytest.raises(OversellError):
        add_manual_trade(conn, _p(side="sell", qty=100))


def test_oversell_ignores_later_trades(conn):
    add_manual_trade(conn, _p(qty=100, d=date(2026, 9, 20)))
    with pytest.raises(OversellError):
        add_manual_trade(conn, _p(side="sell", qty=100, d=date(2026, 9, 18)))


def test_allow_oversell_registers_and_warns_on_positions(conn, caplog):
    add_manual_trade(conn, _p(qty=100))
    add_manual_trade(conn, _p(side="sell", qty=150, price=1000), allow_oversell=True)

    with caplog.at_level("WARNING"):
        positions = calculate_manual_positions(conn, as_of=date(2026, 9, 18))

    assert positions == []
    assert any(
        "MANUAL_2026-09-18_7203_sell" in r.getMessage()
        for r in caplog.records
        if r.levelname == "WARNING"
    )


def test_second_fill_is_reflected_in_portfolio_cash(conn):
    from kabusys.operations.manual_trades import calc_manual_portfolio_value

    add_manual_trade(conn, _p(qty=100, price=1000))
    add_manual_trade(conn, _p(qty=200, price=1300))

    _, cash = calc_manual_portfolio_value(conn, 1_000_000.0, as_of=date(2026, 9, 18))

    assert cash == pytest.approx(1_000_000.0 - 100_000 - 260_000)


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


def test_calculate_manual_positions_aggregates_buys_and_partial_sells(conn):
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 18),
            code="7203",
            side="buy",
            qty=100,
            price=1000,
            fees=100,
        ),
    )
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 19),
            code="7203",
            side="buy",
            qty=100,
            price=1200,
            fees=100,
        ),
    )
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 20),
            code="7203",
            side="sell",
            qty=50,
            price=1300,
            fees=50,
        ),
    )

    positions = calculate_manual_positions(conn, as_of=date(2026, 9, 20))

    assert len(positions) == 1
    assert positions[0].code == "7203"
    assert positions[0].qty == 150
    assert positions[0].avg_price == pytest.approx(1101.0)
    assert positions[0].realized_pnl == pytest.approx(9900.0)
    assert positions[0].last_trade_date == date(2026, 9, 20)


def test_calculate_manual_positions_excludes_closed_positions(conn):
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 18),
            code="7203",
            side="buy",
            qty=100,
            price=1000,
        ),
    )
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 19),
            code="7203",
            side="sell",
            qty=100,
            price=1010,
        ),
    )

    assert calculate_manual_positions(conn, as_of=date(2026, 9, 19)) == []


def test_calculate_manual_positions_supports_read_only_connection(tmp_path):
    from kabusys.data.schema import init_schema

    db_path = tmp_path / "manual.duckdb"
    conn = init_schema(db_path)
    try:
        add_manual_trade(
            conn,
            ManualTradeInput(
                trade_date=date(2026, 9, 18),
                code="7203",
                side="buy",
                qty=100,
                price=2850,
            ),
        )
    finally:
        conn.close()

    ro_conn = duckdb.connect(str(db_path), read_only=True)
    try:
        positions = calculate_manual_positions(ro_conn)
    finally:
        ro_conn.close()

    assert len(positions) == 1
    assert positions[0].code == "7203"


def test_evaluate_manual_positions_uses_latest_close_on_or_before_date(conn):
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 18),
            code="7203",
            side="buy",
            qty=100,
            price=1000,
            fees=100,
        ),
    )
    conn.execute(
        """
        CREATE TABLE prices_daily (
            date DATE, code VARCHAR, open DOUBLE, high DOUBLE, low DOUBLE,
            close DOUBLE, volume BIGINT, turnover DOUBLE
        )
        """
    )
    conn.execute(
        """
        INSERT INTO prices_daily VALUES
          (DATE '2026-09-18', '7203', 1000, 1100, 900, 1050, 1000, 1000000),
          (DATE '2026-09-21', '7203', 1100, 1200, 1000, 1150, 1000, 1100000)
        """
    )

    positions = evaluate_manual_positions(conn, as_of=date(2026, 9, 20))

    assert len(positions) == 1
    position = positions[0]
    assert position.price_date == date(2026, 9, 18)
    assert position.close_price == pytest.approx(1050.0)
    assert position.cost_basis == pytest.approx(100100.0)
    assert position.market_value == pytest.approx(105000.0)
    assert position.unrealized_pnl == pytest.approx(4900.0)
    assert position.unrealized_pnl_pct == pytest.approx(4.8951048951)
    assert position.realized_pnl == pytest.approx(0.0)
    assert position.total_pnl == pytest.approx(4900.0)


def test_evaluate_manual_positions_keeps_position_when_price_is_missing(conn):
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 18),
            code="7203",
            side="buy",
            qty=100,
            price=1000,
        ),
    )

    positions = evaluate_manual_positions(conn, as_of=date(2026, 9, 20))

    assert len(positions) == 1
    assert positions[0].price_date is None
    assert positions[0].close_price is None
    assert positions[0].unrealized_pnl is None
    assert positions[0].total_pnl is None


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


def test_cli_positions_prints_open_manual_positions(tmp_path, monkeypatch, capsys):
    from kabusys import manual_trades as cli

    db_path = tmp_path / "manual.duckdb"
    monkeypatch.setattr(cli, "settings", _Settings(db_path))
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
            "--apply",
        ]
    )

    assert cli.main(["positions", "--date", "2026-09-18"]) == 0
    out = capsys.readouterr().out
    assert "7203" in out
    assert "100" in out
    assert "2850" in out


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


def _buy(conn, d, code="7203", qty=100, price=1000.0):
    add_manual_trade(
        conn, ManualTradeInput(trade_date=d, code=code, side="buy", qty=qty, price=price)
    )


def _sell(conn, d, code="7203", qty=100, price=1000.0):
    add_manual_trade(
        conn, ManualTradeInput(trade_date=d, code=code, side="sell", qty=qty, price=price)
    )


def test_manual_positions_track_entry_dates(conn):
    _buy(conn, date(2026, 9, 1))
    _buy(conn, date(2026, 9, 3))

    pos = calculate_manual_positions(conn, as_of=date(2026, 9, 10))[0]

    assert pos.first_entry_date == date(2026, 9, 1)
    assert pos.latest_entry_date == date(2026, 9, 3)


def test_manual_positions_reset_entry_after_full_exit(conn):
    _buy(conn, date(2026, 9, 1))
    _sell(conn, date(2026, 9, 2))
    _buy(conn, date(2026, 9, 7))

    pos = calculate_manual_positions(conn, as_of=date(2026, 9, 10))[0]

    assert pos.qty == 100
    assert pos.first_entry_date == date(2026, 9, 7)
    assert pos.latest_entry_date == date(2026, 9, 7)


def test_fully_sold_manual_position_is_not_held(conn):
    from kabusys.operations.manual_trades import load_manual_held_positions

    _buy(conn, date(2026, 9, 1))
    _sell(conn, date(2026, 9, 2))

    assert load_manual_held_positions(conn, date(2026, 9, 10)) == []


def test_load_manual_held_positions_returns_held_positions(conn):
    from kabusys.operations.manual_trades import load_manual_held_positions
    from kabusys.strategy.holdings import HeldPosition

    _buy(conn, date(2026, 9, 1), price=1000.0)
    _buy(conn, date(2026, 9, 3), price=1200.0)
    _buy(conn, date(2026, 9, 20), price=1500.0)  # target_date より後 → 含めない

    result = load_manual_held_positions(conn, date(2026, 9, 10))

    assert result == [
        HeldPosition(
            code="7203",
            qty=200,
            avg_price=1100.0,
            first_entry_date=date(2026, 9, 1),
            latest_entry_date=date(2026, 9, 3),
            source="manual",
        )
    ]


def test_manual_position_qty_map(conn):
    from kabusys.operations.manual_trades import manual_position_qty_map

    _buy(conn, date(2026, 9, 1), code="7203", qty=200)
    _buy(conn, date(2026, 9, 1), code="6758", qty=100)
    _sell(conn, date(2026, 9, 2), code="6758", qty=100)

    assert manual_position_qty_map(conn, as_of=date(2026, 9, 10)) == {"7203": 200}


def _prices_table(conn):
    conn.execute(
        "CREATE TABLE IF NOT EXISTS prices_daily (date DATE, code VARCHAR, open DOUBLE, "
        "high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)"
    )


def test_calc_manual_portfolio_value(conn):
    from kabusys.operations.manual_trades import calc_manual_portfolio_value

    _prices_table(conn)
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 1), code="7203", side="buy", qty=200, price=1000.0, fees=100.0
        ),
    )
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 2), code="7203", side="sell", qty=100, price=1100.0, fees=50.0
        ),
    )
    conn.execute("INSERT INTO prices_daily VALUES ('2026-09-02', '7203', 0, 0, 0, 1200, 0)")

    pv, cash = calc_manual_portfolio_value(conn, 1_000_000.0, as_of=date(2026, 9, 2))

    # 現金 = 1,000,000 - (200,000 + 100) + (110,000 - 50) = 909,850
    assert cash == pytest.approx(909_850.0)
    # 総資産 = 現金 + 100株 × 1200
    assert pv == pytest.approx(1_029_850.0)


def test_calc_manual_portfolio_value_missing_price_counts_zero(conn):
    from kabusys.operations.manual_trades import calc_manual_portfolio_value

    _prices_table(conn)
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=date(2026, 9, 1), code="7203", side="buy", qty=100, price=1000.0
        ),
    )

    pv, cash = calc_manual_portfolio_value(conn, 500_000.0, as_of=date(2026, 9, 2))

    assert cash == pytest.approx(400_000.0)
    assert pv == pytest.approx(400_000.0)


def test_calc_manual_portfolio_value_no_trades(conn):
    from kabusys.operations.manual_trades import calc_manual_portfolio_value

    assert calc_manual_portfolio_value(conn, 500_000.0, as_of=date(2026, 9, 2)) == (
        500_000.0,
        500_000.0,
    )


def test_merge_current_positions_adds_manual_qty_for_candidates():
    from kabusys.operations.manual_trades import merge_current_positions

    result = merge_current_positions(
        {"7203": 100}, {"7203": 200, "6758": 100, "9984": 100}, ["7203", "6758"]
    )
    assert result == {"7203": 300, "6758": 100}


def _cli_add(cli, *extra, side="BUY", qty="100", price="2850"):
    return cli.main(
        ["add", "--date", "2026-09-18", "--code", "7203", "--side", side, "--qty", qty]
        + ["--price", price, "--apply", *extra]
    )


def test_cli_allow_duplicate_and_deprecated_force(tmp_path, monkeypatch, capsys):
    from kabusys import manual_trades as cli

    monkeypatch.setattr(cli, "settings", _Settings(tmp_path / "m.duckdb"))
    assert _cli_add(cli) == 0
    assert _cli_add(cli) == 1  # 同一内容は拒否
    assert _cli_add(cli, "--allow-duplicate") == 0
    assert _cli_add(cli, "--force") == 0  # 非推奨だが allow-duplicate と同義
    assert cli.main(["list"]) == 0
    out = capsys.readouterr().out
    assert "MANUAL_2026-09-18_7203_buy_2" in out
    assert "MANUAL_2026-09-18_7203_buy_3" in out
    assert "MANUAL_2026-09-18_7203_buy |" in out  # 1 件目は消えない


def test_cli_allow_oversell(tmp_path, monkeypatch, capsys):
    from kabusys import manual_trades as cli

    monkeypatch.setattr(cli, "settings", _Settings(tmp_path / "m.duckdb"))
    assert _cli_add(cli, side="SELL") == 1
    assert "ERROR" in capsys.readouterr().out
    assert _cli_add(cli, "--allow-oversell", side="SELL") == 0
