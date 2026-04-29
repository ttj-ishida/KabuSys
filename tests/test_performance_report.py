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
