"""tests/test_operations_data.py — operations_data.py の単体テスト。"""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone


# ---------------------------------------------------------------------------
# load_execution_startup のテスト
# ---------------------------------------------------------------------------


class TestLoadExecutionStartup:
    def test_returns_none_when_file_missing(self, tmp_path):
        from kabusys.monitoring.operations_data import load_execution_startup

        result = load_execution_startup(
            tmp_path / "execution_startup", target_date=date(2026, 5, 8)
        )
        assert result is None

    def test_returns_dict_when_file_exists(self, tmp_path):
        from kabusys.monitoring.operations_data import load_execution_startup

        base = tmp_path / "execution_startup"
        day_dir = base / "2026-05-08"
        day_dir.mkdir(parents=True)
        payload = {
            "status": "READY",
            "orders_synced": 3,
            "orders_no_status": 0,
            "position_discrepancies": [],
            "warnings": [],
            "generated_at": "2026-05-08T08:30:00+00:00",
        }
        (day_dir / "summary.json").write_text(json.dumps(payload), encoding="utf-8")
        result = load_execution_startup(base, target_date=date(2026, 5, 8))
        assert result is not None
        assert result["status"] == "READY"
        assert result["orders_synced"] == 3

    def test_defaults_to_today_when_no_date_given(self, tmp_path):
        from kabusys.monitoring.operations_data import load_execution_startup

        base = tmp_path / "execution_startup"
        today_str = date.today().isoformat()
        day_dir = base / today_str
        day_dir.mkdir(parents=True)
        (day_dir / "summary.json").write_text(
            json.dumps({"status": "BLOCKED"}), encoding="utf-8"
        )
        result = load_execution_startup(base)
        assert result is not None
        assert result["status"] == "BLOCKED"


# ---------------------------------------------------------------------------
# load_intraday_summary のテスト
# ---------------------------------------------------------------------------


def _make_monitoring_db() -> sqlite3.Connection:
    """テスト用の monitoring SQLite DB を作成する。"""
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE risk_logs (
            id INTEGER PRIMARY KEY,
            event_type TEXT,
            message TEXT,
            logged_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE dashboard (
            id INTEGER PRIMARY KEY,
            portfolio_value REAL,
            cash REAL,
            drawdown_pct REAL,
            updated_at TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE trade_logs (
            id INTEGER PRIMARY KEY,
            event_type TEXT,
            message TEXT,
            logged_at TEXT
        )
    """)
    conn.commit()
    return conn


class TestLoadIntradaySummary:
    def test_returns_zeros_when_no_events(self):
        from kabusys.monitoring.operations_data import load_intraday_summary

        conn = _make_monitoring_db()
        result = load_intraday_summary(conn, hours=1)
        assert result["order_errors"] == 0
        assert result["stale_orders"] == 0
        assert result["drawdown_pct"] == 0.0
        conn.close()

    def test_counts_order_errors_within_window(self):
        from kabusys.monitoring.operations_data import load_intraday_summary

        conn = _make_monitoring_db()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO risk_logs (event_type, message, logged_at) VALUES (?, ?, ?)",
            ("ORDER_ERROR", "error", now),
        )
        conn.commit()
        result = load_intraday_summary(conn, hours=1)
        assert result["order_errors"] == 1
        conn.close()

    def test_reads_drawdown_from_dashboard(self):
        from kabusys.monitoring.operations_data import load_intraday_summary

        conn = _make_monitoring_db()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO dashboard (portfolio_value, cash, drawdown_pct, updated_at) VALUES (?, ?, ?, ?)",
            (1000000, 300000, -0.05, now),
        )
        conn.commit()
        result = load_intraday_summary(conn)
        assert abs(result["drawdown_pct"] - (-5.0)) < 0.01
        conn.close()


# ---------------------------------------------------------------------------
# load_failure_summary のテスト
# ---------------------------------------------------------------------------


class TestLoadFailureSummary:
    def test_returns_zero_counts_when_no_events(self):
        from kabusys.monitoring.operations_data import load_failure_summary

        conn = _make_monitoring_db()
        result = load_failure_summary(conn)
        assert result["critical_count"] == 0
        assert result["kill_switch_count"] == 0
        assert result["order_error_count"] == 0
        assert result["recent_events"] == []
        conn.close()

    def test_counts_critical_events_within_24h(self):
        from kabusys.monitoring.operations_data import load_failure_summary

        conn = _make_monitoring_db()
        now = datetime.now(timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO risk_logs (event_type, message, logged_at) VALUES (?, ?, ?)",
            ("CRITICAL", "crit", now),
        )
        conn.execute(
            "INSERT INTO risk_logs (event_type, message, logged_at) VALUES (?, ?, ?)",
            ("KILL_SWITCH", "ks", now),
        )
        conn.commit()
        result = load_failure_summary(conn)
        assert result["critical_count"] == 1
        assert result["kill_switch_count"] == 1
        assert len(result["recent_events"]) == 2
        conn.close()


# ---------------------------------------------------------------------------
# load_paper_verification_data のテスト
# ---------------------------------------------------------------------------


class TestLoadPaperVerificationData:
    def test_returns_unavailable_when_db_missing(self, tmp_path):
        from kabusys.monitoring.operations_data import load_paper_verification_data

        result = load_paper_verification_data(tmp_path / "nonexistent.db")
        assert result["available"] is False

    def test_returns_available_with_empty_db(self, tmp_path):
        from kabusys.monitoring.operations_data import load_paper_verification_data

        db_path = tmp_path / "paper.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("""
            CREATE TABLE system_status (
                id INTEGER PRIMARY KEY, process_ok INTEGER, recorded_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE trade_logs (
                id INTEGER PRIMARY KEY, event_type TEXT, logged_at TEXT, latency_ms REAL
            )
        """)
        conn.execute("""
            CREATE TABLE risk_logs (id INTEGER PRIMARY KEY, logged_at TEXT)
        """)
        conn.commit()
        conn.close()
        result = load_paper_verification_data(db_path)
        assert result["available"] is True
        assert result["uptime_pct"] is None  # 空DB なので None
