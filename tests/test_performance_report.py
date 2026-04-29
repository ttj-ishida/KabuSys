"""performance_collector / performance_report のテスト"""

from __future__ import annotations

import duckdb


# ---------------------------------------------------------------------------
# テストヘルパー
# ---------------------------------------------------------------------------


def _make_conn(
    *perf_rows: dict,
    cal_rows: list[dict] | None = None,
) -> duckdb.DuckDBPyConnection:
    """インメモリ DuckDB にテーブルとデータを投入して返す。

    perf_rows キー: date (str), equity (float), cash (float, 省略可),
                    drawdown (float|None), daily_return (float|None),
                    env (str, 省略時 "live")
    cal_rows  キー: date (str), is_trading_day (bool)
    """
    conn = duckdb.connect(":memory:")
    conn.execute(
        """
        CREATE TABLE portfolio_performance (
            date         DATE          NOT NULL PRIMARY KEY,
            equity       DECIMAL(20,4) NOT NULL,
            cash         DECIMAL(20,4) NOT NULL DEFAULT 0,
            drawdown     DOUBLE,
            daily_return DOUBLE,
            env          VARCHAR       NOT NULL DEFAULT 'live'
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE market_calendar (
            date           DATE    NOT NULL PRIMARY KEY,
            is_trading_day BOOLEAN NOT NULL
        )
        """
    )
    for r in perf_rows:
        conn.execute(
            "INSERT INTO portfolio_performance"
            " (date, equity, cash, drawdown, daily_return, env)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            [
                r["date"],
                r["equity"],
                r.get("cash", 0.0),
                r.get("drawdown"),
                r.get("daily_return"),
                r.get("env", "live"),
            ],
        )
    for r in cal_rows or []:
        conn.execute(
            "INSERT INTO market_calendar VALUES (?, ?)",
            [r["date"], r["is_trading_day"]],
        )
    return conn


# ---------------------------------------------------------------------------
# Task 1: schema smoke test
# ---------------------------------------------------------------------------


def test_schema_env_column_exists():
    """インメモリ DB で env 列が作れる（スキーマ定義の確認）。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "env": "live"},
    )
    row = conn.execute(
        "SELECT env FROM portfolio_performance WHERE date = '2026-04-21'"
    ).fetchone()
    assert row is not None
    assert row[0] == "live"


# ---------------------------------------------------------------------------
# Task 2: collect_daily_rows
# ---------------------------------------------------------------------------

from datetime import date  # noqa: E402

import pytest  # noqa: E402

from kabusys.operations.performance_collector import (  # noqa: E402
    DailyRow,
    collect_daily_rows,
)


def test_collect_daily_rows_basic():
    """基本的な日次行取得。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "daily_return": 0.004, "drawdown": -0.002},
        {"date": "2026-04-22", "equity": 5_020_000.0, "daily_return": 0.004, "drawdown": -0.001},
    )
    rows = collect_daily_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert len(rows) == 2
    assert isinstance(rows[0], DailyRow)
    assert rows[0].equity == 5_000_000.0


def test_collect_daily_rows_env_isolation():
    """live と paper_trading が混在しても正しく絞り込まれる。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "env": "live"},
        {"date": "2026-04-22", "equity": 4_500_000.0, "env": "paper_trading"},
    )
    rows = collect_daily_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert len(rows) == 1
    assert rows[0].env == "live"


def test_collect_daily_rows_empty():
    """データなし → []。"""
    conn = _make_conn()
    rows = collect_daily_rows(conn, "live", date(2026, 4, 1), date(2026, 4, 30))
    assert rows == []


def test_collect_daily_rows_cumulative_return():
    """累積リターンが期間内最初の equity を基準に計算される。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0},
        {"date": "2026-04-22", "equity": 5_100_000.0},
    )
    rows = collect_daily_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert rows[0].cumulative_return == pytest.approx(0.0)
    assert rows[1].cumulative_return == pytest.approx(0.02)


def test_collect_daily_rows_date_filter():
    """from_date / to_date で正しく絞り込まれる。"""
    conn = _make_conn(
        {"date": "2026-04-20", "equity": 4_900_000.0},
        {"date": "2026-04-21", "equity": 5_000_000.0},
        {"date": "2026-04-23", "equity": 5_100_000.0},
    )
    rows = collect_daily_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert len(rows) == 1
    assert rows[0].equity == 5_000_000.0
