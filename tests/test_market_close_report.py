"""Market Close Summary レポートのテスト。"""

from __future__ import annotations

import json
import sqlite3 as _sqlite3
from datetime import date

import duckdb as _duckdb
import pytest

from kabusys.operations.market_close_report import (
    STATUS_BLOCKED,
    STATUS_OK,
    MarketCloseReport,
    build_report,
    format_cli_summary,
    format_json,
    format_markdown,
    save_report,
)


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------


def _make_report(
    *,
    signal_pending_count: int = 0,
    positions_updated: bool = True,
    performance_recorded: bool = True,
    filled_count: int = 3,
    daily_return: float | None = 0.0032,
    equity_today: float | None = 5_234_000.0,
    equity_prev: float | None = 5_217_600.0,
    report_date: date = date(2026, 4, 28),
) -> MarketCloseReport:
    return build_report(
        report_date=report_date,
        signal_pending_count=signal_pending_count,
        positions_updated=positions_updated,
        performance_recorded=performance_recorded,
        filled_count=filled_count,
        daily_return=daily_return,
        equity_today=equity_today,
        equity_prev=equity_prev,
    )


# ---------------------------------------------------------------------------
# build_report — ステータス判定
# ---------------------------------------------------------------------------


def test_build_report_ok():
    report = _make_report()
    assert report.status == STATUS_OK


def test_build_report_blocked_pending():
    report = _make_report(signal_pending_count=2)
    assert report.status == STATUS_BLOCKED


def test_build_report_blocked_positions():
    report = _make_report(positions_updated=False)
    assert report.status == STATUS_BLOCKED


def test_build_report_blocked_performance():
    report = _make_report(performance_recorded=False)
    assert report.status == STATUS_BLOCKED


def test_build_report_all_blocked():
    report = _make_report(
        signal_pending_count=1,
        positions_updated=False,
        performance_recorded=False,
    )
    assert report.status == STATUS_BLOCKED
    assert len(report.warnings) == 3


# ---------------------------------------------------------------------------
# build_report — チェック項目
# ---------------------------------------------------------------------------


def test_build_report_check_items_count():
    report = _make_report()
    assert len(report.checks) == 3


def test_build_report_checks_all_ok():
    report = _make_report()
    assert all(c.status == "ok" for c in report.checks)


def test_build_report_checks_signal_failed():
    report = _make_report(signal_pending_count=3)
    sq = next(c for c in report.checks if c.name == "signal_queue")
    assert sq.status == "failed"
    assert "3 件" in sq.detail


def test_build_report_checks_positions_failed():
    report = _make_report(positions_updated=False)
    pos = next(c for c in report.checks if c.name == "positions")
    assert pos.status == "failed"


def test_build_report_checks_performance_failed():
    report = _make_report(performance_recorded=False)
    perf = next(c for c in report.checks if c.name == "portfolio_performance")
    assert perf.status == "failed"


# ---------------------------------------------------------------------------
# build_report — summary（損益額計算）
# ---------------------------------------------------------------------------


def test_build_report_pnl_amount_calculated():
    report = _make_report(equity_today=5_234_000.0, equity_prev=5_217_600.0)
    assert report.summary["pnl_amount"] == pytest.approx(16_400.0)


def test_build_report_pnl_amount_none_when_equity_today_missing():
    report = _make_report(equity_today=None, equity_prev=5_217_600.0)
    assert report.summary["pnl_amount"] is None


def test_build_report_pnl_amount_none_when_equity_prev_missing():
    report = _make_report(equity_today=5_234_000.0, equity_prev=None)
    assert report.summary["pnl_amount"] is None


def test_build_report_summary_fields():
    report = _make_report(filled_count=5, daily_return=0.0032)
    assert report.summary["filled_count"] == 5
    assert report.summary["daily_return"] == pytest.approx(0.0032)


# ---------------------------------------------------------------------------
# format_cli_summary
# ---------------------------------------------------------------------------


def test_format_cli_summary_ok():
    report = _make_report()
    out = format_cli_summary(report)
    assert "✅" in out
    assert STATUS_OK in out
    assert "pending: 0 件" in out


def test_format_cli_summary_blocked():
    report = _make_report(signal_pending_count=2)
    out = format_cli_summary(report)
    assert "🚫" in out
    assert STATUS_BLOCKED in out
    assert "Warnings" in out
    assert "2 件" in out


def test_format_cli_summary_summary_section():
    report = _make_report(
        filled_count=5,
        daily_return=0.0032,
        equity_today=5_234_000.0,
        equity_prev=5_217_600.0,
    )
    out = format_cli_summary(report)
    assert "5 件" in out
    assert "0.32%" in out
    assert "16,400" in out
    assert "5,234,000" in out


def test_format_cli_summary_none_values():
    report = _make_report(daily_return=None, equity_today=None, equity_prev=None)
    out = format_cli_summary(report)
    assert "N/A" in out


# ---------------------------------------------------------------------------
# format_json
# ---------------------------------------------------------------------------


def test_format_json_is_valid_json():
    report = _make_report()
    data = json.loads(format_json(report))
    assert data["status"] == STATUS_OK
    assert data["report_date"] == "2026-04-28"
    assert "checks" in data
    assert "summary" in data
    assert "warnings" in data
    assert len(data["checks"]) == 3


# ---------------------------------------------------------------------------
# format_markdown
# ---------------------------------------------------------------------------


def test_format_markdown_contains_sections():
    report = _make_report()
    md = format_markdown(report)
    assert "# Market Close Summary" in md
    assert "Overview" in md
    assert "Checks" in md
    assert "Summary" in md
    assert "Final Decision" in md
    assert STATUS_OK in md


def test_format_markdown_blocked_contains_warnings():
    report = _make_report(signal_pending_count=1)
    md = format_markdown(report)
    assert "Warnings" in md
    assert STATUS_BLOCKED in md


# ---------------------------------------------------------------------------
# save_report
# ---------------------------------------------------------------------------


def test_save_report_creates_files(tmp_path):
    report = _make_report()
    run_dir = save_report(report, output_dir=tmp_path)
    assert (run_dir / "summary.json").exists()
    assert (run_dir / "report.md").exists()
    assert (run_dir / "warnings.json").exists()


def test_save_report_directory_name(tmp_path):
    report = _make_report()
    run_dir = save_report(report, output_dir=tmp_path)
    assert run_dir.name == "2026-04-28"


def test_save_report_invalid_date_format(tmp_path):
    report = _make_report()
    report.report_date = "20260428"
    with pytest.raises(ValueError):
        save_report(report, output_dir=tmp_path)


def test_save_report_invalid_calendar_date(tmp_path):
    report = _make_report()
    report.report_date = "2026-99-99"
    with pytest.raises(ValueError):
        save_report(report, output_dir=tmp_path)


# ---------------------------------------------------------------------------
# collector fixtures（Task 2 で使用）
# ---------------------------------------------------------------------------

TODAY = date(2026, 4, 28)
PREV = date(2026, 4, 25)


@pytest.fixture
def ddb():
    """インメモリ DuckDB（positions + portfolio_performance テーブル付き）。"""
    conn = _duckdb.connect(":memory:")
    conn.execute(
        "CREATE TABLE positions ("
        "  date DATE, code VARCHAR, position_size INTEGER,"
        "  avg_price FLOAT, market_value FLOAT"
        ")"
    )
    conn.execute(
        "CREATE TABLE portfolio_performance ("
        "  date DATE, equity FLOAT, cash FLOAT,"
        "  drawdown FLOAT, daily_return FLOAT"
        ")"
    )
    yield conn
    conn.close()


@pytest.fixture
def sdb():
    """インメモリ SQLite（signal_queue テーブル付き）。"""
    conn = _sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE signal_queue ("
        "  signal_id TEXT, date TEXT, code TEXT, side TEXT,"
        "  size INTEGER, order_type TEXT, price REAL,"
        "  status TEXT, created_at TEXT, processed_at TEXT"
        ")"
    )
    conn.commit()
    yield conn
    conn.close()


def _insert_signal(sdb, date_str: str, status: str, code: str = "1234") -> None:
    sdb.execute(
        "INSERT INTO signal_queue"
        " (signal_id, date, code, side, size, order_type, price, status, created_at, processed_at)"
        " VALUES (?, ?, ?, 'buy', 100, 'market', NULL, ?, '2026-04-28T08:00:00', NULL)",
        (f"sig-{code}-{status}", date_str, code, status),
    )
    sdb.commit()


def _insert_position(ddb, date_val: date, code: str = "1234") -> None:
    ddb.execute(
        "INSERT INTO positions VALUES (?, ?, 100, 1500.0, 150000.0)",
        [date_val.isoformat(), code],
    )


def _insert_performance(
    ddb,
    date_val: date,
    equity: float = 5_234_000.0,
    daily_return: float = 0.0032,
) -> None:
    ddb.execute(
        "INSERT INTO portfolio_performance VALUES (?, ?, 1000000.0, -0.005, ?)",
        [date_val.isoformat(), equity, daily_return],
    )
