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
    WeeklyRow,
    MonthlyRow,
    collect_daily_rows,
    collect_weekly_rows,
    collect_monthly_rows,
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


# ---------------------------------------------------------------------------
# collect_weekly_rows
# ---------------------------------------------------------------------------


def test_collect_weekly_rows_grouping():
    """同週の日次行が正しく 1 件の WeeklyRow に集約される。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "daily_return": 0.004, "drawdown": -0.002},
        {"date": "2026-04-22", "equity": 5_020_000.0, "daily_return": 0.004, "drawdown": -0.001},
        # 2026-04-21 と 2026-04-22 は同じ ISO 週（W17）
    )
    rows = collect_weekly_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert len(rows) == 1
    assert isinstance(rows[0], WeeklyRow)
    assert rows[0].week_label == "2026-W17"
    assert rows[0].equity_start == 5_000_000.0
    assert rows[0].equity_end == 5_020_000.0
    assert rows[0].win_days == 2


def test_collect_weekly_rows_trading_days():
    """market_calendar の営業日数が正しく集計される。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0},
        {"date": "2026-04-22", "equity": 5_020_000.0},
        cal_rows=[
            {"date": "2026-04-21", "is_trading_day": True},
            {"date": "2026-04-22", "is_trading_day": True},
            {"date": "2026-04-23", "is_trading_day": True},
            {"date": "2026-04-24", "is_trading_day": False},
            {"date": "2026-04-25", "is_trading_day": True},
        ],
    )
    rows = collect_weekly_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 22))
    assert rows[0].trading_days == 2  # 21 と 22 のみ（portfolio_performance の範囲で集計）


def test_collect_weekly_rows_empty():
    """データなし → []。"""
    conn = _make_conn()
    rows = collect_weekly_rows(conn, "live", date(2026, 4, 1), date(2026, 4, 30))
    assert rows == []


def test_collect_weekly_rows_two_weeks():
    """2 週にまたがるデータが 2 件の WeeklyRow になる。"""
    conn = _make_conn(
        # W17: 2026-04-20(月)〜2026-04-26(日)
        {"date": "2026-04-21", "equity": 5_000_000.0, "daily_return": 0.004},
        # W18: 2026-04-27(月)〜
        {"date": "2026-04-28", "equity": 5_050_000.0, "daily_return": 0.010},
    )
    rows = collect_weekly_rows(conn, "live", date(2026, 4, 21), date(2026, 4, 28))
    assert len(rows) == 2
    assert rows[0].week_label == "2026-W17"
    assert rows[1].week_label == "2026-W18"


# ---------------------------------------------------------------------------
# collect_monthly_rows
# ---------------------------------------------------------------------------


def test_collect_monthly_rows_grouping():
    """同月の日次行が正しく 1 件の MonthlyRow に集約される。"""
    conn = _make_conn(
        {"date": "2026-04-21", "equity": 5_000_000.0, "daily_return": 0.004, "drawdown": -0.002},
        {"date": "2026-04-22", "equity": 5_020_000.0, "daily_return": -0.002, "drawdown": -0.003},
    )
    rows = collect_monthly_rows(conn, "live", date(2026, 4, 1), date(2026, 4, 30))
    assert len(rows) == 1
    assert isinstance(rows[0], MonthlyRow)
    assert rows[0].month_label == "2026-04"
    assert rows[0].equity_start == 5_000_000.0
    assert rows[0].equity_end == 5_020_000.0
    assert rows[0].max_drawdown == pytest.approx(-0.003)
    assert rows[0].win_days == 1  # daily_return > 0 は 1 日


def test_collect_monthly_rows_two_months():
    """2 ヶ月にまたがるデータが 2 件の MonthlyRow になる。"""
    conn = _make_conn(
        {"date": "2026-03-31", "equity": 4_900_000.0},
        {"date": "2026-04-01", "equity": 5_000_000.0},
    )
    rows = collect_monthly_rows(conn, "live", date(2026, 3, 1), date(2026, 4, 30))
    assert len(rows) == 2
    assert rows[0].month_label == "2026-03"
    assert rows[1].month_label == "2026-04"


def test_collect_monthly_rows_empty():
    """データなし → []。"""
    conn = _make_conn()
    rows = collect_monthly_rows(conn, "live", date(2026, 4, 1), date(2026, 4, 30))
    assert rows == []


from kabusys.operations.performance_report import (  # noqa: E402
    PerformanceReport,
    build_report,
    format_markdown,  # noqa: F401
    save_report,  # noqa: F401
)


# ---------------------------------------------------------------------------
# build_report
# ---------------------------------------------------------------------------


def _make_daily_rows() -> list:
    from kabusys.operations.performance_collector import DailyRow
    return [
        DailyRow(date=date(2026, 4, 21), env="live", equity=5_000_000.0,
                 daily_return=0.004, drawdown=-0.002, cumulative_return=0.0),
        DailyRow(date=date(2026, 4, 22), env="live", equity=5_020_000.0,
                 daily_return=-0.001, drawdown=-0.003, cumulative_return=0.004),
        DailyRow(date=date(2026, 4, 23), env="live", equity=5_040_000.0,
                 daily_return=0.004, drawdown=-0.001, cumulative_return=0.008),
    ]


def test_build_report_summary_basic():
    """cumulative_return / max_drawdown / win_rate が正しく計算される。"""
    rows = _make_daily_rows()
    report = build_report(
        rows,
        report_type="daily",
        env="live",
        from_date=date(2026, 4, 21),
        to_date=date(2026, 4, 23),
    )
    assert isinstance(report, PerformanceReport)
    assert report.summary["total_trading_days"] == 3
    assert report.summary["equity_start"] == 5_000_000.0
    assert report.summary["equity_end"] == 5_040_000.0
    assert report.summary["cumulative_return"] == pytest.approx(0.008)
    assert report.summary["max_drawdown"] == pytest.approx(-0.003)
    assert report.summary["win_rate"] == pytest.approx(2 / 3)


def test_build_report_empty_rows():
    """rows=[] のとき summary は None 値（total_trading_days=0）。"""
    report = build_report(
        [],
        report_type="daily",
        env="live",
        from_date=date(2026, 4, 21),
        to_date=date(2026, 4, 23),
    )
    assert report.summary["total_trading_days"] == 0
    assert report.summary["cumulative_return"] is None
    assert report.summary["max_drawdown"] is None
    assert report.summary["win_rate"] is None


def test_build_report_weekly_summary():
    """週次 rows から summary が正しく集約される。"""
    from kabusys.operations.performance_collector import WeeklyRow
    rows = [
        WeeklyRow(week_label="2026-W17", trading_days=5,
                  equity_start=5_000_000.0, equity_end=5_025_000.0,
                  weekly_return=0.005, max_drawdown=-0.002, win_days=3),
        WeeklyRow(week_label="2026-W18", trading_days=5,
                  equity_start=5_025_000.0, equity_end=5_050_000.0,
                  weekly_return=0.005, max_drawdown=-0.001, win_days=4),
    ]
    report = build_report(
        rows,
        report_type="weekly",
        env="live",
        from_date=date(2026, 4, 20),
        to_date=date(2026, 4, 30),
    )
    assert report.summary["total_trading_days"] == 10
    assert report.summary["equity_start"] == 5_000_000.0
    assert report.summary["equity_end"] == 5_050_000.0
    assert report.summary["max_drawdown"] == pytest.approx(-0.002)
    assert report.summary["win_rate"] == pytest.approx(7 / 10)
