"""tests/test_line_reports.py — LINE 定期レポートメッセージ生成テスト"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from kabusys.operations.line_reports import (
    format_evening_message,
    format_monthly_message,
    format_morning_message,
    format_pre_market_message,
    format_signal_queue_message,
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


class TestFormatSignalQueueMessage:
    _SIGNALS = [
        {"code": "7203", "side": "buy", "target_size": 100},
        {"code": "6758", "side": "sell", "target_size": 200},
        {"code": "9984", "side": "buy", "target_size": None},
    ]

    def test_ready_with_signals(self):
        msg = format_signal_queue_message(
            status="READY",
            buy_count=2,
            sell_count=1,
            signals=self._SIGNALS,
            report_date="2026-05-13",
        )
        assert "2026-05-13" in msg
        assert "READY" in msg
        assert "2" in msg
        assert "1" in msg
        assert "7203" in msg
        assert "BUY" in msg
        assert "6758" in msg
        assert "SELL" in msg

    def test_empty_status(self):
        msg = format_signal_queue_message(
            status="EMPTY",
            buy_count=0,
            sell_count=0,
            signals=[],
            report_date="2026-05-13",
        )
        assert "EMPTY" in msg
        assert "0" in msg

    def test_target_size_shown(self):
        msg = format_signal_queue_message(
            status="READY",
            buy_count=1,
            sell_count=0,
            signals=[{"code": "7203", "side": "buy", "target_size": 100}],
            report_date="2026-05-13",
        )
        assert "100" in msg

    def test_none_target_size_no_crash(self):
        msg = format_signal_queue_message(
            status="READY",
            buy_count=1,
            sell_count=0,
            signals=[{"code": "9984", "side": "buy", "target_size": None}],
            report_date="2026-05-13",
        )
        assert "9984" in msg
        assert isinstance(msg, str)

    def test_max_signals_truncation(self):
        many = [{"code": str(1000 + i), "side": "buy", "target_size": 100} for i in range(15)]
        msg = format_signal_queue_message(
            status="READY",
            buy_count=15,
            sell_count=0,
            signals=many,
            report_date="2026-05-13",
        )
        assert "他" in msg
        assert "5" in msg

    def test_returns_string(self):
        msg = format_signal_queue_message(
            status="EMPTY",
            buy_count=0,
            sell_count=0,
            signals=[],
            report_date="2026-05-13",
        )
        assert isinstance(msg, str)
        assert len(msg) > 0


class TestFormatPreMarketMessage:
    def test_ready_status(self):
        msg = format_pre_market_message(
            status="READY",
            warnings_count=0,
            pending_count=5,
            report_date="2026-05-13",
        )
        assert "2026-05-13" in msg
        assert "READY" in msg
        assert "5" in msg
        assert "0" in msg

    def test_blocked_status(self):
        msg = format_pre_market_message(
            status="BLOCKED",
            warnings_count=2,
            pending_count=0,
            report_date="2026-05-13",
        )
        assert "BLOCKED" in msg
        assert "2" in msg

    def test_ready_with_warnings(self):
        msg = format_pre_market_message(
            status="READY_WITH_WARNINGS",
            warnings_count=1,
            pending_count=3,
            report_date="2026-05-13",
        )
        assert "READY_WITH_WARNINGS" in msg
        assert "1" in msg
        assert "3" in msg

    def test_returns_string(self):
        msg = format_pre_market_message(
            status="READY",
            warnings_count=0,
            pending_count=0,
            report_date="2026-05-13",
        )
        assert isinstance(msg, str)
        assert len(msg) > 0


# run_execution の朝通知ヘルパーのテスト
class TestCountPendingSignals:
    def test_returns_count_from_db(self):
        from kabusys.run_execution import _count_pending_signals

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (5,)
        result = _count_pending_signals(conn, date(2026, 5, 7))
        assert result == 5

    def test_returns_zero_when_no_rows(self):
        from kabusys.run_execution import _count_pending_signals

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (0,)
        result = _count_pending_signals(conn, date(2026, 5, 7))
        assert result == 0

    def test_returns_zero_when_fetchone_is_none(self):
        from kabusys.run_execution import _count_pending_signals

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        result = _count_pending_signals(conn, date(2026, 5, 7))
        assert result == 0


class TestGetTodayReturn:
    def test_returns_float_when_row_exists(self):
        from scripts.run_portfolio_construction import _get_today_return

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (0.032,)
        result = _get_today_return(conn, date(2026, 5, 7), "live")
        assert result == 0.032

    def test_returns_none_when_no_row(self):
        from scripts.run_portfolio_construction import _get_today_return

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = None
        result = _get_today_return(conn, date(2026, 5, 7), "live")
        assert result is None

    def test_returns_none_when_value_is_null(self):
        from scripts.run_portfolio_construction import _get_today_return

        conn = MagicMock()
        conn.execute.return_value.fetchone.return_value = (None,)
        result = _get_today_return(conn, date(2026, 5, 7), "live")
        assert result is None
