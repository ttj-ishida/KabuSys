"""tests/test_inject_dummy_signal.py — inject_dummy_signal ツールのテスト"""

from __future__ import annotations

from datetime import date

import pytest

from kabusys.data.schema import init_schema
from kabusys.tools.inject_dummy_signal import (
    DuplicateSignalError,
    build_signal_id,
    inject_signal,
    resolve_target_date,
)


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


class TestBuildSignalId:
    def test_has_dummy_prefix(self):
        sid = build_signal_id(date(2026, 5, 1), "7203", "buy")
        assert sid.startswith("DUMMY_")

    def test_contains_date_code_side(self):
        sid = build_signal_id(date(2026, 5, 1), "7203", "buy")
        assert "2026-05-01" in sid
        assert "7203" in sid
        assert "buy" in sid

    def test_deterministic(self):
        a = build_signal_id(date(2026, 5, 1), "7203", "buy")
        b = build_signal_id(date(2026, 5, 1), "7203", "buy")
        assert a == b


class TestResolveTargetDate:
    def test_explicit_date_returned_as_is(self, conn):
        d = date(2026, 5, 7)  # 木曜
        assert resolve_target_date(conn, d) == d

    def test_none_returns_prev_trading_day(self, conn):
        """Issue #413 fix round 1: 既定は prev_trading_day(today)。

        当日の執行エンジン（signal_date=前営業日）がすぐ拾え、21:00 の夜間バッチ
        （当日日付の pending 行を DELETE する）にも消されない。
        """
        today = date(2026, 5, 7)  # 木曜 → 水曜
        assert resolve_target_date(conn, None, today=today) == date(2026, 5, 6)

    def test_none_on_monday_returns_previous_friday(self, conn):
        today = date(2026, 5, 11)  # 月曜 → 金曜
        assert resolve_target_date(conn, None, today=today) == date(2026, 5, 8)


class TestInjectSignal:
    def test_buy_signal_inserted(self, conn):
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy", qty=100)
        rows = conn.execute(
            "SELECT code, side, size, order_type, status FROM signal_queue WHERE code='7203'"
        ).fetchall()
        assert len(rows) == 1
        code, side, size, order_type, status = rows[0]
        assert code == "7203"
        assert side == "buy"
        assert size == 100
        assert order_type == "market"
        assert status == "pending"

    def test_sell_signal_inserted(self, conn):
        inject_signal(conn, target_date=date(2026, 5, 7), code="9984", side="sell", qty=200)
        rows = conn.execute("SELECT side, size FROM signal_queue WHERE code='9984'").fetchall()
        assert rows[0] == ("sell", 200)

    def test_default_qty_is_100(self, conn):
        inject_signal(conn, target_date=date(2026, 5, 7), code="6758", side="buy")
        row = conn.execute("SELECT size FROM signal_queue WHERE code='6758'").fetchone()
        assert row[0] == 100

    def test_signal_id_has_dummy_prefix(self, conn):
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy")
        row = conn.execute("SELECT signal_id FROM signal_queue WHERE code='7203'").fetchone()
        assert row[0].startswith("DUMMY_")

    def test_duplicate_raises_without_force(self, conn):
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy")
        with pytest.raises(DuplicateSignalError):
            inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy")

    def test_duplicate_overwrites_with_force(self, conn):
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy", qty=100)
        inject_signal(
            conn,
            target_date=date(2026, 5, 7),
            code="7203",
            side="buy",
            qty=300,
            force=True,
        )
        rows = conn.execute("SELECT signal_id, size FROM signal_queue WHERE code='7203'").fetchall()
        assert len(rows) == 1
        assert rows[0][1] == 300

    def test_force_uses_fresh_signal_id(self, conn):
        """--force の再注入は新しい signal_id を使う（処理済み記録で読み飛ばされないため）。"""
        first = inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy")
        second = inject_signal(
            conn, target_date=date(2026, 5, 7), code="7203", side="buy", force=True
        )
        third = inject_signal(
            conn, target_date=date(2026, 5, 7), code="7203", side="buy", force=True
        )
        assert len({first, second, third}) == 3
        assert second.startswith(first)
        ids = [r[0] for r in conn.execute("SELECT signal_id FROM signal_queue").fetchall()]
        assert ids == [third]

    def test_reinjected_signal_still_detected_as_duplicate_without_force(self, conn):
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy")
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy", force=True)
        with pytest.raises(DuplicateSignalError):
            inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy")

    def test_price_is_null_for_market_order(self, conn):
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy")
        row = conn.execute("SELECT price FROM signal_queue WHERE code='7203'").fetchone()
        assert row[0] is None

    def test_multiple_codes_same_date(self, conn):
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy")
        inject_signal(conn, target_date=date(2026, 5, 7), code="9984", side="sell")
        count = conn.execute("SELECT COUNT(*) FROM signal_queue").fetchone()[0]
        assert count == 2

    def test_buy_and_sell_same_code_same_date(self, conn):
        """同一銘柄・同一日でも BUY と SELL は別レコード（signal_id が異なる）。"""
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy")
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="sell")
        count = conn.execute("SELECT COUNT(*) FROM signal_queue WHERE code='7203'").fetchone()[0]
        assert count == 2

    def test_side_uppercase_normalized_to_lowercase(self, conn):
        """大文字 BUY/SELL が渡されても小文字に正規化されて挿入される。"""
        inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="BUY")
        row = conn.execute("SELECT side FROM signal_queue WHERE code='7203'").fetchone()
        assert row[0] == "buy"

    def test_invalid_side_raises_value_error(self, conn):
        """buy/sell 以外の side は ValueError を送出する。"""
        with pytest.raises(ValueError, match="buy.*sell"):
            inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="long")

    def test_zero_qty_raises_value_error(self, conn):
        """qty=0 は ValueError を送出する。"""
        with pytest.raises(ValueError, match="1 以上"):
            inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy", qty=0)

    def test_negative_qty_raises_value_error(self, conn):
        """負数 qty は ValueError を送出する。"""
        with pytest.raises(ValueError, match="1 以上"):
            inject_signal(conn, target_date=date(2026, 5, 7), code="7203", side="buy", qty=-1)
