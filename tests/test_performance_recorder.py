"""record_daily_performance のテスト（Issue #427）。"""

from __future__ import annotations

from datetime import date

import duckdb
import pytest

from kabusys.data.schema import init_schema
from kabusys.operations.performance_recorder import record_daily_performance


@pytest.fixture
def conn(tmp_path):
    c = init_schema(tmp_path / "t.duckdb")
    yield c
    c.close()


def _rows(conn: duckdb.DuckDBPyConnection, env: str = "paper_trading"):
    return conn.execute(
        "SELECT date, equity, cash, drawdown, daily_return FROM portfolio_performance"
        " WHERE env = ? ORDER BY date",
        [env],
    ).fetchall()


def test_first_day_has_no_return_and_zero_drawdown(conn):
    row = record_daily_performance(
        conn, as_of=date(2026, 11, 2), env="paper_trading", equity=1_000_000.0, cash=400_000.0
    )
    assert row.daily_return is None
    assert row.drawdown == pytest.approx(0.0)
    rows = _rows(conn)
    assert len(rows) == 1
    assert float(rows[0][1]) == pytest.approx(1_000_000.0)
    assert float(rows[0][2]) == pytest.approx(400_000.0)
    assert rows[0][4] is None


def test_second_day_daily_return(conn):
    record_daily_performance(
        conn, as_of=date(2026, 11, 2), env="paper_trading", equity=1_000_000.0, cash=0.0
    )
    row = record_daily_performance(
        conn, as_of=date(2026, 11, 4), env="paper_trading", equity=1_050_000.0, cash=0.0
    )
    assert row.daily_return == pytest.approx(0.05)
    assert row.drawdown == pytest.approx(0.0)


def test_drawdown_from_peak(conn):
    row = None
    for d, eq in [(2, 1_000_000.0), (4, 1_100_000.0), (5, 1_045_000.0)]:
        row = record_daily_performance(
            conn, as_of=date(2026, 11, d), env="paper_trading", equity=eq, cash=0.0
        )
    assert row is not None
    assert row.drawdown == pytest.approx(-0.05)
    assert row.daily_return == pytest.approx(1_045_000 / 1_100_000 - 1)


def test_rerun_same_day_is_idempotent(conn):
    record_daily_performance(
        conn, as_of=date(2026, 11, 2), env="paper_trading", equity=1_000_000.0, cash=0.0
    )
    record_daily_performance(
        conn, as_of=date(2026, 11, 4), env="paper_trading", equity=1_100_000.0, cash=0.0
    )
    row = record_daily_performance(
        conn, as_of=date(2026, 11, 4), env="paper_trading", equity=900_000.0, cash=10.0
    )
    rows = _rows(conn)
    assert len(rows) == 2
    assert float(rows[1][1]) == pytest.approx(900_000.0)
    assert float(rows[1][2]) == pytest.approx(10.0)
    # 再実行しても直前日（11/2）基準で計算され、自分自身を直前とみなさない
    assert row.daily_return == pytest.approx(-0.1)
    # ピークは 11/2 の 1,000,000（上書き前の 11/4 値は含まない）
    assert row.drawdown == pytest.approx(-0.1)


def test_envs_are_independent(conn):
    record_daily_performance(
        conn, as_of=date(2026, 11, 2), env="paper_trading", equity=1_000_000.0, cash=0.0
    )
    row = record_daily_performance(
        conn, as_of=date(2026, 11, 4), env="live", equity=5_000_000.0, cash=0.0
    )
    assert row.daily_return is None
    assert row.drawdown == pytest.approx(0.0)
    assert len(_rows(conn, "paper_trading")) == 1
    assert len(_rows(conn, "live")) == 1


def test_backfill_ignores_later_dates(conn):
    """過去日を後から記録しても、その日以降の equity はピーク・直前に含めない。"""
    record_daily_performance(
        conn, as_of=date(2026, 11, 5), env="paper_trading", equity=2_000_000.0, cash=0.0
    )
    row = record_daily_performance(
        conn, as_of=date(2026, 11, 2), env="paper_trading", equity=1_000_000.0, cash=0.0
    )
    assert row.daily_return is None
    assert row.drawdown == pytest.approx(0.0)
