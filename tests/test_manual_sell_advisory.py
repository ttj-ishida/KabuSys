"""手動保有への SELL 判定（助言モード）のテスト"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from kabusys.data.schema import init_schema
from kabusys.operations.manual_trades import ManualTradeInput, add_manual_trade
from kabusys.strategy.holdings import HeldPosition
from kabusys.strategy.signal_generator import _generate_sell_signals, generate_signals

TARGET = date(2026, 4, 6)  # 月曜


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


def _weekdays_before(d: date, n: int) -> list[date]:
    result: list[date] = []
    cur = d - timedelta(days=1)
    while len(result) < n:
        if cur.weekday() < 5:
            result.insert(0, cur)
        cur -= timedelta(days=1)
    return result


def _price(conn, d: date, code: str, close: float) -> None:
    conn.execute(
        "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
        "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
        [d, code, close, close + 10, close - 10, close],
    )


def _calendar(conn, days: list[date]) -> None:
    for d in days:
        conn.execute(
            "INSERT OR IGNORE INTO market_calendar (date, is_trading_day, is_half_day) "
            "VALUES (?, TRUE, FALSE)",
            [d],
        )


def _manual(code: str, avg: float, entry: date | None, qty: int = 100) -> HeldPosition:
    return HeldPosition(code, qty, avg, entry, entry, "manual")


def _sell(conn, positions, **kwargs):
    return _generate_sell_signals(
        conn,
        TARGET,
        score_map=kwargs.pop("score_map", {}),
        threshold=0.6,
        positions=positions,
        **kwargs,
    )


def test_stop_loss_for_manual_position(conn):
    _price(conn, TARGET, "M1", 900.0)
    result = _sell(conn, [_manual("M1", 1000.0, TARGET - timedelta(days=1))], score_map={"M1": 1.0})
    assert result == [
        {"code": "M1", "score": 1.0, "reason": "stop_loss", "qty": 100, "source": "manual"}
    ]


def test_trailing_stop_for_manual_position(conn):
    days = _weekdays_before(TARGET, 20)
    for i, d in enumerate(days):
        _price(conn, d, "M2", 1100.0 if i == 15 else 1000.0)
    _price(conn, TARGET, "M2", 1020.0)
    # peak=1100, ATR=(17*20+110+110+30)/20=29.5 → 閾値 1100-2*29.5=1041 > 1020
    result = _sell(conn, [_manual("M2", 1000.0, days[0])], score_map={"M2": 1.0})
    assert [r["reason"] for r in result] == ["trailing_stop"]


def test_time_exit_counts_from_manual_entry_date(conn):
    days = _weekdays_before(TARGET, 5)
    _calendar(conn, days + [TARGET])
    _price(conn, TARGET, "M3", 1000.0)
    result = _sell(
        conn, [_manual("M3", 1000.0, days[0])], score_map={"M3": 1.0}, max_holding_days=5
    )
    assert [r["reason"] for r in result] == ["time_exit"]


def test_score_drop_for_manual_position_after_min_holding(conn):
    days = _weekdays_before(TARGET, 6)
    _calendar(conn, days + [TARGET])
    _price(conn, TARGET, "M4", 1000.0)
    result = _sell(conn, [_manual("M4", 1000.0, days[0])], score_map={"M4": 0.1})
    assert [r["reason"] for r in result] == ["score_drop"]


def test_score_drop_suppressed_within_min_holding(conn):
    days = _weekdays_before(TARGET, 2)
    _calendar(conn, days + [TARGET])
    _price(conn, TARGET, "M5", 1000.0)
    assert _sell(conn, [_manual("M5", 1000.0, days[0])], score_map={"M5": 0.1}) == []


def test_missing_price_skips_manual_position(conn):
    assert _sell(conn, [_manual("M6", 1000.0, TARGET)]) == []


def test_generate_signals_includes_manual_positions_and_reports_out(conn):
    _price(conn, TARGET, "M7", 900.0)
    out: list[dict] = []

    generate_signals(
        conn,
        TARGET,
        manual_positions=[_manual("M7", 1000.0, TARGET - timedelta(days=1))],
        sell_signals_out=out,
    )

    rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'", [TARGET]
    ).fetchall()
    assert rows == [("M7",)]
    assert out[0]["code"] == "M7"
    assert out[0]["reason"] == "stop_loss"
    assert out[0]["source"] == "manual"


def test_generate_signals_ignores_manual_trades_by_default(conn):
    """manual_positions 未指定（バックテスト・フラグ OFF）では manual_trades を読まない。"""
    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=TARGET - timedelta(days=3), code="M8", side="buy", qty=100, price=1000.0
        ),
    )
    _price(conn, TARGET, "M8", 800.0)

    generate_signals(conn, TARGET)

    rows = conn.execute(
        "SELECT code FROM signals WHERE date = ? AND side = 'sell'", [TARGET]
    ).fetchall()
    assert rows == []


def test_generate_signals_merges_auto_and_manual_same_code(conn):
    conn.execute(
        "INSERT INTO positions (date, code, position_size, avg_price) VALUES (?, 'M9', 100, 1000)",
        [TARGET],
    )
    _price(conn, TARGET, "M9", 900.0)
    out: list[dict] = []

    generate_signals(
        conn,
        TARGET,
        manual_positions=[_manual("M9", 1000.0, TARGET - timedelta(days=1), qty=200)],
        sell_signals_out=out,
    )

    assert out[0]["qty"] == 300
    assert out[0]["source"] == "mixed"


def test_run_manual_signal_step_records_candidates_when_enabled(conn):
    from kabusys.operations.manual_trades import list_manual_actions, run_manual_signal_step

    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=TARGET - timedelta(days=3), code="S1", side="buy", qty=100, price=1000.0
        ),
    )
    _price(conn, TARGET, "S1", 900.0)

    n, recorded = run_manual_signal_step(conn, TARGET, enabled=True, generate=generate_signals)

    assert n >= 1
    assert recorded == 1
    [action] = list_manual_actions(conn, target_date=TARGET)
    assert (action.code, action.reason, action.qty) == ("S1", "stop_loss", 100)


def test_run_manual_signal_step_disabled_ignores_manual_trades(conn):
    from kabusys.operations.manual_trades import list_manual_actions, run_manual_signal_step

    add_manual_trade(
        conn,
        ManualTradeInput(
            trade_date=TARGET - timedelta(days=3), code="S2", side="buy", qty=100, price=1000.0
        ),
    )
    _price(conn, TARGET, "S2", 900.0)

    _, recorded = run_manual_signal_step(conn, TARGET, enabled=False, generate=generate_signals)

    assert recorded == 0
    assert list_manual_actions(conn, target_date=TARGET) == []
