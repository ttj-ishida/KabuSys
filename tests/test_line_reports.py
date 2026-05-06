"""tests/test_line_reports.py — LINE 定期レポートメッセージ生成テスト"""

from __future__ import annotations

from kabusys.operations.line_reports import (
    format_evening_message,
    format_monthly_message,
    format_morning_message,
    format_weekly_message,
)


class TestFormatMorningMessage:
    def test_ready_with_pending(self):
        msg = format_morning_message(
            status="READY",
            orders_no_status=0,
            pending_count=3,
            report_date="2026-05-07",
        )
        assert "2026-05-07" in msg
        assert "READY" in msg
        assert "3" in msg

    def test_blocked_shows_orders_no_status(self):
        msg = format_morning_message(
            status="BLOCKED",
            orders_no_status=2,
            pending_count=0,
            report_date="2026-05-07",
        )
        assert "BLOCKED" in msg
        assert "2" in msg

    def test_ready_with_warnings(self):
        msg = format_morning_message(
            status="READY_WITH_WARNINGS",
            orders_no_status=0,
            pending_count=1,
            report_date="2026-05-07",
        )
        assert "READY_WITH_WARNINGS" in msg

    def test_zero_pending(self):
        msg = format_morning_message(
            status="READY",
            orders_no_status=0,
            pending_count=0,
            report_date="2026-05-07",
        )
        assert "0" in msg


class TestFormatEveningMessage:
    def test_with_daily_return(self):
        msg = format_evening_message(
            inserted=4,
            report_date="2026-05-07",
            daily_return=0.032,
        )
        assert "2026-05-07" in msg
        assert "4" in msg
        assert "3.2" in msg

    def test_negative_daily_return(self):
        msg = format_evening_message(
            inserted=2,
            report_date="2026-05-07",
            daily_return=-0.015,
        )
        assert "-1.5" in msg

    def test_no_daily_return(self):
        msg = format_evening_message(
            inserted=0,
            report_date="2026-05-07",
            daily_return=None,
        )
        assert "2026-05-07" in msg
        assert "0" in msg

    def test_return_is_string(self):
        msg = format_evening_message(
            inserted=3,
            report_date="2026-05-07",
            daily_return=0.01,
        )
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestFormatWeeklyMessage:
    def test_with_full_summary(self):
        summary = {
            "cumulative_return": 0.032,
            "max_drawdown": -0.015,
            "win_rate": 0.6,
            "equity_start": 10_000_000,
            "equity_end": 10_320_000,
        }
        msg = format_weekly_message(
            summary=summary,
            from_date="2026-04-28",
            to_date="2026-05-02",
        )
        assert "2026-04-28" in msg
        assert "2026-05-02" in msg
        assert "3.2" in msg
        assert "60.0" in msg

    def test_with_none_values(self):
        summary = {
            "cumulative_return": None,
            "max_drawdown": None,
            "win_rate": None,
            "equity_start": None,
            "equity_end": None,
        }
        msg = format_weekly_message(
            summary=summary,
            from_date="2026-04-28",
            to_date="2026-05-02",
        )
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestFormatMonthlyMessage:
    def test_with_full_summary(self):
        summary = {
            "cumulative_return": 0.058,
            "max_drawdown": -0.023,
            "win_rate": 0.553,
            "equity_start": 10_000_000,
            "equity_end": 10_580_000,
        }
        msg = format_monthly_message(
            summary=summary,
            from_date="2026-04-01",
            to_date="2026-04-30",
        )
        assert "2026-04-01" in msg
        assert "5.8" in msg
        assert "55.3" in msg

    def test_with_none_values(self):
        summary = {
            "cumulative_return": None,
            "max_drawdown": None,
            "win_rate": None,
            "equity_start": None,
            "equity_end": None,
        }
        msg = format_monthly_message(
            summary=summary,
            from_date="2026-04-01",
            to_date="2026-04-30",
        )
        assert isinstance(msg, str)
        assert len(msg) > 0


# run_execution の朝通知ヘルパーのテスト
from unittest.mock import MagicMock


class TestCountPendingSignals:
    def test_returns_count_from_db(self):
        from datetime import date

        from kabusys.run_execution import _count_pending_signals

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (5,)
        result = _count_pending_signals(conn, date(2026, 5, 7))
        assert result == 5

    def test_returns_zero_when_no_rows(self):
        from datetime import date

        from kabusys.run_execution import _count_pending_signals

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (0,)
        result = _count_pending_signals(conn, date(2026, 5, 7))
        assert result == 0
