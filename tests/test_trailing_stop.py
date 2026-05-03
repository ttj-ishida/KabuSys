"""tests/test_trailing_stop.py — トレーリングストップ（ATR×2）テスト"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from kabusys.data.schema import init_schema
from kabusys.strategy.signal_generator import _atr_20d, _peak_close


def _weekdays_before(d: date, n: int) -> list[date]:
    """d の前の n 営業日（月〜金）を昇順で返す。"""
    result: list[date] = []
    cur = d - timedelta(days=1)
    while len(result) < n:
        if cur.weekday() < 5:
            result.insert(0, cur)
        cur -= timedelta(days=1)
    return result


@pytest.fixture
def conn():
    c = init_schema(":memory:")
    yield c
    c.close()


# ---------------------------------------------------------------------------
# _atr_20d ヘルパー
# ---------------------------------------------------------------------------


class TestAtr20d:
    def test_returns_correct_average(self, conn):
        """20営業日の履歴 + target_date の計 21 行があるとき ATR_20d を正しく計算する。

        high=1010, low=990, close=1000（前日 close も 1000）のとき
        TR = GREATEST(20, |1010-1000|, |990-1000|) = 20 → ATR = 20.0
        """
        code = "ATR1"
        target = date(2026, 4, 6)
        for d in _weekdays_before(target, 20) + [target]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, 1000.0, 1010.0, 990.0, 1000.0, 1000000)",
                [d, code],
            )
        result = _atr_20d(conn, code, target)
        assert result == pytest.approx(20.0)

    def test_returns_none_when_insufficient_data(self, conn):
        """履歴が 20 日未満（TR < 20 本）のとき None を返す。"""
        code = "ATR2"
        target = date(2026, 4, 6)
        # 10 days before + target = 11 rows → 10 TR values → None
        for d in _weekdays_before(target, 10) + [target]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, 1000.0, 1010.0, 990.0, 1000.0, 1000000)",
                [d, code],
            )
        result = _atr_20d(conn, code, target)
        assert result is None

    def test_returns_none_at_boundary_19_tr_values(self, conn):
        """TR が 19 本（境界値 -1）のとき None を返す。"""
        code = "ATR3"
        target = date(2026, 4, 6)
        # 19 days before + target = 20 rows → 19 TR values (oldest has NULL prev_close) → None
        for d in _weekdays_before(target, 19) + [target]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, 1000.0, 1010.0, 990.0, 1000.0, 1000000)",
                [d, code],
            )
        result = _atr_20d(conn, code, target)
        assert result is None


# ---------------------------------------------------------------------------
# _peak_close ヘルパー
# ---------------------------------------------------------------------------


class TestPeakClose:
    def test_returns_max_close_since_entry(self, conn):
        """エントリー日以降の最高 close を返す。"""
        code = "PEAK1"
        entry = date(2026, 4, 6)
        target = date(2026, 4, 8)
        conn.execute(
            "INSERT INTO position_entries (code, entry_date, sell_date) VALUES (?, ?, NULL)",
            [code, entry],
        )
        for d, c in [
            (date(2026, 4, 6), 100.0),
            (date(2026, 4, 7), 120.0),
            (date(2026, 4, 8), 110.0),
        ]:
            conn.execute(
                "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
                "VALUES (?, ?, ?, ?, ?, ?, 1000000)",
                [d, code, c, c * 1.05, c * 0.95, c],
            )
        result = _peak_close(conn, code, target)
        assert result == pytest.approx(120.0)

    def test_returns_none_when_no_open_entry(self, conn):
        """オープンなエントリーが存在しない場合 None を返す。"""
        code = "PEAK2"
        target = date(2026, 4, 8)
        conn.execute(
            "INSERT INTO prices_daily (date, code, open, high, low, close, volume) "
            "VALUES (?, ?, 100.0, 110.0, 90.0, 100.0, 1000000)",
            [target, code],
        )
        result = _peak_close(conn, code, target)
        assert result is None
